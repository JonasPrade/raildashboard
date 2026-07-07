"""Editor overrides for the in-app guide pages ("Anleitungen").

Guide content ships as versioned markdown defaults inside the frontend bundle.
Users with the ``guides.edit`` capability can replace the text of a single
guide section in-app; the override is stored here keyed by (guide_slug,
section_key) and wins over the bundled default. Deleting the row falls back to
the default, so guides can never be broken permanently from the UI.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from dashboard_backend.models.base import Base


class GuideSectionOverride(Base):
    __tablename__ = "guide_section_override"
    __table_args__ = (
        UniqueConstraint("guide_slug", "section_key", name="uq_guide_section"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    guide_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    section_key: Mapped[str] = mapped_column(String(100), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    username_snapshot: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<GuideSectionOverride(guide_slug={self.guide_slug!r}, "
            f"section_key={self.section_key!r})>"
        )
