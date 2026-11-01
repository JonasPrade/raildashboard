"""DB-Bauportal importer (#47).

Fetches the open project list from ``bauprojekte.deutschebahn.com`` and upserts
one ``bauportal_status`` row per external project, with a fuzzy-matched
suggestion. No scraping — the portal exposes a public JSON endpoint. Matching is
only a suggestion; an editor confirms the match in the review UI, which sets
``project_id`` and triggers materialisation via ``sync_derived_observations``.

Since #340 (feature-routine-abrufe.md) the fetch runs as the Celery task
``refresh_bauportal`` — nightly from the scheduler and from the button on the
admin page alike. Every run leaves a row in ``routine_job_run`` (job
``bauportal``), also when it fails. Two dates per entry (W2):
``last_seen_at`` moves with every fetch, ``status_changed_at`` only when
``status_raw`` changes — that is the observation date of the derived
BAUPORTAL observation. Projects whose confirmed entry changed its status are
recomputed right after the run.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from dashboard_backend.celery_app import celery_app
from dashboard_backend.database import Session as SessionLocal
from dashboard_backend.models.projects.bauportal_status import BauportalStatus
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.routine_job_run import (
    JOB_BAUPORTAL,
    RUN_STATUS_ERROR,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCESS,
    RoutineJobRun,
)
from dashboard_backend.services import job_lock
from dashboard_backend.services.routine_jobs import retry_note, retry_or_fail, will_retry
from dashboard_backend.tasks.vib_matching import suggest_project_for_bauportal

logger = logging.getLogger(__name__)

BAUPORTAL_API_URL = "https://bauprojekte.deutschebahn.com/api/getProjectsList"

# Test seam: an ``httpx.MockTransport`` replaces the network in the test suite.
_transport: httpx.BaseTransport | None = None


def fetch_bauportal_projects(timeout: float = 30.0) -> list[dict]:
    """GET the public Bauportal project list. Returns the parsed JSON array.

    Raises ``httpx.HTTPError`` on network/HTTP failure (retried by the task when
    it is a timeout, a refused connection or a 5xx) and ``ValueError`` on an
    unexpected answer (not retried), without persisting a partial import.
    """

    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    with httpx.Client(
        timeout=timeout, headers=headers, follow_redirects=True, transport=_transport
    ) as client:
        response = client.get(BAUPORTAL_API_URL)
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, list):
        raise ValueError("Unexpected Bauportal response shape (expected a JSON array).")
    return data


def _coerce_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def import_bauportal(db: Session, records: list[dict] | None = None) -> dict:
    """Fetch (unless ``records`` supplied) and upsert Bauportal rows.

    Upserts by external ``id`` (``bauportal_id``). A confirmed ``project_id`` is
    never overwritten on re-import; the fuzzy suggestion is refreshed only while
    the entry is still unconfirmed. ``last_seen_at`` is set on every row the
    API returns, ``status_changed_at`` only when ``status_raw`` changed (or the
    row is new). Returns a summary dict; ``changed_project_ids`` lists the
    projects whose *confirmed* entry changed its status.
    """

    if records is None:
        records = fetch_bauportal_projects()

    # Archived projects are no matching candidates (feature-project-archive.md).
    projects = db.query(Project).filter(Project.is_archived.is_(False)).all()

    existing = {row.bauportal_id: row for row in db.query(BauportalStatus).all()}
    created = updated = skipped = status_changed = 0
    changed_project_ids: set[int] = set()
    now = datetime.utcnow()

    for rec in records:
        bauportal_id = _coerce_int(rec.get("id"))
        shorttitle = (rec.get("shorttitle") or "").strip()
        if bauportal_id is None or not shorttitle:
            skipped += 1
            continue

        suggestion = suggest_project_for_bauportal(shorttitle, projects)
        row = existing.get(bauportal_id)
        is_new = row is None
        if is_new:
            row = BauportalStatus(bauportal_id=bauportal_id)
            db.add(row)
            existing[bauportal_id] = row

        new_status = rec.get("icon_title")
        if is_new:
            row.status_changed_at = now
        elif row.status_raw != new_status:
            row.status_changed_at = now
            status_changed += 1
            if row.confirmed and row.project_id is not None:
                changed_project_ids.add(row.project_id)
        row.last_seen_at = now

        row.shorttitle = shorttitle
        row.parent_bauportal_id = _coerce_int(rec.get("parent_id")) or None
        row.status_raw = new_status
        row.projecttime_raw = rec.get("projecttime")
        row.url = rec.get("url")
        row.lat = _coerce_float(rec.get("lat"))
        row.lng = _coerce_float(rec.get("lng"))
        row.raw_json = json.dumps(rec, ensure_ascii=False)
        # Refresh the suggestion while unconfirmed and pre-fill it into the
        # assignment (like Fulda) so the editor only reviews/confirms it. A
        # confirmed match is never touched.
        if not row.confirmed:
            row.suggested_project_id = suggestion
            if row.project_id is None:
                row.project_id = suggestion

        if is_new:
            created += 1
        else:
            updated += 1

    db.commit()
    return {
        "fetched": len(records),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "status_changed": status_changed,
        "changed_project_ids": sorted(changed_project_ids),
    }


@celery_app.task(bind=True)
def refresh_bauportal(
    self,
    user_id: int | None = None,
    lock_token: str | None = None,
    run_id: int | None = None,
) -> dict:
    """Fetch the Bauportal, upsert, then recompute the projects whose confirmed
    entry changed its status. ``user_id = None`` is a scheduled run.

    The caller holds the job lock (``services/routine_jobs.launch`` or the
    scheduler's wrapper task) and passes its token; the task releases it.
    Network errors are retried up to three times — the run row stays
    ``running`` meanwhile (``run_id`` carries it over to the next attempt).
    """
    from dashboard_backend.crud._importer_common import recompute_for

    db = SessionLocal()
    try:
        run = db.get(RoutineJobRun, run_id) if run_id else None
        if run is None:
            run = RoutineJobRun(
                job=JOB_BAUPORTAL,
                status=RUN_STATUS_RUNNING,
                started_at=datetime.utcnow(),
                triggered_by_user_id=user_id,
            )
            db.add(run)
            db.commit()
        run_id = run.id

        try:
            summary = import_bauportal(db)
            changed = summary.pop("changed_project_ids")
            recompute_for(db, changed)
        except Exception as exc:  # noqa: BLE001 — the run row records the failure
            db.rollback()
            run = db.get(RoutineJobRun, run_id)
            if will_retry(self, exc):
                run.error = retry_note(self, exc)
            else:
                run.status = RUN_STATUS_ERROR
                run.error = str(exc)[:2000] or type(exc).__name__
                run.finished_at = datetime.utcnow()
            db.commit()
            retry_or_fail(
                self,
                exc,
                job=JOB_BAUPORTAL,
                lock_token=lock_token,
                kwargs={"user_id": user_id, "lock_token": lock_token, "run_id": run_id},
            )

        run = db.get(RoutineJobRun, run_id)
        stats = {**summary, "recomputed_projects": len(changed)}
        run.status = RUN_STATUS_SUCCESS
        run.error = None
        run.stats = stats
        run.finished_at = datetime.utcnow()
        db.commit()
        job_lock.release(JOB_BAUPORTAL, lock_token)
        logger.info("Bauportal run %s: %s", run_id, stats)
        return {"run_id": run_id, **stats}
    finally:
        db.close()
