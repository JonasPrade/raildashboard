"""Shared helpers for the source-importer review CRUDs (fulda/media/bauportal).

Only the structurally repeated pieces live here; per-importer behavior rules
(e.g. Bauportal's "confirmed requires an assigned project") stay in the
feature modules. A fourth importer starts from these helpers instead of a
fourth copy.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from dashboard_backend.crud.projects.progress import recompute_progress
from dashboard_backend.models.projects.project import Project


class ProjectNotFoundError(Exception):
    """An update referenced a non-existent project (endpoints map this to 404)."""


def project_name_map(db: Session, ids: Iterable[int | None]) -> dict[int, str]:
    """Batched id → name lookup; ``None`` entries are ignored."""
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    rows = db.query(Project.id, Project.name).filter(Project.id.in_(wanted)).all()
    return {row.id: row.name for row in rows}


def ensure_projects_exist(db: Session, ids: Iterable[int]) -> list[Project]:
    """Validate that every id exists; return the ``Project`` rows in input order.

    Raises :class:`ProjectNotFoundError` naming the missing ids otherwise.
    """
    wanted = list(dict.fromkeys(ids))  # dedupe, keep order
    if not wanted:
        return []
    found = db.query(Project).filter(Project.id.in_(wanted)).all()
    by_id = {p.id: p for p in found}
    missing = [pid for pid in wanted if pid not in by_id]
    if missing:
        raise ProjectNotFoundError(f"Project(s) not found: {missing}")
    return [by_id[pid] for pid in wanted]


def apply_editable_fields(row: object, payload: dict, fields: set[str]) -> None:
    """setattr every payload key that is in the importer's editable-field set."""
    for key, value in payload.items():
        if key in fields:
            setattr(row, key, value)


def recompute_for(db: Session, ids: Iterable[int | None]) -> None:
    """Re-materialise progress for every distinct non-None project id."""
    for pid in {i for i in ids if i is not None}:
        recompute_progress(db, pid)
