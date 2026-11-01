"""Run record of a scheduled routine job (feature-routine-abrufe.md).

One row per run of a routine job that has no run table of its own — today the
DB-Bauportal fetch (``bauportal``) and the weekly recompute of the planning
state (``progress_recompute``). A further routine job is one more value of
``job``, not a new table. The members of parliament keep their own
``parliament_import_run``; a scheduled parliament run the lock skipped is
recorded here (``job = "parliament"``, ``status = "skipped"``), because that
table has no notion of a skipped run.

``triggered_by_user_id`` is ``NULL`` for a run the scheduler started — the UI
shows „Zeitplan“ for it.
"""

from __future__ import annotations

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from dashboard_backend.models.base import Base

JOB_BAUPORTAL = "bauportal"
JOB_PARLIAMENT = "parliament"
JOB_PROGRESS_RECOMPUTE = "progress_recompute"

RUN_STATUS_RUNNING = "running"
RUN_STATUS_SUCCESS = "success"
RUN_STATUS_ERROR = "error"
RUN_STATUS_SKIPPED = "skipped"


class RoutineJobRun(Base):
    __tablename__ = "routine_job_run"

    id = Column(Integer, primary_key=True)
    job = Column(String(40), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=RUN_STATUS_RUNNING)
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    # Free-form counters (fetched, created, status changes, projects …) so a new
    # metric does not need a migration.
    stats = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    triggered_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    triggered_by = relationship("User", lazy="select")

    @property
    def triggered_by_username(self) -> str | None:
        return self.triggered_by.username if self.triggered_by is not None else None
