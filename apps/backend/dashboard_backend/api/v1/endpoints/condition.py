"""InfraGO-Zustandsbericht: public reads of the released years and the import
endpoints (upload, values, release).

See docs/features/feature-zustandsbericht.md ("REST-API"). The MCP tools in
``mcp/tools/condition.py`` call the same CRUD functions.
"""

from __future__ import annotations

from fastapi import Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from dashboard_backend.api.deps import read_upload_within_limit
from dashboard_backend.core.security import require_permission
from dashboard_backend.crud import condition as crud
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.condition import (
    ConditionAssetClassSchema,
    ConditionCheckResult,
    ConditionPublicReport,
    ConditionPublicYear,
    ConditionReleaseResult,
    ConditionReportCreate,
    ConditionReportSchema,
    ConditionSeriesValue,
    ConditionValueCorrection,
    ConditionValueCorrectionResult,
    ConditionValueSchema,
)

router = AuthRouter()
import_router = AuthRouter()

PERMISSION = "condition.import"
_require_importer = Depends(require_permission(PERMISSION))


def _errors(exc: Exception) -> HTTPException:
    if isinstance(exc, crud.ConditionNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=409, detail=str(exc))


def _released_or_404(db: Session, year: int):
    report = crud.get_report_by_year(db, year)
    if report is None or report.status != "FREIGEGEBEN":
        raise HTTPException(status_code=404, detail=f"Den Zustandsbericht {year} gibt es nicht.")
    return report


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------


@router.get("/reports", response_model=list[ConditionPublicReport])
def public_reports(db: Session = Depends(get_db)):
    """Released years, newest first."""
    return crud.list_reports(db, released_only=True)


@router.get("/reports/{year}", response_model=ConditionPublicYear)
def public_year(year: int, db: Session = Depends(get_db)):
    """Checked values of one released year with the asset classes."""
    report = _released_or_404(db, year)
    return {
        "report": crud.report_out(db, report),
        "classes": [crud.class_out(c) for c in crud.list_classes(db)],
        "values": crud.report_values(db, report, checked_only=True),
    }


@router.get("/series", response_model=list[ConditionSeriesValue])
def public_series(db: Session = Depends(get_db)):
    """Grades and headline figures over all released years (newest report
    wins per reference year)."""
    return crud.public_series(db)


# ---------------------------------------------------------------------------
# Import (condition.import)
# ---------------------------------------------------------------------------


def _report_or_404(db: Session, year: int):
    try:
        return crud.report_or_error(db, year)
    except crud.ConditionNotFoundError as exc:
        raise _errors(exc) from exc


@import_router.get("/reports", response_model=list[ConditionReportSchema], dependencies=[_require_importer])
def list_reports(db: Session = Depends(get_db)):
    return crud.list_reports(db)


@import_router.post("/reports", response_model=ConditionReportSchema, status_code=201)
def create_report(
    body: ConditionReportCreate,
    current_user: User = Depends(require_permission(PERMISSION)),
    db: Session = Depends(get_db),
):
    try:
        report = crud.create_report(db, **body.model_dump(), username=current_user.username)
    except crud.ConditionError as exc:
        raise _errors(exc) from exc
    return crud.report_out(db, report)


@import_router.post(
    "/reports/{year}/pdf", response_model=ConditionReportSchema, dependencies=[_require_importer]
)
async def upload_pdf(year: int, pdf: UploadFile = File(...), db: Session = Depends(get_db)):
    """Store the report's PDF — the agent reads page text and images from it."""
    report = _report_or_404(db, year)
    if pdf.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    pdf_bytes = await read_upload_within_limit(pdf)
    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Die Datei ist kein PDF.")
    crud.attach_pdf(db, report, pdf_bytes)
    return crud.report_out(db, report)


@import_router.get(
    "/reports/{year}/page/{page}.png",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
    dependencies=[_require_importer],
)
def page_image(year: int, page: int, dpi: int = Query(110, ge=50, le=200), db: Session = Depends(get_db)):
    """One page of the stored PDF as PNG (1-indexed)."""
    report = _report_or_404(db, year)
    try:
        png = crud.render_page(report, page, dpi)
    except crud.ConditionNotFoundError as exc:
        raise _errors(exc) from exc
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@import_router.get(
    "/reports/{year}/values", response_model=list[ConditionValueSchema], dependencies=[_require_importer]
)
def report_values(year: int, db: Session = Depends(get_db)):
    """Every value of a year, checked or not (release view)."""
    return crud.report_values(db, _report_or_404(db, year))


@import_router.get(
    "/classes", response_model=list[ConditionAssetClassSchema], dependencies=[_require_importer]
)
def list_classes(db: Session = Depends(get_db)):
    return [crud.class_out(c) for c in crud.list_classes(db)]


@import_router.get(
    "/reports/{year}/check", response_model=ConditionCheckResult, dependencies=[_require_importer]
)
def check_report(year: int, db: Session = Depends(get_db)):
    return crud.check_report(db, _report_or_404(db, year))


@import_router.patch("/values/{value_id}", response_model=ConditionValueCorrectionResult)
def correct_value(
    value_id: int,
    body: ConditionValueCorrection,
    current_user: User = Depends(require_permission(PERMISSION)),
    db: Session = Depends(get_db),
):
    """Correct one value; it counts as checked. Broken sums come back as warnings."""
    try:
        return crud.correct_value(db, value_id, body.value, current_user.username)
    except crud.ConditionError as exc:
        raise _errors(exc) from exc


@import_router.delete("/values/{value_id}", status_code=204, dependencies=[_require_importer])
def delete_value(value_id: int, db: Session = Depends(get_db)):
    try:
        crud.delete_value(db, value_id)
    except crud.ConditionError as exc:
        raise _errors(exc) from exc
    return Response(status_code=204)


@import_router.post("/reports/{year}/release", response_model=ConditionReleaseResult)
def release_report(
    year: int,
    current_user: User = Depends(require_permission(PERMISSION)),
    db: Session = Depends(get_db),
):
    """Mark every value as checked and publish the year on /netzzustand."""
    report = _report_or_404(db, year)
    return {"released": crud.release_report(db, report, current_user.username)}


@import_router.delete("/reports/{year}", status_code=204, dependencies=[_require_importer])
def delete_report(year: int, db: Session = Depends(get_db)):
    """Delete one year with all its values and the stored PDF."""
    crud.delete_report(db, _report_or_404(db, year))
    return Response(status_code=204)
