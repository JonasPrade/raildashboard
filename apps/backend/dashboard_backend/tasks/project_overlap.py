"""Celery task for the map overlaps (docs/features/feature-map-overlapping-geometries.md).

``recompute_all_overlaps_task`` rebuilds ``project_map_geometry`` and
``project_overlap`` over the whole portfolio. The backend starts it once by
itself when it finds the tables empty (``start_initial_fill_if_empty``, the
initial fill after the deploy that adds them); an admin can start it again via
``POST /api/v1/admin/overlap-recompute``. In daily operation saving a project
keeps the tables current.
"""

from __future__ import annotations

import logging

from dashboard_backend.celery_app import celery_app
from dashboard_backend.database import Session
from dashboard_backend.services.project_overlap import is_empty, recompute_all_overlaps

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def recompute_all_overlaps_task(self) -> dict:
    """Recompute overlap pairs and lanes of every project."""
    self.update_state(state="PROGRESS", meta={"step": "recompute", "step_label": "Überlappungen werden berechnet …"})
    db = Session()
    try:
        return recompute_all_overlaps(db).as_dict()
    finally:
        db.close()


def start_initial_fill_if_empty() -> None:
    """Queue the full rebuild when the overlap tables are still empty.

    Called once at backend start, off the event loop. Never raises: a missing
    table (migration not applied) or an unreachable broker must not keep the
    backend from starting — the map then simply draws every project on lane 0.
    """
    try:
        db = Session()
        try:
            empty = is_empty(db)
        finally:
            db.close()
        if empty:
            recompute_all_overlaps_task.apply_async(retry=False)
            logger.info("map overlaps: tables empty, initial fill queued")
    except Exception:  # noqa: BLE001 — see docstring
        logger.warning("map overlaps: could not queue the initial fill", exc_info=True)
