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


def _entry_dict(r: BauportalStatus, names: dict[int, str]) -> dict:
    phase = bauportal_status_to_main_phase(r.status_raw)
    return {
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
        "confirmed": r.confirmed,
    }


def list_entries(db: Session, *, only_unconfirmed: bool = False) -> list[dict]:
    """List Bauportal entries with resolved suggestion / match names.

    Unconfirmed entries sort first (they need attention), then by title.
    """

    query = db.query(BauportalStatus)
    if only_unconfirmed:
        query = query.filter(BauportalStatus.confirmed.is_(False))
    rows = query.order_by(
        BauportalStatus.confirmed,  # unconfirmed (False) first
        BauportalStatus.shorttitle,
    ).all()

    names = _project_name_map(
        db,
        [r.project_id for r in rows] + [r.suggested_project_id for r in rows],
    )
    return [_entry_dict(r, names) for r in rows]


def update_entry(db: Session, entry_id: int, payload: dict) -> dict | None:
    """Set the assigned project and/or confirm flag for one entry.

    ``project_id`` (may be ``None`` to clear) and ``confirmed`` are both
    optional. Clearing the project also drops the confirm flag (nothing to
    confirm). Re-materialises the previously- and newly-linked projects so
    derived BAUPORTAL observations stay in sync. Returns the updated entry dict,
    ``None`` if the entry is missing, and raises :class:`ProjectNotFoundError`
    for an unknown ``project_id``.
    """

    row = db.query(BauportalStatus).filter(BauportalStatus.id == entry_id).first()
    if row is None:
        return None

    old_project_id = row.project_id

    if "project_id" in payload:
        project_id = payload["project_id"]
        if project_id is not None:
            exists = db.query(Project.id).filter(Project.id == project_id).first()
            if exists is None:
                raise ProjectNotFoundError(f"Project {project_id} not found")
        row.project_id = project_id
        if project_id is None:
            row.confirmed = False

    if "confirmed" in payload:
        # Can only confirm a row that actually has an assigned project.
        row.confirmed = bool(payload["confirmed"]) and row.project_id is not None

    db.commit()

    for affected in {old_project_id, row.project_id} - {None}:
        recompute_progress(db, affected)

    names = _project_name_map(db, [row.project_id, row.suggested_project_id])
    return _entry_dict(row, names)


def confirm_all(db: Session) -> int:
    """Confirm every assigned-but-unconfirmed entry in one step.

    Skips entries without an assigned project. Re-materialises each affected
    project once and returns the number of newly confirmed entries.
    """

    rows = (
        db.query(BauportalStatus)
        .filter(
            BauportalStatus.confirmed.is_(False),
            BauportalStatus.project_id.isnot(None),
        )
        .all()
    )
    affected: set[int] = set()
    for row in rows:
        row.confirmed = True
        if row.project_id is not None:
            affected.add(row.project_id)
    db.commit()

    for project_id in affected:
        recompute_progress(db, project_id)
    return len(rows)
