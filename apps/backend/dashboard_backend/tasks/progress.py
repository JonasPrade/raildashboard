"""Celery task for the planning state (Planungsstand).

``recompute_all_progress_task`` — the full resync over every project. Started
weekly by the scheduler (Sundays 03:10, ``user_id = None``) and by hand from the
admin page „Planungsstand · Konflikte“ — e.g. after a deploy that changes the
derivation (a new source such as the GVFG-Bundesprogramm). In daily operation
the lazy resync on read keeps single projects current, and the nightly
Bauportal run recomputes the projects whose Bauportal status changed.

Every run leaves a row in ``routine_job_run`` (job ``progress_recompute``),
also when it fails. The caller holds the job lock and passes its token; the
task releases it. No retries: a failed recompute is no network problem.
See docs/features/feature-routine-abrufe.md.
"""

from __future__ import annotations

from datetime import datetime

from dashboard_backend.celery_app import celery_app
from dashboard_backend.crud.projects.progress import recompute_all_progress
from dashboard_backend.database import Session
from dashboard_backend.models.routine_job_run import (
    JOB_PROGRESS_RECOMPUTE,
    RUN_STATUS_ERROR,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCESS,
    RoutineJobRun,
)
from dashboard_backend.services import job_lock


@celery_app.task(bind=True)
def recompute_all_progress_task(
    self, user_id: int | None = None, lock_token: str | None = None
) -> dict:
    """Resync derived observations, headline and dates of all projects."""

    def report(done: int, total: int) -> None:
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "recompute",
                "step_label": f"{done} von {total} Projekten neu berechnet …",
                "current_page": done,
                "total_pages": total,
            },
        )

    db = Session()
    try:
        run = RoutineJobRun(
            job=JOB_PROGRESS_RECOMPUTE,
            status=RUN_STATUS_RUNNING,
            started_at=datetime.utcnow(),
            triggered_by_user_id=user_id,
        )
        db.add(run)
        db.commit()
        run_id = run.id
        try:
            result = recompute_all_progress(db, on_batch=report)
        except Exception as exc:  # noqa: BLE001 — the run row records the failure
            db.rollback()
            run = db.get(RoutineJobRun, run_id)
            run.status = RUN_STATUS_ERROR
            run.error = str(exc)[:2000] or type(exc).__name__
            run.finished_at = datetime.utcnow()
            db.commit()
            raise
        run = db.get(RoutineJobRun, run_id)
        run.status = RUN_STATUS_SUCCESS
        run.stats = result
        run.finished_at = datetime.utcnow()
        db.commit()
        return result
    finally:
        job_lock.release(JOB_PROGRESS_RECOMPUTE, lock_token)
        db.close()
