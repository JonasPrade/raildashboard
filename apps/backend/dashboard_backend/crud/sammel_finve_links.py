"""Edit the year-scoped links of Sammel-FinVes (``finve_to_project.haushalt_year`` set).

The Haushalt import writes these links per report year; the Haushalt follow-up
(MCP ``set_sammel_finve_year_projects``, feature-haushalt-import.md →
„Nacharbeit per MCP“) corrects them afterwards. Each changed project gets a
changelog entry ``sammel_finve_years`` — ``{"finve_id": …, "years": […]}`` before
and after, revertable — and its planning state is recomputed (Sammel-FinVes are
observations of the planning state like any FinVe).

Archived projects keep their year links as history (feature-project-archive.md →
W5a): setting the projects of a year never removes them and never adds one.
Permanent links are edited in ``crud.finve_links``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy.orm import Session

from dashboard_backend.crud.finve_links import FinveLinkConflict, FinveLinkError, _require_existing
from dashboard_backend.crud.projects.progress import recompute_progress
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.change_tracking import ChangeLog, ChangeLogEntry
from dashboard_backend.models.projects.budget import Budget
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.users import User

SAMMEL_YEARS_FIELD = "sammel_finve_years"


def _sammel_finve(db: Session, finve_id: int) -> Finve:
    finve = db.get(Finve, finve_id)
    if finve is None:
        raise FinveLinkError(f"FinVe {finve_id} nicht gefunden.")
    if not finve.is_sammel_finve:
        raise FinveLinkError(
            f"FinVe {finve_id} ist keine Sammel-FinVe — feste Zuordnungen mit update_finve_projects."
        )
    return finve


def budget_years(db: Session, finve_id: int) -> list[int]:
    """Report years in which the FinVe is listed, ascending."""
    rows = db.query(Budget.budget_year).filter(Budget.fin_ve == finve_id).distinct()
    return sorted(r[0] for r in rows)


def project_sammel_years(db: Session, project_id: int, finve_id: int) -> list[int]:
    """Sorted years in which the project is linked to the Sammel-FinVe."""
    rows = db.query(FinveToProject.haushalt_year).filter(
        FinveToProject.project_id == project_id,
        FinveToProject.finve_id == finve_id,
        FinveToProject.haushalt_year.isnot(None),
    )
    return sorted({r[0] for r in rows})


def year_projects(db: Session, finve_id: int, year: int) -> list[Project]:
    """Projects linked to the Sammel-FinVe in one year, archived ones last."""
    return (
        db.query(Project)
        .join(FinveToProject, FinveToProject.project_id == Project.id)
        .filter(FinveToProject.finve_id == finve_id, FinveToProject.haushalt_year == year)
        .order_by(Project.is_archived, Project.id)
        .all()
    )


def change_sammel_links(
    db: Session,
    finve_id: int,
    *,
    add: Iterable[tuple[int, int]] = (),
    remove: Iterable[tuple[int, int]] = (),
    user: User | None,
    action: str = "PATCH",
) -> list[int]:
    """Add/remove year links given as ``(project_id, year)`` pairs of one Sammel-FinVe.

    Adding an existing link or removing a missing one is a no-op. Commits, then
    recomputes the planning state of every project whose links changed; returns
    those project ids.
    """
    add, remove = set(add), set(remove)
    if add & remove:
        raise FinveLinkError("Eine Zuordnung steht sowohl beim Hinzufügen als auch beim Entfernen.")
    _sammel_finve(db, finve_id)
    _require_existing(db, Project, (p for p, _ in add), "Projekt(e)")
    listed = set(budget_years(db, finve_id))
    unknown = sorted({y for _, y in add} - listed)
    if unknown:
        raise FinveLinkError(
            f"FinVe {finve_id} steht nicht im Haushalt {', '.join(map(str, unknown))} "
            f"(Jahre: {', '.join(map(str, sorted(listed))) or 'keine'})."
        )
    archived = sorted(
        r[0]
        for r in db.query(Project.id).filter(
            Project.id.in_({p for p, _ in add}), Project.is_archived.is_(True)
        )
    )
    if archived:
        raise FinveLinkConflict(
            f"Projekt(e) archiviert, keine neue Zuordnung möglich: {', '.join(map(str, archived))}"
        )

    project_ids = {p for p, _ in add | remove}
    before = {pid: project_sammel_years(db, pid, finve_id) for pid in project_ids}

    for project_id, year in add:
        if year not in before[project_id]:
            db.add(FinveToProject(project_id=project_id, finve_id=finve_id, haushalt_year=year))
    for project_id, year in remove:
        db.query(FinveToProject).filter(
            FinveToProject.project_id == project_id,
            FinveToProject.finve_id == finve_id,
            FinveToProject.haushalt_year == year,
        ).delete(synchronize_session=False)
    db.flush()

    changed: list[int] = []
    for project_id in sorted(project_ids):
        after = project_sammel_years(db, project_id, finve_id)
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
                        field_name=SAMMEL_YEARS_FIELD,
                        old_value=json.dumps({"finve_id": finve_id, "years": before[project_id]}),
                        new_value=json.dumps({"finve_id": finve_id, "years": after}),
                    )
                ],
            )
        )
    db.commit()
    db.expire_all()
    for project_id in changed:
        recompute_progress(db, project_id)
    return changed


def set_year_projects(
    db: Session,
    finve_id: int,
    years: Iterable[int],
    project_ids: Iterable[int],
    *,
    user: User | None,
) -> list[int]:
    """Make ``project_ids`` the projects of the Sammel-FinVe in each of ``years``.

    Links of archived projects stay as history and do not count as current.
    """
    wanted = set(project_ids)
    add: set[tuple[int, int]] = set()
    remove: set[tuple[int, int]] = set()
    for year in set(years):
        current = {p.id for p in year_projects(db, finve_id, year) if not p.is_archived}
        add |= {(pid, year) for pid in wanted - current}
        remove |= {(pid, year) for pid in current - wanted}
    return change_sammel_links(db, finve_id, add=add, remove=remove, user=user)


def set_project_sammel_years(
    db: Session,
    project_id: int,
    finve_id: int,
    years: Iterable[int],
    *,
    user: User | None,
    action: str = "PATCH",
) -> list[int]:
    """Make ``years`` the project's years in the Sammel-FinVe (used by the revert)."""
    current = set(project_sammel_years(db, project_id, finve_id))
    wanted = set(years)
    return change_sammel_links(
        db,
        finve_id,
        add={(project_id, y) for y in wanted - current},
        remove={(project_id, y) for y in current - wanted},
        user=user,
        action=action,
    )
