"""Medien/Presse importer endpoints (#48).

Mounted under ``/import/media``. Semi-automatic: submit an article URL/text for
(optional) LLM extraction, review/edit the draft, then confirm to materialise a
low-trust derived MEDIEN observation. All actions require ``progress.edit``.
"""

from __future__ import annotations

import httpx
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_permission
from dashboard_backend.crud import media as media_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.media import (
    MediaEntrySchema,
    MediaExtractInput,
    MediaUpdateInput,
)

router = AuthRouter()

_require_edit = Depends(require_permission("progress.edit"))


@router.post("/extract", response_model=MediaEntrySchema, dependencies=[_require_edit])
def extract_media(
    body: MediaExtractInput,
    current_user: User = Depends(require_permission("progress.edit")),
    db: Session = Depends(get_db),
):
    """Create a draft media report from a URL and/or text (LLM-assisted)."""
    try:
        return media_crud.create_from_input(
            db, url=body.url, text=body.text, user=current_user
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Artikel konnte nicht geladen werden: {exc}"
        ) from exc


@router.get("/entries", response_model=list[MediaEntrySchema], dependencies=[_require_edit])
def list_media_entries(
    only_unconfirmed: bool = Query(False),
    db: Session = Depends(get_db),
):
    """List media reports with resolved suggestion / match names."""
    return media_crud.list_entries(db, only_unconfirmed=only_unconfirmed)


@router.patch("/entries/{entry_id}", response_model=MediaEntrySchema, dependencies=[_require_edit])
def update_media_entry(
    entry_id: int,
    body: MediaUpdateInput,
    db: Session = Depends(get_db),
):
    """Edit fields / confirm the match for one media report."""
    try:
        entry = media_crud.update_entry(db, entry_id, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if entry is None:
        raise HTTPException(status_code=404, detail="Medienbericht nicht gefunden")
    return entry


@router.delete("/entries/{entry_id}", status_code=204, dependencies=[_require_edit])
def delete_media_entry(entry_id: int, db: Session = Depends(get_db)):
    """Delete a media report (and drop its derived observation)."""
    if not media_crud.delete_entry(db, entry_id):
        raise HTTPException(status_code=404, detail="Medienbericht nicht gefunden")
