"""Fulda-Runde importer endpoints (feature-fulda-import.md).

Mounted under ``/import/fulda``. Fulda answers are read by an agent over MCP
(``mcp/tools/fulda.py``); these endpoints serve the human review: year and
document overview, per-entry assignment, confirm, delete. All actions require
``fulda.import``.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_permission
from dashboard_backend.crud import fulda as fulda_crud
from dashboard_backend.crud._importer_common import ProjectNotFoundError
from dashboard_backend.database import get_db
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.fulda import (
    FuldaCategorySchema,
    FuldaConfirmSummary,
    FuldaDocumentSchema,
    FuldaEntrySchema,
    FuldaUpdateInput,
    FuldaYearSummary,
)
from dashboard_backend.services.fulda_categories import FULDA_CATEGORY_LIST

router = AuthRouter()

_require_import = Depends(require_permission("fulda.import"))


@router.get("/categories", response_model=list[FuldaCategorySchema], dependencies=[_require_import])
def list_fulda_categories():
    """Category catalog in display order (meaning, statement kind, phase)."""
    return [
        {
            "key": c.key,
            "label": c.label,
            "statement_kind": c.kind,
            "phase": c.phase.value if c.phase else None,
        }
        for c in FULDA_CATEGORY_LIST
    ]


@router.get("/years", response_model=list[int], dependencies=[_require_import])
def list_fulda_years(db: Session = Depends(get_db)):
    """Distinct Fulda-Runde years present (newest first)."""
    return fulda_crud.list_years(db)


@router.get(
    "/year-summaries",
    response_model=list[FuldaYearSummary],
    dependencies=[_require_import],
)
def list_fulda_year_summaries(db: Session = Depends(get_db)):
    """Per-year overview rows (counts + documents) for the landing table."""
    return fulda_crud.list_year_summaries(db)


@router.get("/documents", response_model=list[FuldaDocumentSchema], dependencies=[_require_import])
def list_fulda_documents(year: int | None = Query(None), db: Session = Depends(get_db)):
    """Evaluated Fulda answers with entry counters, newest first."""
    return fulda_crud.list_documents(db, year=year)


@router.post(
    "/years/{year}/confirm",
    response_model=FuldaConfirmSummary,
    dependencies=[_require_import],
)
def confirm_fulda_year(year: int, db: Session = Depends(get_db)):
    """Confirm all assigned, still-open entries of a year in one step."""
    return {"confirmed": fulda_crud.confirm_year(db, year)}


@router.delete("/years/{year}", status_code=204, dependencies=[_require_import])
def delete_fulda_year(year: int, db: Session = Depends(get_db)):
    """Delete all Fulda documents and entries of a year (and their observations)."""
    deleted = fulda_crud.delete_year(db, year)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"Keine Fulda-Einträge für {year}")


@router.get("/entries", response_model=list[FuldaEntrySchema], dependencies=[_require_import])
def list_fulda_entries(
    only_unconfirmed: bool = Query(False),
    year: int | None = Query(None),
    document_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """List Fulda announcements with their (suggested or confirmed) projects."""
    return fulda_crud.list_entries(
        db, only_unconfirmed=only_unconfirmed, year=year, document_id=document_id
    )


@router.patch(
    "/entries/{entry_id}", response_model=FuldaEntrySchema, dependencies=[_require_import]
)
def update_fulda_entry(
    entry_id: int,
    body: FuldaUpdateInput,
    db: Session = Depends(get_db),
):
    """Edit fields / confirm the match for one announcement."""
    try:
        entry = fulda_crud.update_entry(db, entry_id, body.model_dump(exclude_unset=True))
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except fulda_crud.FuldaValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if entry is None:
        raise HTTPException(status_code=404, detail="Fulda-Eintrag nicht gefunden")
    return entry


@router.delete("/entries/{entry_id}", status_code=204, dependencies=[_require_import])
def delete_fulda_entry(entry_id: int, db: Session = Depends(get_db)):
    """Delete a Fulda announcement (and drop its derived observation)."""
    if not fulda_crud.delete_entry(db, entry_id):
        raise HTTPException(status_code=404, detail="Fulda-Eintrag nicht gefunden")
