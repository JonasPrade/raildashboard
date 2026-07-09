"""Fulda-Runde importer endpoints (#46).

Mounted under ``/import/fulda``. Upload a Kleine-Anfrage PDF for OCR + LLM
extraction into draft announcements, review/edit/match them, then confirm to
materialise FULDA_RUNDE observations. All actions require ``progress.edit``.
"""

from __future__ import annotations

from fastapi import Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_permission
from dashboard_backend.crud import fulda as fulda_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.fulda import (
    FuldaConfirmSummary,
    FuldaEntrySchema,
    FuldaParseSummary,
    FuldaUpdateInput,
    FuldaYearSummary,
)

router = AuthRouter()

_require_edit = Depends(require_permission("progress.edit"))


@router.post("/parse", response_model=FuldaParseSummary)
async def parse_fulda(
    pdf: UploadFile = File(...),
    year: int = Form(...),
    current_user: User = Depends(require_permission("progress.edit")),
    db: Session = Depends(get_db),
):
    """Upload a Fulda Kleine-Anfrage PDF for ``year``; OCR + LLM extract drafts."""
    pdf_bytes = await pdf.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Leere Datei")
    try:
        return fulda_crud.parse_and_store(
            db, pdf_bytes=pdf_bytes, year=year, user=current_user
        )
    except Exception as exc:  # noqa: BLE001 - OCR/LLM failures surface as 502
        raise HTTPException(status_code=502, detail=f"Fulda-Parsing fehlgeschlagen: {exc}") from exc


@router.get("/years", response_model=list[int], dependencies=[_require_edit])
def list_fulda_years(db: Session = Depends(get_db)):
    """Distinct Fulda-Runde years present (newest first)."""
    return fulda_crud.list_years(db)


@router.get(
    "/year-summaries",
    response_model=list[FuldaYearSummary],
    dependencies=[_require_edit],
)
def list_fulda_year_summaries(db: Session = Depends(get_db)):
    """Per-year overview rows (counts + provenance) for the landing table."""
    return fulda_crud.list_year_summaries(db)


@router.post(
    "/years/{year}/confirm",
    response_model=FuldaConfirmSummary,
    dependencies=[_require_edit],
)
def confirm_fulda_year(year: int, db: Session = Depends(get_db)):
    """Confirm all assigned, still-open entries of a year in one step."""
    return {"confirmed": fulda_crud.confirm_year(db, year)}


@router.delete("/years/{year}", status_code=204, dependencies=[_require_edit])
def delete_fulda_year(year: int, db: Session = Depends(get_db)):
    """Delete all Fulda announcements of a year (and their derived observations)."""
    deleted = fulda_crud.delete_year(db, year)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"Keine Fulda-Einträge für {year}")


@router.get("/entries", response_model=list[FuldaEntrySchema], dependencies=[_require_edit])
def list_fulda_entries(
    only_unconfirmed: bool = Query(False),
    year: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """List Fulda announcements with suggested / confirmed matches."""
    return fulda_crud.list_entries(db, only_unconfirmed=only_unconfirmed, year=year)


@router.patch("/entries/{entry_id}", response_model=FuldaEntrySchema, dependencies=[_require_edit])
def update_fulda_entry(
    entry_id: int,
    body: FuldaUpdateInput,
    db: Session = Depends(get_db),
):
    """Edit fields / confirm the match for one announcement."""
    try:
        entry = fulda_crud.update_entry(db, entry_id, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if entry is None:
        raise HTTPException(status_code=404, detail="Fulda-Eintrag nicht gefunden")
    return entry


@router.delete("/entries/{entry_id}", status_code=204, dependencies=[_require_edit])
def delete_fulda_entry(entry_id: int, db: Session = Depends(get_db)):
    """Delete a Fulda announcement (and drop its derived observation)."""
    if not fulda_crud.delete_entry(db, entry_id):
        raise HTTPException(status_code=404, detail="Fulda-Eintrag nicht gefunden")
