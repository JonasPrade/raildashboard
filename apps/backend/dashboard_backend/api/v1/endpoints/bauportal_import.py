"""DB-Bauportal importer endpoints (#47).

Mounted under ``/import/bauportal``. All actions require ``progress.edit``:
fetching refreshes the raw table from the public Bauportal API, the entry list
backs the review UI, and confirming a match links a Bauportal record to one of
our projects (which materialises a derived BAUPORTAL observation).
"""

from __future__ import annotations

import httpx
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_permission
from dashboard_backend.crud import bauportal as bauportal_crud
from dashboard_backend.database import get_db
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.bauportal import (
    BauportalConfirmInput,
    BauportalEntrySchema,
    BauportalImportSummary,
)

router = AuthRouter()

_require_edit = Depends(require_permission("progress.edit"))


@router.post("/fetch", response_model=BauportalImportSummary, dependencies=[_require_edit])
def fetch_bauportal(db: Session = Depends(get_db)):
    """Fetch the public Bauportal project list and upsert the raw table."""
    try:
        return bauportal_crud.run_import(db)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502, detail=f"Bauportal-Abruf fehlgeschlagen: {exc}"
        ) from exc


@router.get("/entries", response_model=list[BauportalEntrySchema], dependencies=[_require_edit])
def list_bauportal_entries(
    only_unconfirmed: bool = Query(False),
    db: Session = Depends(get_db),
):
    """List fetched Bauportal entries with suggested / confirmed matches."""
    return bauportal_crud.list_entries(db, only_unconfirmed=only_unconfirmed)


@router.patch("/entries/{entry_id}", response_model=BauportalEntrySchema, dependencies=[_require_edit])
def confirm_bauportal_match(
    entry_id: int,
    body: BauportalConfirmInput,
    db: Session = Depends(get_db),
):
    """Set or clear the confirmed project match for one entry."""
    try:
        entry = bauportal_crud.confirm_match(db, entry_id, body.project_id)
    except bauportal_crud.ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if entry is None:
        raise HTTPException(status_code=404, detail="Bauportal-Eintrag nicht gefunden")
    return entry
