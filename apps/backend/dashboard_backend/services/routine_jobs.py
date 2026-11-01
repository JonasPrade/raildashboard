"""Start, guard and report the scheduled routine jobs (feature-routine-abrufe.md).

Three jobs — DB-Bauportal, members of parliament, weekly recompute of the
planning state — can each be started two ways: by a button in the admin area
(``launch``) or by the ``scheduler`` service (``start_scheduled``, called by
the wrapper tasks in ``tasks/routine.py``). Both take the job's lock first
(``services/job_lock.py``), so a second start while a run is going is refused
(button → 409) or skipped (schedule → recorded as ``skipped``).

``routine_jobs_status`` backs the block „Zeitgesteuerte Abrufe“ in
``/admin/system`` and the badge in the admin overview.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from dashboard_backend.core.config import settings
from dashboard_backend.models.parliament import IMPORT_KIND_POLITICIANS, ParliamentImportRun
from dashboard_backend.models.routine_job_run import (
    JOB_BAUPORTAL,
    JOB_PARLIAMENT,
    JOB_PROGRESS_RECOMPUTE,
    RUN_STATUS_ERROR,
    RUN_STATUS_SKIPPED,
    RUN_STATUS_SUCCESS,
    RoutineJobRun,
)
from dashboard_backend.schedule import ROUTINE_JOBS, TIMEZONE
from dashboard_backend.services import job_lock
from dashboard_backend.services.exceptions import TransientFetchError

logger = logging.getLogger(__name__)

ROUTINE_TZ = ZoneInfo(TIMEZONE)

# Network errors: up to three retries with a backoff of 1, 4 and 16 minutes.
MAX_RETRIES = 3
RETRY_BASE_SECONDS = 60


def retry_countdown(retries_so_far: int) -> int:
    """Backoff before the next attempt: 60 s × 4ⁿ."""
    return RETRY_BASE_SECONDS * 4**retries_so_far


def is_transient(exc: BaseException) -> bool:
    """Is ``exc`` a network failure worth retrying (timeout, refused, 5xx)?"""
    if isinstance(exc, TransientFetchError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response is not None and exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


def will_retry(task, exc: BaseException, *, retryable: bool = True) -> bool:
    return retryable and is_transient(exc) and task.request.retries < MAX_RETRIES


def retry_or_fail(task, exc: BaseException, *, job: str, lock_token: str | None, kwargs: dict):
    """Re-queue ``task`` after a network error, otherwise release the lock and
    re-raise. Never returns."""
    if will_retry(task, exc):
        countdown = retry_countdown(task.request.retries)
        # Keep the job locked through the wait and the next attempt.
        job_lock.extend(job, lock_token, countdown + job_lock.DEFAULT_TTL_SECONDS)
        logger.warning(
            "Routine job %s failed (%s), retry %d/%d in %d s",
            job, exc, task.request.retries + 1, MAX_RETRIES, countdown,
        )
        raise task.retry(exc=exc, countdown=countdown, max_retries=MAX_RETRIES, kwargs=kwargs)
    job_lock.release(job, lock_token)
    raise exc


def retry_note(task, exc: BaseException) -> str:
    """What a run row says while it waits for its next attempt."""
    attempt = task.request.retries + 1
    minutes = retry_countdown(task.request.retries) // 60
    return (
        f"Versuch {attempt} fehlgeschlagen: {exc} — "
        f"Wiederholung {attempt}/{MAX_RETRIES} in {minutes} min"
    )[:2000]


def _task_for(job: str):
    # Imported here: the task modules import the database and celery_app.
    if job == JOB_BAUPORTAL:
        from dashboard_backend.tasks.bauportal import refresh_bauportal

        return refresh_bauportal
    if job == JOB_PARLIAMENT:
        from dashboard_backend.tasks.parliament import refresh_parliament_data

        return refresh_parliament_data
    if job == JOB_PROGRESS_RECOMPUTE:
        from dashboard_backend.tasks.progress import recompute_all_progress_task

        return recompute_all_progress_task
    raise KeyError(job)


def launch(job: str, *, user_id: int | None) -> str:
    """Lock ``job`` and queue its task; returns the Celery task id.

    Raises :class:`job_lock.JobAlreadyRunning` while a run holds the lock.
    """
    task = _task_for(job)
    token = job_lock.acquire(job)
    try:
        result = task.delay(user_id=user_id, lock_token=token)
    except Exception:
        job_lock.release(job, token)
        raise
    return result.id


def already_running_detail(exc: job_lock.JobAlreadyRunning) -> str:
    """The 409 message: „Läuft bereits seit 02:40 Uhr (01.11.2026).“"""
    if exc.since is None:
        return "Läuft bereits."
    local = exc.since.astimezone(ROUTINE_TZ)
    return f"Läuft bereits seit {local:%H:%M} Uhr ({local:%d.%m.%Y})."


def record_skipped(db: Session, job: str, since: datetime | None) -> RoutineJobRun:
    """A scheduled run that found the lock taken."""
    now = datetime.utcnow()
    note = "Übersprungen: Der Job lief bereits"
    if since is not None:
        note += f" (seit {since.astimezone(ROUTINE_TZ):%d.%m.%Y %H:%M} Uhr)"
    run = RoutineJobRun(
        job=job,
        status=RUN_STATUS_SKIPPED,
        started_at=now,
        finished_at=now,
        error=note + ".",
    )
    db.add(run)
    db.commit()
    return run


def start_scheduled(db: Session, job: str) -> dict[str, Any]:
    """What a wrapper task does when Beat fires: check the switch and the lock,
    then queue the job's task as a scheduled run (``user_id = None``)."""
    if not settings.routine_jobs_enabled:
        logger.info("Routine job %s not started: ROUTINE_JOBS_ENABLED is false", job)
        return {"job": job, "status": "disabled"}
    try:
        token = job_lock.acquire(job)
    except job_lock.JobAlreadyRunning as exc:
        logger.warning("Routine job %s skipped: already running since %s", job, exc.since)
        run = record_skipped(db, job, exc.since)
        return {"job": job, "status": RUN_STATUS_SKIPPED, "run_id": run.id}
    try:
        result = _task_for(job).delay(user_id=None, lock_token=token)
    except Exception:
        job_lock.release(job, token)
        raise
    return {"job": job, "status": "queued", "task_id": result.id}


