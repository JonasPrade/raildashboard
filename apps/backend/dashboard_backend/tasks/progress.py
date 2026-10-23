"""Celery task for the planning state (Planungsstand).

``recompute_all_progress_task`` — the full resync over every project, started
from the admin page „Planungsstand · Konflikte“. Needed after a deploy that
changes the derivation (e.g. a new source such as the GVFG-Bundesprogramm);
in daily operation the lazy resync on read keeps single projects current.
"""

from __future__ import annotations

from dashboard_backend.celery_app import celery_app
from dashboard_backend.crud.projects.progress import recompute_all_progress
from dashboard_backend.database import Session


@celery_app.task(bind=True)
def recompute_all_progress_task(self) -> dict:
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
        return recompute_all_progress(db, on_batch=report)
    finally:
        db.close()
