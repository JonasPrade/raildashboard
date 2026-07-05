"""Raw record for the Fulda-Runde importer (#46).

The Fulda-Runde appears as a yearly "Antwort der Bundesregierung" (PDF) that
lists projects per Leistungsphase, grouped by numbered question. One row per
(project, category) is extracted via OCR + LLM. An announcement can be matched
to several projects (m:n, like VIB) — once an editor confirms the match,
``sync_derived_observations`` materialises a derived FULDA_RUNDE observation
(trust 0.7) for each linked project, whose date also feeds the forecast.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.associations.fulda_announcement_to_project import (
    fulda_announcement_to_project,
)
from dashboard_backend.models.base import Base

if TYPE_CHECKING:
    from dashboard_backend.models.projects.project import Project


class FuldaAnnouncement(Base):
    __tablename__ = "fulda_announcement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Fulda-Runde year the import belongs to (one answer per year). Entered by the
    # editor at upload time; the whole importer is organised/filtered by this year.
    announcement_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Provenance of the Kleine Anfrage (e.g. "Drucksache 20/12345") + its date.
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    raw_name: Mapped[str] = mapped_column(String(500), nullable=False)
    # Abschnitt (the answer table's second column / the part after the colon in a
    # bullet list). In the dashboard the Abschnitt is the subproject — matching
    # pre-fills the leaf subproject under the matched superior project.
    abschnitt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Extraction category: IN_LPH_1_2 | IN_LPH_3_4 | COMPLETED_LPH_1_2 | COMPLETED_LPH_3_4
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Derived MainPhase value (from category; editor-confirmable).
    announced_phase: Mapped[str | None] = mapped_column(String(40), nullable=True)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # m:n project assignment (mirrors VIB's vib_entry_project). Pre-filled with the
    # fuzzy-match suggestions at parse time; the editor adjusts via a MultiSelect.
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        secondary=fulda_announcement_to_project,
        backref="fulda_announcements",
        lazy="selectin",
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
            f"<FuldaAnnouncement(id={self.id}, year={self.announcement_year}, "
            f"name={self.raw_name!r}, category={self.category!r}, "
            f"confirmed={self.confirmed})>"
        )
