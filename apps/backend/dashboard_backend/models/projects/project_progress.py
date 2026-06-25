"""1:1 planning-state record for a (leaf) project.

Replaces the historic commented-out ``project_progress`` relation in
``project.py``. Holds the editorial flags, lifecycle overlay, the cached
derivation output and the manual overrides. The actual per-source statements
live in :class:`ProgressObservation`.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base
from dashboard_backend.models.projects.progress_enums import LifecycleStatus


class ProjectProgress(Base):
    __tablename__ = "project_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # --- Editorial flags -----------------------------------------------------
    has_planfeststellung: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # None = derive default from project groups (BSWAG* → relevant). A concrete
    # bool is a manual override that keeps live even when groups change.
    parl_befassung_relevant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # --- Parliamentary involvement details (editorial, single block) ---------
    # Free-text note, link to the Bundestags-Drucksache and the relevant date.
    # The "Beschluss" itself is the PARL track state (parl_state_override).
    parl_befassung_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parl_drucksache_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    parl_befassung_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)

    # --- Planfeststellung details (editorial) --------------------------------
    # Free-text note, the relevant date, and a list of commented reference links
    # ``[{"url": str, "comment": str | None}, ...]`` (replaces single-URL +
    # document-id linking). The PF track state itself remains pf_state_override.
    pf_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    pf_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    pf_links: Mapped[list | None] = mapped_column(JSON, nullable=True)

    lifecycle_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=LifecycleStatus.AKTIV.value,
        server_default=LifecycleStatus.AKTIV.value,
    )

    # --- Cached derivation output -------------------------------------------
    computed_phase: Mapped[str | None] = mapped_column(String(40), nullable=True)
    computed_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- Manual overrides (win over computed) -------------------------------
    manual_phase_override: Mapped[str | None] = mapped_column(String(40), nullable=True)
    manual_override_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    pf_state_override: Mapped[str | None] = mapped_column(String(20), nullable=True)
    parl_state_override: Mapped[str | None] = mapped_column(String(20), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    observations: Mapped[list["ProgressObservation"]] = relationship(
        "ProgressObservation",
        primaryjoin="ProjectProgress.project_id == foreign(ProgressObservation.project_id)",
        viewonly=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ProjectProgress(project_id={self.project_id}, phase={self.computed_phase})>"
