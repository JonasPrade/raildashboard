"""DB-Bauportal importer (#47).

Fetches the open project list from ``bauprojekte.deutschebahn.com`` and upserts
one ``bauportal_status`` row per external project, with a fuzzy-matched
suggestion. No scraping — the portal exposes a public JSON endpoint. Matching is
only a suggestion; an editor confirms the match in the review UI, which sets
``project_id`` and triggers materialisation via ``sync_derived_observations``.

The fetch is small enough (~300 records) to run synchronously from the admin
endpoint; no Celery worker is involved.
"""

from __future__ import annotations

import json

import httpx
from sqlalchemy.orm import Session

from dashboard_backend.models.projects.bauportal_status import BauportalStatus
from dashboard_backend.models.projects.project import Project
from dashboard_backend.tasks.vib_matching import suggest_project_for_bauportal

BAUPORTAL_API_URL = "https://bauprojekte.deutschebahn.com/api/getProjectsList"


def fetch_bauportal_projects(timeout: float = 30.0) -> list[dict]:
    """GET the public Bauportal project list. Returns the parsed JSON array.

    Raises ``httpx.HTTPError`` on network/HTTP failure so the caller can report
    it without persisting a partial import.
    """

    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
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
    the entry is still unconfirmed. Returns a summary dict.
    """

    if records is None:
        records = fetch_bauportal_projects()

    projects = db.query(Project).all()

    existing = {row.bauportal_id: row for row in db.query(BauportalStatus).all()}
    created = updated = skipped = 0

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

        row.shorttitle = shorttitle
        row.parent_bauportal_id = _coerce_int(rec.get("parent_id")) or None
        row.status_raw = rec.get("icon_title")
        row.projecttime_raw = rec.get("projecttime")
        row.url = rec.get("url")
        row.lat = _coerce_float(rec.get("lat"))
        row.lng = _coerce_float(rec.get("lng"))
        row.raw_json = json.dumps(rec, ensure_ascii=False)
        # Refresh the suggestion only while unconfirmed; never touch a confirmed match.
        if row.project_id is None:
            row.suggested_project_id = suggestion

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
    }
