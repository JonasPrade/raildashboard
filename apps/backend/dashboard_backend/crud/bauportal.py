"""DB access for the DB-Bauportal importer (#47).

Thin layer over the fetch/match task and the ``bauportal_status`` raw table.
Confirming a match sets ``project_id`` and immediately re-materialises the
affected project(s) so the derived BAUPORTAL observation appears without waiting
for the 24-h lazy resync.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from dashboard_backend.crud.projects.progress import recompute_progress
from dashboard_backend.models.projects.bauportal_status import BauportalStatus
from dashboard_backend.models.projects.project import Project
from dashboard_backend.services.progress_materialization import (
    bauportal_status_to_main_phase,
)
from dashboard_backend.tasks.bauportal import import_bauportal


class ProjectNotFoundError(Exception):
    """Raised when confirming a match against a non-existent project."""


def run_import(db: Session) -> dict:
    """Fetch from the Bauportal API and upsert raw rows. Returns a summary."""
    return import_bauportal(db)


def _project_name_map(db: Session, ids: list[int | None]) -> dict[int, str]:
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    rows = db.query(Project.id, Project.name).filter(Project.id.in_(wanted)).all()
    return {row.id: row.name for row in rows}


def list_entries(db: Session, *, only_unconfirmed: bool = False) -> list[dict]:
    """List Bauportal entries with resolved suggestion / match names.

    Unmatched/unconfirmed entries sort first (they need attention), then by title.
    """

    query = db.query(BauportalStatus)
    if only_unconfirmed:
        query = query.filter(BauportalStatus.project_id.is_(None))
    rows = query.order_by(
        BauportalStatus.project_id.isnot(None),  # unconfirmed (NULL) first
        BauportalStatus.shorttitle,
    ).all()

    names = _project_name_map(
        db,
        [r.project_id for r in rows] + [r.suggested_project_id for r in rows],
    )

    entries: list[dict] = []
    for r in rows:
        phase = bauportal_status_to_main_phase(r.status_raw)
        entries.append(
            {
                "id": r.id,
                "bauportal_id": r.bauportal_id,
                "parent_bauportal_id": r.parent_bauportal_id,
                "shorttitle": r.shorttitle,
                "status_raw": r.status_raw,
                "mapped_phase": phase.value if phase is not None else None,
                "projecttime_raw": r.projecttime_raw,
                "url": r.url,
                "lat": r.lat,
                "lng": r.lng,
                "fetched_at": r.fetched_at,
                "suggested_project_id": r.suggested_project_id,
                "suggested_project_name": names.get(r.suggested_project_id),
                "project_id": r.project_id,
                "project_name": names.get(r.project_id),
            }
        )
    return entries


def confirm_match(db: Session, entry_id: int, project_id: int | None) -> dict | None:
    """Set or clear (``project_id=None``) the confirmed match for one entry.

    Re-materialises the previously- and newly-linked projects so derived
    BAUPORTAL observations stay in sync. Returns the updated entry dict, ``None``
    if the entry is missing, and raises :class:`ProjectNotFoundError` for an
    unknown ``project_id``.
    """

    row = db.query(BauportalStatus).filter(BauportalStatus.id == entry_id).first()
    if row is None:
        return None

    if project_id is not None:
        exists = db.query(Project.id).filter(Project.id == project_id).first()
        if exists is None:
            raise ProjectNotFoundError(f"Project {project_id} not found")

    old_project_id = row.project_id
    row.project_id = project_id
    db.commit()

    for affected in {old_project_id, project_id} - {None}:
        recompute_progress(db, affected)

    entries = list_entries(db)
    return next((e for e in entries if e["id"] == entry_id), None)
