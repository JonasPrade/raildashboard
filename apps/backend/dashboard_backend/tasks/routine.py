"""Wrapper tasks the ``scheduler`` service (Celery Beat) queues.

One per routine job (``dashboard_backend/schedule.py``). Each checks
``ROUTINE_JOBS_ENABLED`` and the job's lock before it queues the real task as a
scheduled run; a run that finds the lock taken is skipped and recorded
(feature-routine-abrufe.md, E4).
"""

from __future__ import annotations

from dashboard_backend.celery_app import celery_app
from dashboard_backend.database import Session
from dashboard_backend.models.routine_job_run import (
    JOB_BAUPORTAL,
    JOB_PARLIAMENT,
    JOB_PROGRESS_RECOMPUTE,
)
from dashboard_backend.services.routine_jobs import start_scheduled


def _start(job: str) -> dict:
    db = Session()
    try:
        return start_scheduled(db, job)
    finally:
        db.close()


@celery_app.task
def scheduled_bauportal() -> dict:
    return _start(JOB_BAUPORTAL)


@celery_app.task
def scheduled_parliament() -> dict:
    return _start(JOB_PARLIAMENT)


@celery_app.task
def scheduled_progress_recompute() -> dict:
    return _start(JOB_PROGRESS_RECOMPUTE)
