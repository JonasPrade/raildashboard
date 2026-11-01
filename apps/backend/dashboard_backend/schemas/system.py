from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class RoutingHealthSchema(BaseModel):
    """The routing service (GraphHopper) at one moment."""

    status: Literal["ok", "error", "unreachable"]
    # Host only; credentials, if any, are never handed out.
    base_url: str
    http_status: int | None = None
    latency_ms: int | None = None
    # German, and it names the next step rather than only the state.
    message: str
    detail: str | None = None
    checked_at: float


class RoutineJobRunSchema(BaseModel):
    """The last run of a routine job (feature-routine-abrufe.md)."""

    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    status: Literal["running", "success", "error", "skipped"] | str
    error: str | None = None
    stats: Any = None
    # NULL = started by the scheduler („Zeitplan“).
    triggered_by_user_id: int | None = None
    triggered_by_username: str | None = None


class RoutineJobStatusSchema(BaseModel):
    key: str
    label: str
    schedule_label: str
    interval_hours: int
    # None while the schedule is switched off (ROUTINE_JOBS_ENABLED=false).
    next_run_at: datetime | None = None
    admin_path: str
    admin_label: str
    # Start of the run that holds the job lock right now.
    running_since: datetime | None = None
    last_run: RoutineJobRunSchema | None = None
    last_success_at: datetime | None = None
    # No successful run for more than twice the interval (or never).
    overdue: bool
    needs_attention: bool


class RoutineJobsSchema(BaseModel):
    """Block „Zeitgesteuerte Abrufe“ in /admin/system and its badge."""

    enabled: bool
    timezone: str
    jobs: list[RoutineJobStatusSchema]
    needs_attention: bool
