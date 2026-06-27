"""Atomic per-source statement about a project's planning state.

One row per assertion. Manual observations are persistent and audited; in
Phase 2 the VIB/FinVe importers will materialise rows with ``is_derived=True``
plus provenance FKs (regenerated on resync, never hand-edited / hand-deleted).
The provenance columns already exist so Phase 2 only has to populate them.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dashboard_backend.models.base import Base


class ProgressObservation(Base):
    __tablename__ = "progress_observation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )

    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    track: Mapped[str] = mapped_column(String(10), nullable=False)
    # The asserted lower-bound state: a MainPhase value for MAIN, a
    # ParallelState value for PF/PARL.
    asserted_state: Mapped[str] = mapped_column(String(40), nullable=False)
    observed_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    # Per-observation confidence override (0..1). None → source-type default.
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Provenance (Phase 2; nullable, SET NULL so history survives) --------
    vib_entry_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("vib_entry.id", ondelete="SET NULL"), nullable=True
    )
    vib_pfa_entry_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("vib_pfa_entry.id", ondelete="SET NULL"), nullable=True
    )
    finve_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("finve.id", ondelete="SET NULL"), nullable=True
    )
    bauportal_status_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("bauportal_status.id", ondelete="SET NULL"), nullable=True
    )

    is_derived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # Expected (future) milestone rather than a reached state. Expected
    # observations feed the forecast only and are excluded from the
    # headline / computed_phase derivation (they must not pull the current
    # phase forward).
    is_expected: Mapped[bool] = mapped_column(
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
            f"<ProgressObservation(project_id={self.project_id}, "
            f"source={self.source_type}, track={self.track}, "
            f"state={self.asserted_state}, derived={self.is_derived})>"
        )
