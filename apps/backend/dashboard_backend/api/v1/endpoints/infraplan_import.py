"""Infraplan import, stage 1: upload, parse drafts, page images.

See docs/features/feature-infraplan-import.md ("API"). Review, confirmation
and KPI values follow in later stages.
"""

from __future__ import annotations

from fastapi import Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from dashboard_backend.api.deps import read_upload_within_limit
from dashboard_backend.core.security import require_permission
from dashboard_backend.crud.infraplan_import import (
    create_parse_result,
    delete_parse_result,
    get_parse_result,
    list_parse_results,
    mark_parse_failed,
    mark_parse_pending,
    row_count,
)
from dashboard_backend.database import get_db
from dashboard_backend.models.infraplan import InfraplanParseResult
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.infraplan_import import (
    InfraplanParseLaunchResponse,
    InfraplanParseResultListItem,
    InfraplanParseResultSchema,
)
from dashboard_backend.tasks.infraplan import parse_infraplan_pdf
from dashboard_backend.utils.file_storage import (
    delete_infraplan_pdf,
    infraplan_pdf_exists,
    read_infraplan_pdf,
    save_infraplan_pdf,
)

router = AuthRouter()

_require_importer = Depends(require_permission("infraplan.import"))

PARSE_RESULT_NOT_FOUND = "Infraplan-Entwurf nicht gefunden"


def _get_or_404(db: Session, parse_result_id: int) -> InfraplanParseResult:
    record = get_parse_result(db, parse_result_id)
    if record is None:
        raise HTTPException(status_code=404, detail=PARSE_RESULT_NOT_FOUND)
    return record


def _launch(db: Session, record: InfraplanParseResult) -> InfraplanParseLaunchResponse:
    """Start the parse task for a committed draft and remember its task id."""
    try:
        result = parse_infraplan_pdf.delay(record.id)
    except Exception as exc:
        mark_parse_failed(db, record, f"Auslesen konnte nicht gestartet werden: {exc}")
        db.commit()
        raise
    mark_parse_pending(record, result.id)
    db.commit()
    return InfraplanParseLaunchResponse(task_id=result.id, parse_result_id=record.id)


# ---------------------------------------------------------------------------
# POST /parse — upload and start parsing
# ---------------------------------------------------------------------------


@router.post("/parse", response_model=InfraplanParseLaunchResponse)
async def start_parse(
    pdf: UploadFile = File(...),
    year: int = Form(..., ge=2000, le=2100),
    current_user: User = Depends(require_permission("infraplan.import")),
    db: Session = Depends(get_db),
):
    """Upload an Infraplan PDF; the parse task starts right away.

    The PDF is stored with the draft (re-parse, page images). Poll the task via
    GET /api/v1/tasks/{task_id}, then load the draft by ``parse_result_id``.
    """
    if pdf.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    pdf_bytes = await read_upload_within_limit(pdf)
    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Die Datei ist kein PDF.")

    record = create_parse_result(db, year, pdf.filename or "infraplan.pdf", current_user)
    record.pdf_path = save_infraplan_pdf(record.id, pdf_bytes)
    try:
        db.commit()
    except Exception:
        delete_infraplan_pdf(record.pdf_path)
        raise
    return _launch(db, record)


# ---------------------------------------------------------------------------
# POST /parse-result/{id}/reparse — parse the stored PDF again
# ---------------------------------------------------------------------------


@router.post(
    "/parse-result/{parse_result_id}/reparse",
    response_model=InfraplanParseLaunchResponse,
    dependencies=[_require_importer],
)
def reparse(parse_result_id: int, db: Session = Depends(get_db)):
    record = _get_or_404(db, parse_result_id)
    if record.confirmed_at is not None:
        raise HTTPException(
            status_code=409, detail="Der Entwurf ist bereits übernommen und wird nicht neu ausgelesen."
        )
    if not infraplan_pdf_exists(record.pdf_path):
        raise HTTPException(
            status_code=409, detail="Zu diesem Entwurf ist kein PDF mehr gespeichert. Bitte neu hochladen."
        )
    return _launch(db, record)


# ---------------------------------------------------------------------------
# GET /parse-result, GET/DELETE /parse-result/{id}
# ---------------------------------------------------------------------------


@router.get(
    "/parse-result",
    response_model=list[InfraplanParseResultListItem],
    dependencies=[_require_importer],
)
def list_drafts(db: Session = Depends(get_db)):
    """All drafts without their rows, newest first."""
    items = []
    for record in list_parse_results(db):
        item = InfraplanParseResultListItem.model_validate(record)
        item.row_count = row_count(record)
        items.append(item)
    return items


@router.get(
    "/parse-result/{parse_result_id}",
    response_model=InfraplanParseResultSchema,
    dependencies=[_require_importer],
)
def get_draft(parse_result_id: int, db: Session = Depends(get_db)):
    record = _get_or_404(db, parse_result_id)
    item = InfraplanParseResultSchema.model_validate(record)
    item.row_count = row_count(record)
    item.has_pdf = infraplan_pdf_exists(record.pdf_path)
    return item


@router.delete(
    "/parse-result/{parse_result_id}",
    status_code=204,
    dependencies=[_require_importer],
)
def delete_draft(parse_result_id: int, db: Session = Depends(get_db)):
    """Discard a draft and its stored PDF. A confirmed draft belongs to an
    imported year and is removed together with that year, not here."""
    record = _get_or_404(db, parse_result_id)
    if record.confirmed_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Der Entwurf ist bereits übernommen; bitte den Jahrgang löschen.",
        )
    pdf_path = delete_parse_result(db, record)
    db.commit()
    delete_infraplan_pdf(pdf_path)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# GET /parse-result/{id}/page/{page}.png — page image (KPI review, MCP)
# ---------------------------------------------------------------------------


@router.get(
    "/parse-result/{parse_result_id}/page/{page}.png",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
    dependencies=[_require_importer],
)
def page_image(
    parse_result_id: int,
    page: int,
    dpi: int = Query(110, ge=50, le=200),
    db: Session = Depends(get_db),
):
    """Render one page of the stored PDF as PNG (1-indexed)."""
    import fitz  # pymupdf

    record = _get_or_404(db, parse_result_id)
    try:
        pdf_bytes = read_infraplan_pdf(record.pdf_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Zu diesem Entwurf ist kein PDF gespeichert.")
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if not 1 <= page <= doc.page_count:
            raise HTTPException(
                status_code=404, detail=f"Seite {page} gibt es nicht (1–{doc.page_count})."
            )
        png = doc[page - 1].get_pixmap(dpi=dpi).tobytes("png")
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})
