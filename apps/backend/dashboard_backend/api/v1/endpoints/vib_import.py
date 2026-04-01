from __future__ import annotations

from fastapi import Depends, File, Form, HTTPException, UploadFile
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
    list_reports,
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
    VibParseTaskResult,
    VibReportSchema,
)
from dashboard_backend.tasks.vib import parse_vib_pdf
from dashboard_backend.tasks.vib_ai_extraction import extract_vib_blocks

router = AuthRouter()

_require_editor = Depends(require_roles(UserRole.editor, UserRole.admin))


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
# POST /parse — start PDF parse task
# ---------------------------------------------------------------------------

@router.post("/parse", response_model=TaskLaunchResponse, dependencies=[_require_editor])
async def start_vib_parse(
    pdf: UploadFile = File(...),
    year: int = Form(...),
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
):
    """Upload a VIB PDF and start a background parse task.

    Returns the Celery task_id for polling via GET /api/v1/tasks/{task_id}.
    Once the task is in SUCCESS state, retrieve the parse result via
    GET /import/vib/parse-result/{task_id}.
    """
    pdf_bytes = await pdf.read()
    user_info = {"id": current_user.id, "username": current_user.username}
    result = parse_vib_pdf.delay(pdf_bytes, year, pdf.filename or "upload.pdf", user_info)
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
        draft = get_draft_by_task_id(db, task_id)
        if draft is None:
            raise HTTPException(status_code=202, detail=f"Task state: {async_result.state}")
        return VibParseTaskResult.model_validate_json(draft.raw_result_json)

    if async_result.state == "FAILURE":
        raise HTTPException(
            status_code=422,
            detail=f"Parse task failed: {async_result.result}",
        )

    if async_result.state == "SUCCESS":
        raw = async_result.result
        if isinstance(raw, dict):
            return VibParseTaskResult.model_validate(raw)

    # Redis result gone (PENDING after eviction) — fall back to DB
    draft = get_draft_by_task_id(db, task_id)
    if draft is not None:
        return VibParseTaskResult.model_validate_json(draft.raw_result_json)

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
