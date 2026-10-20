"""Infraplan import: upload, parse drafts, review, confirmation, years, KPIs.

See docs/features/feature-infraplan-import.md ("API"). The MCP tools
(``mcp/tools/infraplan.py``) call the same CRUD functions.
"""

from __future__ import annotations

from fastapi import Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from dashboard_backend.api.deps import read_upload_within_limit
from dashboard_backend.core.security import require_permission
from dashboard_backend.crud import infraplan as infraplan_crud
from dashboard_backend.crud import infraplan_import as crud
from dashboard_backend.crud.infraplan_import import (
    InfraplanConflictError,
    InfraplanNotFoundError,
    create_parse_result,
    delete_parse_result,
    get_parse_result,
    list_parse_results,
    row_count,
)
from dashboard_backend.database import get_db
from dashboard_backend.models.infraplan import InfraplanParseResult
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.infraplan import (
    InfraplanKpiApproveResult,
    InfraplanKpiSchema,
    InfraplanKpiValueSchema,
    InfraplanKpiValuesResult,
    InfraplanKpiValuesUpdate,
)
from dashboard_backend.schemas.infraplan_import import (
    InfraplanApplyResult,
    InfraplanApplySuggestions,
    InfraplanConfirmRequest,
    InfraplanConfirmResult,
    InfraplanParsedRow,
    InfraplanParseLaunchResponse,
    InfraplanParseResultListItem,
    InfraplanParseResultSchema,
    InfraplanReportSchema,
    InfraplanRowPatch,
    InfraplanSubprojectCreate,
    InfraplanSubprojectResult,
)
from dashboard_backend.utils.file_storage import (
    delete_infraplan_pdf,
    infraplan_pdf_exists,
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
    task_id = crud.launch_parse(db, record)
    return InfraplanParseLaunchResponse(task_id=task_id, parse_result_id=record.id)


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
    try:
        crud.check_reparse(record)
    except InfraplanConflictError as exc:
        raise _errors(exc) from exc
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
        item.assigned_count = crud.assigned_count(record)
        items.append(item)
    return items


@router.get(
    "/parse-result/{parse_result_id}",
    response_model=InfraplanParseResultSchema,
    dependencies=[_require_importer],
)
def get_draft(parse_result_id: int, db: Session = Depends(get_db)):
    """A draft with its rows, the projects they reference and the projects
    of the previous year that have no row in it."""
    record = _get_or_404(db, parse_result_id)
    return draft_schema(db, record)


def draft_schema(db: Session, record: InfraplanParseResult) -> InfraplanParseResultSchema:
    item = InfraplanParseResultSchema.model_validate(record)
    item.row_count = row_count(record)
    item.has_pdf = infraplan_pdf_exists(record.pdf_path)
    item.projects = crud.draft_projects(db, record)
    item.previous_year, item.missing_from_previous = crud.missing_from_previous(db, record)
    item.assigned_count = crud.assigned_count(record)
    item.report_year_exists = crud.get_report_by_year(db, record.year) is not None
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
    record = _get_or_404(db, parse_result_id)
    try:
        png = crud.render_page(record, page, dpi)
    except InfraplanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


# ---------------------------------------------------------------------------
# Review (stage 2): rows, suggestions, subprojects
# ---------------------------------------------------------------------------


def _errors(exc: Exception) -> HTTPException:
    if isinstance(exc, InfraplanNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=409, detail=str(exc))


@router.patch(
    "/parse-result/{parse_result_id}/rows/{row_key}",
    response_model=InfraplanParsedRow,
)
def patch_row(
    parse_result_id: int,
    row_key: str,
    body: InfraplanRowPatch,
    current_user: User = Depends(require_permission("infraplan.import")),
    db: Session = Depends(get_db),
):
    """Change the projects (``project_ids`` replaces) and/or values of a row."""
    record = _get_or_404(db, parse_result_id)
    try:
        return crud.patch_row(
            db, record, row_key, body, source="MANUAL", username=current_user.username
        )
    except (InfraplanNotFoundError, InfraplanConflictError) as exc:
        raise _errors(exc) from exc


@router.post(
    "/parse-result/{parse_result_id}/apply-suggestions",
    response_model=InfraplanApplyResult,
)
def apply_suggestions(
    parse_result_id: int,
    body: InfraplanApplySuggestions,
    current_user: User = Depends(require_permission("infraplan.import")),
    db: Session = Depends(get_db),
):
    """Assign the suggested projects from ``min_confidence`` on."""
    record = _get_or_404(db, parse_result_id)
    try:
        applied, unassigned = crud.apply_suggestions(
            db,
            record,
            body.min_confidence,
            only_unassigned=body.only_unassigned,
            username=current_user.username,
        )
    except InfraplanConflictError as exc:
        raise _errors(exc) from exc
    return InfraplanApplyResult(applied=applied, unassigned=unassigned)


@router.post(
    "/parse-result/{parse_result_id}/rows/{row_key}/subproject",
    response_model=InfraplanSubprojectResult,
)
def create_subproject(
    parse_result_id: int,
    row_key: str,
    body: InfraplanSubprojectCreate,
    current_user: User = Depends(require_permission("infraplan.import")),
    db: Session = Depends(get_db),
):
    """Create a subproject under ``parent_id`` — or, without, a project of its
    own — named after the row unless ``name`` is given, and assign the row to
    it. Only on an open draft; confirmed years go through „Offene Zuordnungen“."""
    record = _get_or_404(db, parse_result_id)
    if record.confirmed_at is not None:
        raise _errors(InfraplanConflictError("Der Entwurf ist bereits übernommen."))
    try:
        project, row = crud.create_subproject(
            db, record, row_key, body.parent_id, body.name, source="MANUAL", user=current_user
        )
    except (InfraplanNotFoundError, InfraplanConflictError) as exc:
        raise _errors(exc) from exc
    return InfraplanSubprojectResult(project_id=project.id, name=project.name, row=row)


# ---------------------------------------------------------------------------
# Confirmation and years
# ---------------------------------------------------------------------------


@router.post("/confirm", response_model=InfraplanConfirmResult)
def confirm(
    body: InfraplanConfirmRequest,
    current_user: User = Depends(require_permission("infraplan.import")),
    db: Session = Depends(get_db),
):
    """Take over a reviewed draft as its year. 409 when the year exists or the
    parser left warnings (``force`` overrides the warnings only)."""
    record = _get_or_404(db, body.parse_result_id)
    try:
        return crud.confirm_parse_result(
            db,
            record,
            published_on=body.published_on,
            title=body.title,
            force=body.force,
            user=current_user,
        )
    except (InfraplanNotFoundError, InfraplanConflictError) as exc:
        raise _errors(exc) from exc


@router.get(
    "/report",
    response_model=list[InfraplanReportSchema],
    dependencies=[_require_importer],
)
def list_reports(db: Session = Depends(get_db)):
    return crud.list_reports(db)


@router.delete("/report/{year}", status_code=204, dependencies=[_require_importer])
def delete_report(year: int, db: Session = Depends(get_db)):
    """Delete one year (entries, links, KPI values); other years stay. Its
    draft can be confirmed again afterwards."""
    report = crud.get_report_by_year(db, year)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Den Infraplan {year} gibt es nicht.")
    crud.delete_report(db, report)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# KPI values (stage 4)
# ---------------------------------------------------------------------------


def _report_or_404(db: Session, year: int):
    report = crud.get_report_by_year(db, year)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Den Infraplan {year} gibt es nicht.")
    return report


@router.get("/kpis", response_model=list[InfraplanKpiSchema], dependencies=[_require_importer])
def list_kpis(db: Session = Depends(get_db)):
    """All KPI definitions (the defaults of the Infraplan 2026 are created on
    first use)."""
    return infraplan_crud.list_kpis(db)


@router.get(
    "/report/{year}/kpi-values",
    response_model=list[InfraplanKpiValueSchema],
    dependencies=[_require_importer],
)
def get_kpi_values(year: int, db: Session = Depends(get_db)):
    """Every value of a year, checked or not (form and approval view)."""
    return infraplan_crud.kpi_values(db, _report_or_404(db, year))


@router.put("/report/{year}/kpi-values", response_model=InfraplanKpiValuesResult)
def put_kpi_values(
    year: int,
    body: InfraplanKpiValuesUpdate,
    current_user: User = Depends(require_permission("infraplan.import")),
    db: Session = Depends(get_db),
):
    """Set values (value null removes one). Values entered here count as
    checked; the MCP path stores them unchecked."""
    report = _report_or_404(db, year)
    try:
        return infraplan_crud.set_kpi_values(
            db,
            report,
            [v.model_dump() for v in body.values],
            [d.model_dump() for d in body.definitions],
            status="GEPRUEFT",
            username=current_user.username,
        )
    except infraplan_crud.InfraplanKpiError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/report/{year}/kpi-values/approve",
    response_model=InfraplanKpiApproveResult,
    dependencies=[_require_importer],
)
def approve_kpi_values(year: int, db: Session = Depends(get_db)):
    """Mark every value of the year as checked — they become public."""
    return InfraplanKpiApproveResult(
        approved=infraplan_crud.approve_kpi_values(db, _report_or_404(db, year))
    )
