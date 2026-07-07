"""DB access for guide-section overrides ("Anleitungen" editing)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from dashboard_backend.models.guides import GuideSectionOverride
from dashboard_backend.models.users import User


def list_overrides(db: Session, guide_slug: str) -> list[GuideSectionOverride]:
    return (
        db.query(GuideSectionOverride)
        .filter(GuideSectionOverride.guide_slug == guide_slug)
        .order_by(GuideSectionOverride.section_key)
        .all()
    )


def upsert_override(
    db: Session,
    *,
    guide_slug: str,
    section_key: str,
    body_markdown: str,
    user: User | None,
) -> GuideSectionOverride:
    row = (
        db.query(GuideSectionOverride)
        .filter(
            GuideSectionOverride.guide_slug == guide_slug,
            GuideSectionOverride.section_key == section_key,
        )
        .one_or_none()
    )
    if row is None:
        row = GuideSectionOverride(guide_slug=guide_slug, section_key=section_key)
        db.add(row)
    row.body_markdown = body_markdown
    row.updated_at = datetime.utcnow()
    row.updated_by_user_id = user.id if user else None
    row.username_snapshot = user.username if user else None
    db.commit()
    db.refresh(row)
    return row


def delete_override(db: Session, *, guide_slug: str, section_key: str) -> bool:
    deleted = (
        db.query(GuideSectionOverride)
        .filter(
            GuideSectionOverride.guide_slug == guide_slug,
            GuideSectionOverride.section_key == section_key,
        )
        .delete()
    )
    db.commit()
    return deleted > 0
