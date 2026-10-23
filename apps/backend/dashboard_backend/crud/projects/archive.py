"""Archive a replaced or superseded project (docs/features/feature-project-archive.md).

An archived project keeps its own history (VIB, Infraplan, changelog, geometry) but
counts nowhere: lists, maps, pickers and every parent aggregation skip it. Archiving
is refused while FinVe or GVFG links, non-archived subprojects or the lifecycle
ABGEBROCHEN would make that silently wrong. REST and MCP share these functions, so
both write the same ARCHIVE / UNARCHIVE changelog entry.
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


class ArchiveError(ValueError):
    """Raised when a project cannot be archived or restored. The message is
    user-facing (German) and names the blocking links."""


def _blocking_links(db: Session, project: Project) -> list[str]:
    """FinVe/GVFG links, non-archived subprojects and ABGEBROCHEN — each one a
    reason to refuse archiving (feature doc W4, W5, F2)."""
    reasons: list[str] = []

    finves = (
        db.query(Finve.id, Finve.name)
        .join(FinveToProject, FinveToProject.finve_id == Finve.id)
        .filter(FinveToProject.project_id == project.id)
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


def kept_links(db: Session, project_id: int) -> dict[str, int]:
    """Historical source links an archived project keeps (feature doc F1): they
    stay on the project and no longer reach its parent. Only non-zero counts."""

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
    return {key: value for key, value in counts.items() if value}


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


def archive_project(
    db: Session,
    project_id: int,
    reason: str,
    user_id: int | None,
    username: str | None,
) -> dict[str, Any] | None:
    """Archive *project_id* with a mandatory *reason*. Returns ``{project,
    kept_links}`` or None if the project does not exist; raises ArchiveError."""
    project = get_project_by_id(db, project_id)
    if project is None:
        return None
    reason = (reason or "").strip()
    if not reason:
        raise ArchiveError("Zum Archivieren ist eine Begründung nötig.")
    if project.is_archived:
        raise ArchiveError(f"Projekt {project_id} ist bereits archiviert.")
    blocking = _blocking_links(db, project)
    if blocking:
        raise ArchiveError(
            f"Projekt {project_id} kann nicht archiviert werden, solange diese "
            "Verknüpfungen bestehen — erst umhängen: " + "; ".join(blocking)
        )

    update = {"is_archived": True, "archived_reason": reason}
    create_changelog_for_patch(db, project, update, user_id, username, action="ARCHIVE")
    project.is_archived = True
    project.archived_reason = reason
    project.archived_at = datetime.utcnow()
    db.commit()
    db.refresh(project)

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
    update = {"is_archived": False, "archived_reason": reason}
    create_changelog_for_patch(db, project, update, user_id, username, action="UNARCHIVE")
    project.is_archived = False
    project.archived_reason = None
    project.archived_at = None
    db.commit()
    db.refresh(project)

    _refresh_ancestors(db, project)
    db.refresh(project)
    return project


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
