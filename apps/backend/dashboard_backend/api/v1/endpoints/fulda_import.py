"""Fulda-Runde importer endpoints (#46).

Mounted under ``/import/fulda``. Upload a Kleine-Anfrage PDF for OCR + LLM
extraction into draft announcements, review/edit/match them, then confirm to
materialise FULDA_RUNDE observations. All actions require ``progress.edit``.
"""

from __future__ import annotations

from fastapi import Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_permission
from dashboard_backend.crud import fulda as fulda_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.fulda import (
    FuldaEntrySchema,
    FuldaParseSummary,
    FuldaUpdateInput,
)

router = AuthRouter()

_require_edit = Depends(require_permission("progress.edit"))


@router.post("/parse", response_model=FuldaParseSummary, dependencies=[_require_edit])
async def parse_fulda(
    pdf: UploadFile = File(...),
    current_user: User = Depends(require_permission("progress.edit")),
    db: Session = Depends(get_db),
):
    """Upload a Fulda Kleine-Anfrage PDF; OCR + LLM extract draft announcements."""
    pdf_bytes = await pdf.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Leere Datei")
    try:
        return fulda_crud.parse_and_store(db, pdf_bytes=pdf_bytes, user=current_user)
    except Exception as exc:  # noqa: BLE001 - OCR/LLM failures surface as 502
        raise HTTPException(status_code=502, detail=f"Fulda-Parsing fehlgeschlagen: {exc}") from exc


@router.get("/entries", response_model=list[FuldaEntrySchema], dependencies=[_require_edit])
def list_fulda_entries(
    only_unconfirmed: bool = Query(False),
    db: Session = Depends(get_db),
):
    """List Fulda announcements with suggested / confirmed matches."""
    return fulda_crud.list_entries(db, only_unconfirmed=only_unconfirmed)


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
