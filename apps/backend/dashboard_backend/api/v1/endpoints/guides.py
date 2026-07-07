"""Guide-section override endpoints ("Anleitungen" editing).

Mounted under ``/guides``. The guide *content* ships as markdown defaults in
the frontend bundle; these endpoints only store per-section replacements.
Reading is public (the defaults are public in the JS bundle anyway); writing
requires the ``guides.edit`` capability.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_permission
from dashboard_backend.crud import guides as guides_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.guides import GuideOverrideInput, GuideOverrideSchema

router = AuthRouter()

_require_edit = Depends(require_permission("guides.edit"))


@router.get("/{guide_slug}/overrides", response_model=list[GuideOverrideSchema])
def list_guide_overrides(guide_slug: str, db: Session = Depends(get_db)):
    """All edited sections of one guide (empty list = pure defaults)."""
    return guides_crud.list_overrides(db, guide_slug)


@router.put(
    "/{guide_slug}/overrides/{section_key}",
    response_model=GuideOverrideSchema,
    dependencies=[_require_edit],
)
def put_guide_override(
    guide_slug: str,
    section_key: str,
    body: GuideOverrideInput,
    current_user: User = Depends(require_permission("guides.edit")),
    db: Session = Depends(get_db),
):
    """Create or replace the override for one guide section."""
    return guides_crud.upsert_override(
        db,
        guide_slug=guide_slug,
        section_key=section_key,
        body_markdown=body.body_markdown,
        user=current_user,
    )


@router.delete(
    "/{guide_slug}/overrides/{section_key}",
    status_code=204,
    dependencies=[_require_edit],
)
def delete_guide_override(
    guide_slug: str,
    section_key: str,
    db: Session = Depends(get_db),
):
    """Reset one section back to the bundled default (idempotent)."""
    guides_crud.delete_override(db, guide_slug=guide_slug, section_key=section_key)
