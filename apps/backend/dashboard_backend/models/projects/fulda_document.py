"""One evaluated Fulda-Runde answer (feature-fulda-import.md).

The Fulda-Runde results reach the public only as the Federal Government's answer
to a Kleine Anfrage. An agent reads that PDF and records it here via the MCP
tools; its announcements (``fulda_announcement``) hang off this row. The
``document_date`` is both the observation date of the "Ist" statements and the
basis of their recency when forecast dates compete.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base

if TYPE_CHECKING:
    from dashboard_backend.models.projects.fulda_announcement import FuldaAnnouncement

# How completely the answer reports the Fulda-Runde results.
ANSWER_STATUSES = ("VOLLSTAENDIG", "TEILWEISE", "OHNE_ERGEBNIS")


class FuldaDocument(Base):
    __tablename__ = "fulda_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    drucksache: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_date: Mapped[date] = mapped_column(Date, nullable=False)
    dip_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    answer_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="VOLLSTAENDIG", server_default="VOLLSTAENDIG"
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    entries: Mapped[list["FuldaAnnouncement"]] = relationship(
        "FuldaAnnouncement",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    username_snapshot: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<FuldaDocument(id={self.id}, year={self.year}, drucksache={self.drucksache!r})>"
