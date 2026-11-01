"""Timetable of the scheduled routine jobs (feature-routine-abrufe.md, E2).

The single source for the Celery Beat schedule (``celery_app``), the test that
checks it against the feature doc, and the „Zeitgesteuerte Abrufe“ block in
``/admin/system``. All times are Europe/Berlin and lie before the Borg backup
at 04:05. Beat uses crontab entries, so a missed slot is not made up — the
next one applies.

This module must not import any task module: ``celery_app`` imports it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from celery.schedules import crontab

from dashboard_backend.models.routine_job_run import (
    JOB_BAUPORTAL,
    JOB_PARLIAMENT,
    JOB_PROGRESS_RECOMPUTE,
)

TIMEZONE = "Europe/Berlin"
_TZ = ZoneInfo(TIMEZONE)

# Python weekday numbers (Monday = 0) and the crontab names for them.
_WEEKDAY_CRON = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_WEEKDAY_LABEL = ("montags", "dienstags", "mittwochs", "donnerstags", "freitags", "samstags", "sonntags")


@dataclass(frozen=True)
class RoutineJob:
    key: str
    label: str
    # Name of the wrapper task Beat queues (tasks/routine.py).
    task_name: str
    hour: int
    minute: int
    # None = every day, else the Python weekday (Monday = 0).
    weekday: int | None
    # The page where the job is started by hand.
    admin_path: str
    admin_label: str

    @property
    def interval(self) -> timedelta:
        return timedelta(days=1) if self.weekday is None else timedelta(days=7)

    @property
    def schedule_label(self) -> str:
        day = "täglich" if self.weekday is None else _WEEKDAY_LABEL[self.weekday]
        return f"{day} {self.hour:02d}:{self.minute:02d} Uhr"

    def crontab(self) -> crontab:
        day_of_week = "*" if self.weekday is None else _WEEKDAY_CRON[self.weekday]
        return crontab(minute=self.minute, hour=self.hour, day_of_week=day_of_week)

    def next_run(self, now: datetime | None = None) -> datetime:
        """Next slot after ``now`` (aware, Europe/Berlin)."""
        now = (now or datetime.now(_TZ)).astimezone(_TZ)
        for offset in range(0, 8):
            day = (now + timedelta(days=offset)).date()
            if self.weekday is not None and day.weekday() != self.weekday:
                continue
            candidate = datetime(day.year, day.month, day.day, self.hour, self.minute, tzinfo=_TZ)
            if candidate > now:
                return candidate
        raise AssertionError("unreachable: a slot lies within eight days")


ROUTINE_JOBS: tuple[RoutineJob, ...] = (
    RoutineJob(
        key=JOB_BAUPORTAL,
        label="DB-Bauportal",
        task_name="dashboard_backend.tasks.routine.scheduled_bauportal",
        hour=2,
        minute=40,
        weekday=None,
        admin_path="/admin/bauportal-import",
        admin_label="Zum Bauportal-Abruf",
    ),
    RoutineJob(
        key=JOB_PARLIAMENT,
        label="Abgeordnete (abgeordnetenwatch)",
        task_name="dashboard_backend.tasks.routine.scheduled_parliament",
        hour=2,
        minute=50,
        weekday=0,
        admin_path="/admin/abgeordnete",
        admin_label="Zu den Abgeordneten",
    ),
    RoutineJob(
        key=JOB_PROGRESS_RECOMPUTE,
        label="Planungsstand neu berechnen",
        task_name="dashboard_backend.tasks.routine.scheduled_progress_recompute",
        hour=3,
        minute=10,
        weekday=6,
        admin_path="/admin/planungsstand-konflikte",
        admin_label="Zu Planungsstand · Konflikte",
    ),
)

ROUTINE_JOBS_BY_KEY = {job.key: job for job in ROUTINE_JOBS}


def build_beat_schedule(enabled: bool) -> dict:
    """The ``beat_schedule`` for Celery — empty when routine jobs are off, so
    the scheduler queues nothing at all."""
    if not enabled:
        return {}
    return {
        f"routine-{job.key}": {"task": job.task_name, "schedule": job.crontab()}
        for job in ROUTINE_JOBS
    }
