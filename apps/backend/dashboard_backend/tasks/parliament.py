"""Celery tasks for the constituency/MP feature.

Three jobs with very different cost:

* ``refresh_parliament_data`` — ~15 paged requests against abgeordnetenwatch and
  an upsert over a few thousand rows. Cheap on purpose: the people data ages
  fast (substitutes, committee reshuffles), so rerunning has to be painless.
* ``rebuild_constituency_links`` — the full ``ST_Intersection`` rebuild over
  every project with a geometry. Needed after a geometry import or a new
  legislative period, not in daily operation.
* ``import_constituency_file`` — writes the outlines from an uploaded GeoJSON
  (once per election), then runs the link rebuild because new outlines
  invalidate every existing link.
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
from dashboard_backend.services.parliament_import import (
    import_constituency_geometries,
    import_politicians,
    parse_constituency_geojson,
)
from dashboard_backend.utils.file_storage import consume_staged_import

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
    try:
        run = _run_link_rebuild(db, user_id)
        return {"run_id": run.id, "status": run.status, "stats": run.stats}
    finally:
        db.close()


@celery_app.task(bind=True)
def import_constituency_file(
    self,
    staged_name: str,
    period_external_id: int,
    election_year: int,
    source: str,
    user_id: int | None = None,
) -> dict:
    """Import the outlines from a staged GeoJSON upload, then rebuild the links.

    The staged file is deleted afterwards, successful or not.
    """
    with consume_staged_import(staged_name) as raw:
        features = parse_constituency_geojson(raw)
    db = Session()
    try:
        geometry_run = import_constituency_geometries(
            db,
            features,
            period_external_id=period_external_id,
            election_year=election_year,
            source=source,
            user_id=user_id,
        )
        link_run = _run_link_rebuild(db, user_id)
        return {
            "run_id": geometry_run.id,
            "status": geometry_run.status,
            "stats": geometry_run.stats,
            "links": link_run.stats,
        }
    finally:
        db.close()


def _run_link_rebuild(db, user_id: int | None) -> ParliamentImportRun:
    """Full link rebuild, recorded as an import run (also when it fails)."""
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
        return run
    except Exception as exc:  # noqa: BLE001 — the run row records the failure
        db.rollback()
        run = db.merge(run)
        run.status = IMPORT_STATUS_ERROR
        run.error = str(exc)[:2000]
        run.finished_at = datetime.utcnow()
        db.commit()
        raise
