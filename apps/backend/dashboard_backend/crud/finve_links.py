"""Edit the permanent FinVe ↔ project links (``finve_to_project.haushalt_year IS NULL``).

Every write path for permanent links outside the Haushalt import goes through
``change_finve_links``: the open-assignments page, the new-project wizard, the
FinVe and project edit UIs, the MCP tool and the changelog revert. Each changed
project gets a changelog entry ``finve_ids`` (sorted permanent FinVe ids before
and after) and its planning state is recomputed — FinVes are lower bounds of the
planning state, so a removed link must drop its observation at once.

Year-scoped links of Sammel-FinVes are never touched here.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy.orm import Session

from dashboard_backend.crud.projects.progress import recompute_progress
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.change_tracking import ChangeLog, ChangeLogEntry
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.users import User

FINVE_IDS_FIELD = "finve_ids"


class FinveLinkError(ValueError):
    """A FinVe or project of a link change does not exist."""


def permanent_finve_ids(db: Session, project_id: int) -> list[int]:
    """Sorted ids of the FinVes permanently linked to a project."""
    rows = (
        db.query(FinveToProject.finve_id)
        .filter(FinveToProject.project_id == project_id, FinveToProject.haushalt_year.is_(None))
        .all()
    )
    return sorted({r[0] for r in rows})


def permanent_projects(db: Session, finve_id: int) -> list[Project]:
    """Projects permanently linked to a FinVe, sorted by id."""
    return (
        db.query(Project)
        .join(FinveToProject, FinveToProject.project_id == Project.id)
        .filter(FinveToProject.finve_id == finve_id, FinveToProject.haushalt_year.is_(None))
        .order_by(Project.id)
        .all()
    )


def _require_existing(db: Session, model, ids: Iterable[int], label: str) -> None:
    wanted = set(ids)
    if not wanted:
        return
    found = {r[0] for r in db.query(model.id).filter(model.id.in_(wanted)).all()}
    missing = sorted(wanted - found)
    if missing:
        raise FinveLinkError(f"{label} nicht gefunden: {', '.join(map(str, missing))}")


def change_finve_links(
    db: Session,
    *,
    add: Iterable[tuple[int, int]] = (),
    remove: Iterable[tuple[int, int]] = (),
    user: User | None,
    action: str = "PATCH",
) -> list[int]:
    """Add/remove permanent links given as ``(project_id, finve_id)`` pairs.

    Adding an existing link or removing a missing one is a no-op. Commits, then
    recomputes the planning state of every project whose links changed; returns
    those project ids.
    """
    add, remove = set(add), set(remove)
    if add & remove:
        raise FinveLinkError("Eine Zuordnung steht sowohl beim Hinzufügen als auch beim Entfernen.")
    _require_existing(db, Project, (p for p, _ in add), "Projekt(e)")
    _require_existing(db, Finve, (f for _, f in add), "FinVe(s)")

    project_ids = {p for p, _ in add | remove}
    before = {pid: permanent_finve_ids(db, pid) for pid in project_ids}

    for project_id, finve_id in add:
        if finve_id not in before[project_id]:
            db.add(FinveToProject(project_id=project_id, finve_id=finve_id, haushalt_year=None))
    for project_id, finve_id in remove:
        db.query(FinveToProject).filter(
            FinveToProject.project_id == project_id,
            FinveToProject.finve_id == finve_id,
            FinveToProject.haushalt_year.is_(None),
        ).delete(synchronize_session=False)
    db.flush()

    changed: list[int] = []
    for project_id in sorted(project_ids):
        after = permanent_finve_ids(db, project_id)
        if after == before[project_id]:
            continue
        changed.append(project_id)
        db.add(
            ChangeLog(
                project_id=project_id,
                user_id=user.id if user else None,
                username_snapshot=user.username if user else None,
                timestamp=datetime.utcnow(),
                action=action,
                entries=[
                    ChangeLogEntry(
                        field_name=FINVE_IDS_FIELD,
                        old_value=json.dumps(before[project_id]),
                        new_value=json.dumps(after),
                    )
                ],
            )
        )
    db.commit()
    # The ORM relationships (Project.finve / Finve.projects) were bypassed above.
    db.expire_all()
    for project_id in changed:
        recompute_progress(db, project_id)
    return changed


def update_finve_projects(
    db: Session,
    finve_id: int,
    *,
    add_project_ids: Iterable[int] = (),
    remove_project_ids: Iterable[int] = (),
    user: User | None,
) -> list[int]:
    """Add/remove projects of one FinVe. Returns the projects whose links changed."""
    _require_existing(db, Finve, [finve_id], "FinVe")
    return change_finve_links(
        db,
        add={(pid, finve_id) for pid in add_project_ids},
        remove={(pid, finve_id) for pid in remove_project_ids},
        user=user,
    )


def set_project_finves(
    db: Session,
    project_id: int,
    finve_ids: Iterable[int],
    *,
    user: User | None,
    action: str = "PATCH",
) -> list[int]:
    """Make ``finve_ids`` the project's permanent FinVe links (used by the revert)."""
    current = set(permanent_finve_ids(db, project_id))
    wanted = set(finve_ids)
    return change_finve_links(
        db,
        add={(project_id, f) for f in wanted - current},
        remove={(project_id, f) for f in current - wanted},
        user=user,
        action=action,
    )
