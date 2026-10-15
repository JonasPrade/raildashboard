from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dashboard_backend.models.base import Base


class InfraplanEntryProject(Base):
    """m:n link Infraplan entry ↔ project (pattern: ``vib_entry_project``),
    with provenance: who assigned it and how (``NUMBER`` | ``FUZZY`` |
    ``MANUAL`` | ``AGENT``); ``note`` carries the agent's reasoning."""

    __tablename__ = "infraplan_entry_project"
    __table_args__ = (
        # The derived-observation sync filters by project_id; the composite
        # primary key leads with entry_id and cannot serve it.
        Index("ix_infraplan_entry_project_project_id", "project_id"),
    )

    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("infraplan_entry.id", ondelete="CASCADE"), primary_key=True
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_by_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assignment_source: Mapped[str] = mapped_column(String(10), nullable=False, default="MANUAL")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