# --- Status for /admin/system ------------------------------------------------


def _as_utc(value: datetime | None) -> datetime | None:
    """DB timestamps are naive UTC; the API hands out aware ones."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _run_dict(run: RoutineJobRun | ParliamentImportRun | None) -> dict | None:
    if run is None:
        return None
    started = _as_utc(run.started_at)
    finished = _as_utc(run.finished_at)
    duration = (finished - started).total_seconds() if started and finished else None
    return {
        "started_at": started,
        "finished_at": finished,
        "duration_seconds": duration,
        "status": run.status,
        "error": run.error,
        "stats": run.stats,
        "triggered_by_user_id": run.triggered_by_user_id,
        "triggered_by_username": run.triggered_by_username,
    }


def _latest(query, model):
    return query.order_by(model.started_at.desc(), model.id.desc()).first()


def _last_runs(db: Session, job: str):
    """(latest run of any status, latest successful run) for ``job``."""
    routine = db.query(RoutineJobRun).filter(RoutineJobRun.job == job)
    if job != JOB_PARLIAMENT:
        last = _latest(routine, RoutineJobRun)
        success = _latest(routine.filter(RoutineJobRun.status == RUN_STATUS_SUCCESS), RoutineJobRun)
        return last, success
    # The members of parliament keep their own run table; only a skipped
    # scheduled run lands in routine_job_run.
    parliament = db.query(ParliamentImportRun).filter(
        ParliamentImportRun.kind == IMPORT_KIND_POLITICIANS
    )
    last_import = _latest(parliament, ParliamentImportRun)
    success = _latest(
        parliament.filter(ParliamentImportRun.status == RUN_STATUS_SUCCESS), ParliamentImportRun
    )
    last_skip = _latest(routine.filter(RoutineJobRun.status == RUN_STATUS_SKIPPED), RoutineJobRun)
    candidates = [r for r in (last_import, last_skip) if r is not None]
    last = max(candidates, key=lambda r: r.started_at) if candidates else None
    return last, success


def routine_jobs_status(db: Session, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    enabled = settings.routine_jobs_enabled
    jobs = []
    for job in ROUTINE_JOBS:
        last, success = _last_runs(db, job.key)
        last_success_at = _as_utc(success.started_at) if success is not None else None
        overdue = last_success_at is None or now - last_success_at > 2 * job.interval
        last_error = last is not None and last.status == RUN_STATUS_ERROR
        jobs.append(
            {
                "key": job.key,
                "label": job.label,
                "schedule_label": job.schedule_label,
                "interval_hours": int(job.interval / timedelta(hours=1)),
                "next_run_at": job.next_run(now) if enabled else None,
                "admin_path": job.admin_path,
                "admin_label": job.admin_label,
                "running_since": job_lock.held_since(job.key),
                "last_run": _run_dict(last),
                "last_success_at": last_success_at,
                "overdue": overdue,
                "needs_attention": overdue or last_error or not enabled,
            }
        )
    return {
        "enabled": enabled,
        "timezone": TIMEZONE,
        "jobs": jobs,
        "needs_attention": (not enabled) or any(j["needs_attention"] for j in jobs),
    }
