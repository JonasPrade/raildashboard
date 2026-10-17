"""One statement of a Fulda-Runde answer (feature-fulda-import.md).

An agent records each project line of a ``FuldaDocument`` via the MCP tools:
the category (``services/fulda_categories.py``) fixes whether the line states
the current phase ("Ist") or announces a future one (prognosis / new
admission), plus provenance (question, page, verbatim text). An announcement can
be matched to several projects (m:n, like VIB) — once confirmed,
``sync_derived_observations`` materialises a derived FULDA_RUNDE observation per
linked project: a phase for "Ist" lines, an expected date for prognoses.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.associations.fulda_announcement_to_project import (
    fulda_announcement_to_project,
)
from dashboard_backend.models.base import Base

if TYPE_CHECKING:
    from dashboard_backend.models.projects.fulda_document import FuldaDocument
    from dashboard_backend.models.projects.project import Project


class FuldaAnnouncement(Base):
    __tablename__ = "fulda_announcement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # The answer this line comes from. Nullable only for the expand step; every
    # row written since feature-fulda-import.md carries it.
    document_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("fulda_document.id", ondelete="CASCADE"), nullable=True, index=True
    )
    document: Mapped["FuldaDocument | None"] = relationship(
        "FuldaDocument", back_populates="entries"
    )

    # Copy of ``document.year`` — the review UI is organised/filtered by year.
    announcement_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Deprecated (expand/contract): now on ``fulda_document``; no longer written.
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    raw_name: Mapped[str] = mapped_column(String(500), nullable=False)
    # Abschnitt (the answer table's second column / the part after the colon in a
    # bullet list). In the dashboard the Abschnitt is the subproject — matching
    # pre-fills the leaf subproject under the matched superior project.
    abschnitt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Key of ``FULDA_CATEGORIES`` — fixes statement kind and phase.
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Deprecated (expand/contract): the phase now follows from ``category``.
    announced_phase: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Announced date for prognoses / new admissions (e.g. 2026-12-31 for
    # "bis Ende 2026"); unused for "Ist" lines.
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Provenance inside the document.
    question_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Who the answer attributes the statement to: BMV or DB ("nach Angaben der DB AG").
    attributed_to: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Why the projects were assigned (written by the agent or editor).
    assignment_note: Mapped[str | None] = mapped_column(Text, nullable=True)

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
