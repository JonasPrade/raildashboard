"""Raw record for the Fulda-Runde importer (#46).

The Fulda-Runde appears as parliamentary "Kleine Anfragen" (PDF) that list
projects by Leistungsphase (in Lph 1–2 / 3–4, and ones that completed Lph 1–2 or
3–4). One row per (project, category) extracted via OCR + LLM. Once an editor
confirms a match, ``sync_derived_observations`` materialises a derived
FULDA_RUNDE observation (trust 0.7) whose date also feeds the forecast.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from dashboard_backend.models.base import Base


class FuldaAnnouncement(Base):
    __tablename__ = "fulda_announcement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Provenance of the Kleine Anfrage (e.g. "Drucksache 20/12345") + its date.
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    raw_name: Mapped[str] = mapped_column(String(500), nullable=False)
    # Extraction category: IN_LPH_1_2 | IN_LPH_3_4 | COMPLETED_LPH_1_2 | COMPLETED_LPH_3_4
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Derived MainPhase value (from category; editor-confirmable).
    announced_phase: Mapped[str | None] = mapped_column(String(40), nullable=True)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)

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
            f"<FuldaAnnouncement(id={self.id}, name={self.raw_name!r}, "
            f"category={self.category!r}, project_id={self.project_id}, "
            f"confirmed={self.confirmed})>"
        )
