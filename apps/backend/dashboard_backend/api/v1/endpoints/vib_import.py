from __future__ import annotations

import base64
import json

from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from dashboard_backend.celery_app import celery_app
from dashboard_backend.core.config import settings
from dashboard_backend.core.security import require_roles
from dashboard_backend.crud.vib import (
    create_vib_report_with_entries,
    delete_draft,
    delete_report,
    get_draft_by_task_id,
    get_report_by_year,
    list_drafts,
    list_reports,
    update_draft_ai_result,
)
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.tasks import TaskLaunchResponse
from dashboard_backend.schemas.users import UserRole
from dashboard_backend.schemas.vib import (
    VibAiAvailableResponse,
    VibConfirmRequest,
    VibConfirmResponse,
    VibDraftSchema,
    VibEntryProposed,
    VibOcrAvailableResponse,
    VibParseTaskResult,
    VibReportSchema,
)
from dashboard_backend.tasks.vib import parse_vib_pdf
from dashboard_backend.tasks.vib_ai_extraction import extract_vib_blocks

router = AuthRouter()

_require_editor = Depends(require_roles(UserRole.editor, UserRole.admin))


def _draft_result(db: Session, task_id: str) -> VibParseTaskResult | None:
    """Return the parsed result stored in the DB draft, or None if no draft exists."""
    draft = get_draft_by_task_id(db, task_id)
    if draft is None:
        return None
    return VibParseTaskResult.model_validate_json(draft.raw_result_json)


# ---------------------------------------------------------------------------
# GET /ai-available — check if LLM-based AI extraction is configured
# ---------------------------------------------------------------------------

@router.get(
    "/ai-available",
    response_model=VibAiAvailableResponse,
    dependencies=[_require_editor],
)
def vib_ai_available():
    """Return whether LLM-based AI extraction is configured."""
    available = bool(settings.llm_base_url)
    return VibAiAvailableResponse(
        available=available,
        model=settings.llm_model if available else None,
    )


# ---------------------------------------------------------------------------
# GET /ocr-available — check if Mistral OCR is configured
# ---------------------------------------------------------------------------

@router.get(
    "/ocr-available",
    response_model=VibOcrAvailableResponse,
    dependencies=[_require_editor],
)
def vib_ocr_available():
    """Return whether Mistral OCR is configured."""
    available = bool(settings.ocr_api_key)
    return VibOcrAvailableResponse(
        available=available,
        model=settings.ocr_model if available else None,
    )


# ---------------------------------------------------------------------------
# POST /parse — start PDF parse task
# ---------------------------------------------------------------------------

@router.post("/parse", response_model=TaskLaunchResponse, dependencies=[_require_editor])
async def start_vib_parse(
    pdf: UploadFile = File(...),
    year: int = Form(...),
    start_page: int | None = Form(None),
    end_page: int | None = Form(None),
    strip_headers_footers: bool = Form(True),
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
):
    """Upload a VIB PDF and start a background parse task.

    start_page / end_page (optional, 1-indexed): restrict OCR to these pages only.
    strip_headers_footers: remove repeated page headers/footers from OCR output (default True).

    Returns the Celery task_id for polling via GET /api/v1/tasks/{task_id}.
    """
    pdf_bytes = await pdf.read()
    user_info = {"id": current_user.id, "username": current_user.username}
    result = parse_vib_pdf.delay(
        pdf_bytes, year, pdf.filename or "upload.pdf", user_info,
        start_page, end_page, strip_headers_footers,
    )
    return TaskLaunchResponse(task_id=result.id)


# ---------------------------------------------------------------------------
# GET /parse-result/{task_id} — retrieve completed parse result from Redis
# ---------------------------------------------------------------------------

@router.get(
    "/parse-result/{task_id}",
    response_model=VibParseTaskResult,
    dependencies=[_require_editor],
)
def get_vib_parse_result(task_id: str, db: Session = Depends(get_db)):
    """Retrieve the parse result for a completed Celery task.

    Tries Redis first (Celery result backend). Falls back to the
    vib_draft_report DB table if the Redis entry has been evicted.
    Returns 202 if the task is still running; 422 if it failed.
    """
    async_result = celery_app.AsyncResult(task_id)

    if async_result.state in ("PENDING", "STARTED", "PROGRESS"):
        # Before giving up, check if the result was already saved to DB
        # (handles the case where Redis lost the task state but DB has it)
        result = _draft_result(db, task_id)
        if result is None:
            raise HTTPException(status_code=202, detail=f"Task state: {async_result.state}")
        return result

    if async_result.state == "FAILURE":
        raise HTTPException(
            status_code=422,
            detail=f"Parse task failed: {async_result.result}",
        )

    if async_result.state == "SUCCESS":
        # Prefer the DB draft over the original Redis result — the user may have
        # saved edits via PATCH /draft/{task_id}, which updates raw_result_json
        # in DB but cannot update the immutable Celery task result in Redis.
        result = _draft_result(db, task_id)
        if result is not None:
            return result
        raw = async_result.result
        if isinstance(raw, dict):
            return VibParseTaskResult.model_validate(raw)

    # Redis result gone (PENDING after eviction) — fall back to DB
    result = _draft_result(db, task_id)
    if result is not None:
        return result

    raise HTTPException(status_code=404, detail="Parse-Ergebnis nicht mehr verfügbar. Bitte PDF erneut hochladen.")


