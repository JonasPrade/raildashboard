"""Raw record for the (semi-automatic) Medien/Presse importer (#48).

An editor pastes an article URL or text; an optional LLM extraction proposes the
project, phase, date and a quote. The draft is stored here unconfirmed. Once the
editor confirms (``confirmed=True`` with a ``project_id`` and a valid phase),
``sync_derived_observations`` materialises a low-trust (0.4) derived MEDIEN
observation. Unlike the derived rows, a media_report itself is editor-owned and
may be edited/deleted.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dashboard_backend.models.base import Base


class MediaReport(Base):
    __tablename__ = "media_report"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    publication: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Original wording supporting the asserted phase (shown in the observation note).
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extracted / editor-confirmed assertion. ``asserted_phase`` is a MainPhase
    # value; ``observed_date`` drives the recency decay (defaults to published_date).
    asserted_phase: Mapped[str | None] = mapped_column(String(40), nullable=True)
    observed_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    suggested_project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("project.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("project.id", ondelete="SET NULL"), nullable=True, index=True
    )
    confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    username_snapshot: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<MediaReport(id={self.id}, publication={self.publication!r}, "
            f"phase={self.asserted_phase!r}, project_id={self.project_id}, "
            f"confirmed={self.confirmed})>"
        )
