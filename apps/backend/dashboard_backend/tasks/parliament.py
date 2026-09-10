"""Celery tasks for the constituency/MP feature.

Two jobs with very different cost:

* ``refresh_parliament_data`` — ~15 paged requests against abgeordnetenwatch and
  an upsert over a few thousand rows. Cheap on purpose: the people data ages
  fast (substitutes, committee reshuffles), so rerunning has to be painless.
* ``rebuild_constituency_links`` — the full ``ST_Intersection`` rebuild over
  every project with a geometry. Needed after a geometry import or a new
  legislative period, not in daily operation.
"""

from __future__ import annotations

import logging
from datetime import datetime

from dashboard_backend.celery_app import celery_app
from dashboard_backend.database import Session
from dashboard_backend.models.parliament import (
    IMPORT_KIND_LINKS,
    IMPORT_STATUS_ERROR,
    IMPORT_STATUS_SUCCESS,
    ParliamentImportRun,
)
from dashboard_backend.services.constituency_matching import recompute_all_links
from dashboard_backend.services.parliament_import import import_politicians

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def refresh_parliament_data(self, user_id: int | None = None, period_external_id: int | None = None) -> dict:
    """Fetch period, constituencies, mandates and committee memberships."""
    db = Session()
    try:
        run = import_politicians(
            db, period_external_id=period_external_id, user_id=user_id
        )
        return {"run_id": run.id, "status": run.status, "stats": run.stats}
    finally:
        db.close()


@celery_app.task(bind=True)
def rebuild_constituency_links(self, user_id: int | None = None) -> dict:
    """Recompute ``project_to_constituency`` for the whole portfolio."""
    db = Session()
    run = ParliamentImportRun(kind=IMPORT_KIND_LINKS, triggered_by_user_id=user_id)
    db.add(run)
    db.commit()
    try:
        stats = recompute_all_links(db)
        run = db.merge(run)
        run.stats = stats.as_dict()
        run.status = IMPORT_STATUS_SUCCESS
        run.finished_at = datetime.utcnow()
        db.commit()
        return {"run_id": run.id, "status": run.status, "stats": run.stats}
    except Exception as exc:  # noqa: BLE001 — the run row records the failure
        db.rollback()
        run = db.merge(run)
        run.status = IMPORT_STATUS_ERROR
        run.error = str(exc)[:2000]
        run.finished_at = datetime.utcnow()
        db.commit()
        raise
    finally:
        db.close()