# ---------------------------------------------------------------------------
# POST /confirm — import parsed data into the database
# ---------------------------------------------------------------------------

@router.post("/confirm", response_model=VibConfirmResponse)
def confirm_vib_import(
    body: VibConfirmRequest,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Confirm a VIB parse result and write VibReport + VibEntry rows to DB.

    Guard: if a VibReport for the given year already exists, returns 409.
    Delete the existing report first if re-import is needed.
    """
    existing = get_report_by_year(db, body.year)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"VIB-Bericht für Jahr {body.year} ist bereits importiert (id={existing.id}). "
                "Bitte zuerst löschen, um neu zu importieren."
            ),
        )

    # Verify the task result is available — the user may also submit the entries
    # directly without going through the task (e.g. in tests), so only validate
    # if a task_id was provided.
    if body.task_id:
        async_result = celery_app.AsyncResult(body.task_id)
        if async_result.state != "SUCCESS":
            # The Celery result may have been evicted from Redis, but the draft
            # saved to DB counts as proof the task completed successfully.
            draft = get_draft_by_task_id(db, body.task_id)
            if draft is None:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Task {body.task_id!r} ist nicht im Status SUCCESS "
                        f"(aktuell: {async_result.state}). "
                        "Bitte warten, bis der Parse-Vorgang abgeschlossen ist."
                    ),
                )

    response = create_vib_report_with_entries(
        db=db,
        year=body.year,
        drucksache_nr=body.drucksache_nr,
        report_date_str=body.report_date,
        entries=body.entries,
        user=current_user,
    )

    # Clean up the draft now that the confirmed data is in the DB
    if body.task_id:
        delete_draft(db, body.task_id)

    db.commit()
    return response


# ---------------------------------------------------------------------------
# POST /extract-ai/{parse_task_id} — start LLM extraction task
# ---------------------------------------------------------------------------

@router.post(
    "/extract-ai/{parse_task_id}",
    response_model=TaskLaunchResponse,
    dependencies=[_require_editor],
)
def start_vib_ai_extraction(
    parse_task_id: str,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Start the LLM extraction Celery task for a parsed VIB draft.

    The parse_task_id must refer to a completed parse task whose draft is saved in DB.
    Returns a new task_id for polling via GET /api/v1/tasks/{task_id}.
    When the task reaches SUCCESS, the draft in DB is updated with AI-extracted content.
    Retrieve the updated parse result via GET /parse-result/{parse_task_id}.
    """
    if not settings.llm_base_url:
        raise HTTPException(status_code=422, detail="LLM not configured: LLM_BASE_URL is empty")

    draft = get_draft_by_task_id(db, parse_task_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found for this parse_task_id")

    user_info = {"id": current_user.id, "username": current_user.username}
    result = extract_vib_blocks.delay(parse_task_id, user_info)
    return TaskLaunchResponse(task_id=result.id)


# ---------------------------------------------------------------------------
# GET /drafts — list all open (unconfirmed) drafts
# ---------------------------------------------------------------------------

@router.get("/drafts", response_model=list[VibDraftSchema], dependencies=[_require_editor])
def list_vib_drafts(db: Session = Depends(get_db)):
    """Return metadata for all unconfirmed VIB drafts, newest first."""
    return list_drafts(db)


# ---------------------------------------------------------------------------
# DELETE /drafts/{task_id} — discard a draft
# ---------------------------------------------------------------------------

@router.delete("/drafts/{task_id}", status_code=204)
def delete_vib_draft(
    task_id: str,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Discard an unconfirmed VIB draft."""
    draft = get_draft_by_task_id(db, task_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Entwurf nicht gefunden")
    delete_draft(db, task_id)
    db.commit()


# ---------------------------------------------------------------------------
# PATCH /draft/{parse_task_id} — persist review edits across sessions
# ---------------------------------------------------------------------------

@router.patch("/draft/{parse_task_id}", status_code=204, dependencies=[_require_editor])
def save_vib_draft(
    parse_task_id: str,
    body: VibParseTaskResult,
    db: Session = Depends(get_db),
):
    """Overwrite the draft's raw_result_json with the current review state.

    Called by the review UI to persist edits so work survives page reloads.
    """
    updated = update_draft_ai_result(db, parse_task_id, body.model_dump_json())
    if not updated:
        raise HTTPException(status_code=404, detail="Draft nicht gefunden")
    db.commit()


# ---------------------------------------------------------------------------
# POST /extract-ai/{parse_task_id}/entry/{entry_idx} — retry AI for one entry
# ---------------------------------------------------------------------------

@router.post(
    "/extract-ai/{parse_task_id}/entry/{entry_idx}",
    response_model=VibEntryProposed,
    dependencies=[_require_editor],
)
def retry_vib_ai_for_entry(
    parse_task_id: str,
    entry_idx: int,
    db: Session = Depends(get_db),
):
    """Re-run LLM extraction synchronously for a single entry and persist the result."""
    from dashboard_backend.tasks.vib_ai_extraction import (
        _USER_PROMPT_TEMPLATE,
        _call_llm,
        _merge_ai_result,
    )

    if not settings.llm_base_url:
        raise HTTPException(status_code=422, detail="LLM nicht konfiguriert: LLM_BASE_URL fehlt")

    draft = get_draft_by_task_id(db, parse_task_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft nicht gefunden")

    result = VibParseTaskResult.model_validate_json(draft.raw_result_json)
    if entry_idx < 0 or entry_idx >= len(result.entries):
        raise HTTPException(
            status_code=422,
            detail=f"entry_idx {entry_idx} außerhalb des gültigen Bereichs (0–{len(result.entries) - 1})",
        )

    entry_dict = result.entries[entry_idx].model_dump()
    raw_text = entry_dict.get("raw_text") or ""
    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Kein Rohtext für diesen Eintrag — KI-Extraktion nicht möglich",
        )

    prompt = _USER_PROMPT_TEMPLATE.format(
        vib_section=entry_dict.get("vib_section") or "?",
        vib_name_raw=entry_dict.get("vib_name_raw") or "?",
        raw_text=raw_text[:6000],
    )
    try:
        ai_result = _call_llm(prompt)
        entry_dict = _merge_ai_result(entry_dict, ai_result)
        entry_dict["ai_extraction_failed"] = False
        entry_dict["ai_extraction_error"] = None
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM-Aufruf fehlgeschlagen: {exc}")

    updated_entries = list(result.entries)
    updated_entries[entry_idx] = VibEntryProposed(**entry_dict)
    updated_result = VibParseTaskResult(
        year=result.year,
        drucksache_nr=result.drucksache_nr,
        report_date=result.report_date,
        entries=updated_entries,
    )
    update_draft_ai_result(db, parse_task_id, updated_result.model_dump_json())
    db.commit()

    return updated_entries[entry_idx]


# ---------------------------------------------------------------------------
# GET /draft/{task_id}/image/{image_id} — serve a single OCR image
# ---------------------------------------------------------------------------

@router.get("/draft/{task_id}/image/{image_id:path}", dependencies=[_require_editor])
def get_vib_draft_image(task_id: str, image_id: str, db: Session = Depends(get_db)):
    """Return a single OCR image extracted from the Mistral OCR response.

    image_id matches the id returned by the OCR API, e.g. "img-0.jpeg".
    The image bytes are decoded from base64 and returned with the appropriate
    content type (image/jpeg or image/png).
    """
    draft = get_draft_by_task_id(db, task_id)
    if draft is None or not draft.ocr_images_json:
        raise HTTPException(status_code=404, detail="No images available for this draft")

    images: list[dict] = json.loads(draft.ocr_images_json)
    for img in images:
        if img.get("id") == image_id:
            img_bytes = base64.b64decode(img["image_base64"])
            lower_id = image_id.lower()
            if lower_id.endswith(".png"):
                media_type = "image/png"
            elif lower_id.endswith(".webp"):
                media_type = "image/webp"
            else:
                media_type = "image/jpeg"
            return Response(content=img_bytes, media_type=media_type)

    raise HTTPException(status_code=404, detail=f"Image {image_id!r} not found in draft")


# ---------------------------------------------------------------------------
# GET /draft/{task_id}/images — list all OCR image IDs for a draft
# ---------------------------------------------------------------------------

@router.get("/draft/{task_id}/images", dependencies=[_require_editor])
def list_vib_draft_images(task_id: str, db: Session = Depends(get_db)):
    """Return metadata for all OCR images extracted from a draft (id, page_index).

    Does NOT return base64 data — fetch individual images via
    GET /draft/{task_id}/image/{image_id}.
    """
    draft = get_draft_by_task_id(db, task_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if not draft.ocr_images_json:
        return []
    images: list[dict] = json.loads(draft.ocr_images_json)
    return [{"id": img["id"], "page_index": img["page_index"]} for img in images]


# ---------------------------------------------------------------------------
# GET /reports — list all imported VIB reports
# ---------------------------------------------------------------------------

@router.get(
    "/reports",
    response_model=list[VibReportSchema],
    dependencies=[_require_editor],
)
def list_vib_reports(db: Session = Depends(get_db)):
    """Return metadata for all imported VIB reports, newest year first."""
    reports = list_reports(db)
    return [
        VibReportSchema(
            id=r.id,
            year=r.year,
            drucksache_nr=r.drucksache_nr,
            report_date=r.report_date,
            imported_at=r.imported_at,
            entry_count=len(r.entries),
        )
        for r in reports
    ]


# ---------------------------------------------------------------------------
# DELETE /reports/{report_id} — remove a report and all its entries
# ---------------------------------------------------------------------------

@router.delete("/reports/{report_id}", status_code=204)
def delete_vib_report(
    report_id: int,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Delete a VIB report and all associated VibEntry / VibPfaEntry rows."""
    deleted = delete_report(db, report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="VIB-Bericht nicht gefunden")
    db.commit()
