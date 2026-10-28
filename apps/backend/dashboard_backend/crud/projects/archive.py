"""Archive a replaced or superseded project (docs/features/feature-project-archive.md).

An archived project keeps its own history (VIB, Infraplan, changelog, geometry) but
counts nowhere: lists, maps, pickers and every parent aggregation skip it. Archiving
is refused while permanent FinVe links, GVFG links, non-archived subprojects or the
lifecycle ABGEBROCHEN would make that silently wrong. Sammel-FinVe year links (from
the Haushalt import) do not block: they stay on the project as history. REST and MCP
share these functions, so both write the same ARCHIVE / UNARCHIVE changelog entry.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dashboard_backend.crud.changelog import create_changelog_for_patch
from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.crud.projects.projects import (
    ancestor_ids,
    get_project_by_id,
    recompute_geojson_for_parent,
)
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.associations.fulda_announcement_to_project import (
    fulda_announcement_to_project,
)
from dashboard_backend.models.gvfg import GvfgEntry, GvfgProgram, gvfg_entry_project
from dashboard_backend.models.infraplan import InfraplanEntryProject
from dashboard_backend.models.projects.bauportal_status import BauportalStatus
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.media_report import MediaReport
from dashboard_backend.models.projects.progress_enums import LifecycleStatus
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.vib.vib_entry_project import vib_entry_project
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry
from dashboard_backend.services.project_overlap import recompute_overlaps_for_project_ids


class ArchiveError(ValueError):
    """Raised when a project cannot be archived or restored. The message is
    user-facing (German) and names the blocking links."""


def _sammel_year_link():
    """A Sammel-FinVe year link: ``haushalt_year`` set on a Sammel-FinVe. Every
    other FinVe link (``haushalt_year IS NULL``) is a permanent one."""
    return FinveToProject.haushalt_year.isnot(None) & Finve.is_sammel_finve.is_(True)


def _blocking_links(db: Session, project: Project) -> list[str]:
    """Permanent FinVe links, GVFG links, non-archived subprojects and ABGEBROCHEN —
    each one a reason to refuse archiving (feature doc W4, W5, F2). Sammel-FinVe
    year links do not block (W5a): they stay as history, see kept_links."""
    reasons: list[str] = []

    finves = (
        db.query(Finve.id, Finve.name)
        .join(FinveToProject, FinveToProject.finve_id == Finve.id)
        .filter(FinveToProject.project_id == project.id, ~_sammel_year_link())
        .distinct()
        .order_by(Finve.id)
        .all()
    )
    if finves:
        names = ", ".join(f"{fid} ({name})" if name else str(fid) for fid, name in finves)
        reasons.append(f"FinVe: {names}")

    gvfg = db.execute(
        select(GvfgEntry.key, GvfgProgram.year_from)
        .join(gvfg_entry_project, gvfg_entry_project.c.entry_id == GvfgEntry.id)
        .join(GvfgProgram, GvfgProgram.id == GvfgEntry.program_id)
        .where(gvfg_entry_project.c.project_id == project.id)
        .order_by(GvfgProgram.year_from, GvfgEntry.key)
    ).all()
    if gvfg:
        reasons.append("GVFG: " + ", ".join(f"{key} ({year})" for key, year in gvfg))

    children = (
        db.query(Project.id, Project.name)
        .filter(Project.superior_project_id == project.id, Project.is_archived.is_(False))
        .order_by(Project.id)
        .all()
    )
    if children:
        reasons.append(
            "Teilprojekte: " + ", ".join(f"{cid} ({name})" for cid, name in children)
        )

    lifecycle = (
        db.query(ProjectProgress.lifecycle_status)
        .filter(ProjectProgress.project_id == project.id)
        .scalar()
    )
    if lifecycle == LifecycleStatus.ABGEBROCHEN.value:
        reasons.append(
            "Lebenszyklus ABGEBROCHEN — ein abgebrochenes Projekt bleibt sichtbar"
        )
    return reasons


def kept_links(db: Session, project_id: int) -> dict[str, int | list[int]]:
    """Historical source links an archived project keeps (feature doc F1, W5a): they
    stay on the project and no longer reach its parent. Only non-zero counts;
    ``sammel_finve_year_links`` lists the Sammel-FinVe numbers."""

    def count(column) -> int:
        return db.scalar(select(func.count()).where(column == project_id)) or 0

    counts = {
        "vib_entries": count(vib_entry_project.c.project_id),
        "vib_pfa_entries": count(VibPfaEntry.project_id),
        "infraplan_entries": count(InfraplanEntryProject.project_id),
        "fulda_announcements": count(fulda_announcement_to_project.c.project_id),
        "bauportal": count(BauportalStatus.project_id),
        "media_reports": count(MediaReport.project_id),
    }
    kept: dict[str, int | list[int]] = {key: value for key, value in counts.items() if value}
    sammel = sorted(
        {
            fid
            for (fid,) in db.query(FinveToProject.finve_id)
            .join(Finve, Finve.id == FinveToProject.finve_id)
            .filter(FinveToProject.project_id == project_id, _sammel_year_link())
        }
    )
    if sammel:
        kept["sammel_finve_year_links"] = sammel
    return kept


def _refresh_ancestors(db: Session, project: Project) -> None:
    """The project left (or rejoined) its parent's aggregation: rebuild the
    geometry and the planning state of every ancestor."""
    parent_id = project.superior_project_id
    if parent_id is None:
        return
    recompute_geojson_for_parent(db, parent_id)
    parent_of = lambda pid: db.query(Project.superior_project_id).filter(Project.id == pid).scalar()  # noqa: E731
    for ancestor_id in [parent_id, *ancestor_ids(parent_id, parent_of)]:
        progress_crud.recompute_progress(db, ancestor_id)


def _check_successor(db: Session, project_id: int, successor_id: int) -> None:
    """A successor exists, is not the project itself, no draft and not archived —
    so no ring can form (feature doc → „Ersetzt durch“)."""
    if successor_id == project_id:
        raise ArchiveError("Ein Projekt kann sich nicht selbst ersetzen.")
    successor = get_project_by_id(db, successor_id)
    if successor is None:
        raise ArchiveError(f"Nachfolgeprojekt {successor_id} gibt es nicht.")
    if successor.is_draft:
        raise ArchiveError(f"Nachfolgeprojekt {successor_id} ist ein Entwurf.")
    if successor.is_archived:
        raise ArchiveError(f"Nachfolgeprojekt {successor_id} ist selbst archiviert.")


def archive_project(
    db: Session,
    project_id: int,
    reason: str,
    user_id: int | None,
    username: str | None,
    replaced_by_project_id: int | None = None,
) -> dict[str, Any] | None:
    """Archive *project_id* with a mandatory *reason* and, optionally, the project
    that replaced it. Returns ``{project, kept_links}`` or None if the project does
    not exist; raises ArchiveError."""
    project = get_project_by_id(db, project_id)
    if project is None:
        return None
    reason = (reason or "").strip()
    if not reason:
        raise ArchiveError("Zum Archivieren ist eine Begründung nötig.")
    if project.is_archived:
        raise ArchiveError(f"Projekt {project_id} ist bereits archiviert.")
    if replaced_by_project_id is not None:
        _check_successor(db, project_id, replaced_by_project_id)
    blocking = _blocking_links(db, project)
    if blocking:
        raise ArchiveError(
            f"Projekt {project_id} kann nicht archiviert werden, solange diese "
            "Verknüpfungen bestehen — erst umhängen: " + "; ".join(blocking)
        )

    update: dict[str, Any] = {"is_archived": True, "archived_reason": reason}
    if replaced_by_project_id is not None:
        update["replaced_by_project_id"] = replaced_by_project_id
    create_changelog_for_patch(db, project, update, user_id, username, action="ARCHIVE")
    project.is_archived = True
    project.archived_reason = reason
    project.archived_at = datetime.utcnow()
    project.replaced_by_project_id = replaced_by_project_id
    db.commit()
    db.refresh(project)

    # An archived project is not on the map: it leaves (or rejoins) the overlaps.
    recompute_overlaps_for_project_ids(db, [project.id])
    _refresh_ancestors(db, project)
    db.refresh(project)
    return {"project": project, "kept_links": kept_links(db, project.id)}


def unarchive_project(
    db: Session,
    project_id: int,
    reason: str | None,
    user_id: int | None,
    username: str | None,
) -> Project | None:
    """Restore an archived project. The optional *reason* is recorded in the
    changelog; the archive reason itself is cleared (it stays in the log)."""
    project = get_project_by_id(db, project_id)
    if project is None:
        return None
    if not project.is_archived:
        raise ArchiveError(f"Projekt {project_id} ist nicht archiviert.")
    parent = get_project_by_id(db, project.superior_project_id) if project.superior_project_id else None
    if parent is not None and parent.is_archived:
        raise ArchiveError(
            f"Das übergeordnete Projekt {parent.id} ist archiviert — erst dieses "
            "wiederherstellen oder das Projekt umhängen."
        )

    reason = (reason or "").strip() or None
    update: dict[str, Any] = {"is_archived": False, "archived_reason": reason}
    if project.replaced_by_project_id is not None:
        update["replaced_by_project_id"] = None
    create_changelog_for_patch(db, project, update, user_id, username, action="UNARCHIVE")
    project.is_archived = False
    project.archived_reason = None
    project.archived_at = None
    project.replaced_by_project_id = None
    db.commit()
    db.refresh(project)

    # An archived project is not on the map: it leaves (or rejoins) the overlaps.
    recompute_overlaps_for_project_ids(db, [project.id])
    _refresh_ancestors(db, project)
    db.refresh(project)
    return project


def _ref(pid: int, name: str, number: str | None) -> dict[str, Any]:
    return {"id": pid, "name": name, "project_number": number}


def replacement(db: Session, project_id: int) -> dict[str, Any]:
    """``replaced_by`` (successor of an archived project, or None) and ``replaces``
    (archived projects naming this one as their successor)."""
    successor = None
    successor_id = db.query(Project.replaced_by_project_id).filter(Project.id == project_id).scalar()
    if successor_id is not None:
        row = (
            db.query(Project.id, Project.name, Project.project_number)
            .filter(Project.id == successor_id)
            .first()
        )
        successor = _ref(*row) if row else None
    replaces = [
        _ref(*row)
        for row in db.query(Project.id, Project.name, Project.project_number)
        .filter(Project.replaced_by_project_id == project_id, Project.is_archived.is_(True))
        .order_by(Project.name, Project.id)
    ]
    return {"replaced_by": successor, "replaces": replaces}


def successor_map(db: Session) -> dict[int, int]:
    """Archived project → the first non-archived project its successor chain leads
    to. Importers hand a suggestion on with it (feature doc → R3); an archived
    project without (reachable) successor is not in the map."""
    direct = dict(
        db.query(Project.id, Project.replaced_by_project_id).filter(
            Project.is_archived.is_(True), Project.replaced_by_project_id.isnot(None)
        )
    )
    archived = {pid for (pid,) in db.query(Project.id).filter(Project.is_archived.is_(True))}
    final: dict[int, int] = {}
    for start in direct:
        seen, current = {start}, direct[start]
        while current in direct and current not in seen:
            seen.add(current)
            current = direct[current]
        if current not in archived:
            final[start] = current
    return final


def redirect_replaced(
    project_ids: list[int], successors: dict[int, int]
) -> tuple[list[int], dict[int, int]]:
    """Swap archived projects for their successors, order kept, no duplicates.
    Returns the new ids and ``{successor: archived}`` for every swap."""
    out: list[int] = []
    redirected: dict[int, int] = {}
    for pid in project_ids:
        target = successors.get(pid, pid)
        if target != pid:
            redirected.setdefault(target, pid)
        if target not in out:
            out.append(target)
    return out, redirected


def archived_warnings(db: Session, project_ids: list[int | None]) -> list[str]:
    """One line per archived project among *project_ids*, naming its successor —
    for the MCP assignment tools (a manual assignment stays allowed)."""
    ids = sorted({pid for pid in project_ids if pid is not None})
    if not ids:
        return []
    rows = (
        db.query(Project.id, Project.name, Project.replaced_by_project_id)
        .filter(Project.id.in_(ids), Project.is_archived.is_(True))
        .order_by(Project.id)
        .all()
    )
    successors = dict(
        db.query(Project.id, Project.name).filter(
            Project.id.in_({succ for _, _, succ in rows if succ is not None})
        )
    )
    return [
        f"Projekt {pid} „{name}“ ist archiviert"
        + (f" und ersetzt durch {succ} „{successors.get(succ, '')}“" if succ is not None else "")
        + " — Zuordnung gespeichert; meist gehört sie zum Nachfolger."
        for pid, name, succ in rows
    ]


def get_archived_projects(db: Session) -> list[dict[str, Any]]:
    """Archived projects for the admin archive page, newest first, with the
    name of their parent."""
    parent = Project.__table__.alias("parent")
    rows = db.execute(
        select(
            Project.id,
            Project.name,
            Project.project_number,
            Project.archived_reason,
            Project.archived_at,
            Project.superior_project_id,
            parent.c.name,
        )
        .outerjoin(parent, parent.c.id == Project.superior_project_id)
        .where(Project.is_archived.is_(True))
        .order_by(Project.archived_at.desc().nullslast(), Project.id)
    ).all()
    return [
        {
            "id": pid,
            "name": name,
            "project_number": number,
            "archived_reason": reason,
            "archived_at": archived_at,
            "superior_project_id": superior_id,
            "superior_project_name": superior_name,
        }
        for pid, name, number, reason, archived_at, superior_id, superior_name in rows
    ]
