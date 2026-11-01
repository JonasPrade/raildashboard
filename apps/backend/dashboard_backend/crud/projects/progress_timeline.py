"""DB access for the multi-project timeline ("Zeitstrahl") of a project group
and of the direct subprojects of one project.

All inputs are loaded with a constant number of bulk queries over the group's
projects and their subtrees (:func:`crud.projects.subtree_dates.load_subtree_dates`,
shared with the forecast); the per-row assembly is the pure
:func:`services.progress_timeline.build_timeline`. Stored observations are read
as they are — no lazy resync per project (that would cost ~10 queries each);
the detail page's GET keeps them fresh.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from dashboard_backend.crud.projects.subtree_dates import load_subtree_dates
from dashboard_backend.models.projects.progress_enums import LifecycleStatus
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.services.date_precision import date_text
from dashboard_backend.services.progress_timeline import build_timeline


def get_group_timeline(
    db: Session, group_id: int, *, only_superior: bool = True, today: date | None = None
) -> dict:
    """Timeline payload (matching ``ProjectGroupTimelineSchema``) for a group."""

    today = today or date.today()

    query = (
        db.query(Project.id, Project.name, Project.project_number, Project.superior_project_id)
        .join(Project.project_groups)
        .filter(
            ProjectGroup.id == group_id,
            Project.is_draft.is_(False),
            Project.is_archived.is_(False),
        )
    )
    if only_superior:
        query = query.filter(Project.superior_project_id.is_(None))
    projects = query.order_by(Project.name).all()

    items = _timeline_items(db, projects, today)
    return {
        "group_id": group_id,
        "items": items,
        "without_dates_count": len(projects) - len(items),
    }


def get_subprojects_timeline(db: Session, project_id: int, *, today: date | None = None) -> dict:
    """Timeline payload (matching ``SubprojectsTimelineSchema``) for the direct
    subprojects of a project — one row per subproject, each pooling its own subtree."""

    today = today or date.today()

    projects = (
        db.query(Project.id, Project.name, Project.project_number, Project.superior_project_id)
        .filter(
            Project.superior_project_id == project_id,
            Project.is_draft.is_(False),
            Project.is_archived.is_(False),
        )
        .order_by(Project.name)
        .all()
    )

    items = _timeline_items(db, projects, today)
    dated = {item["project_id"] for item in items}
    return {
        "project_id": project_id,
        "items": items,
        "without_dates": [
            {"project_id": p.id, "name": p.name} for p in projects if p.id not in dated
        ],
    }


def _timeline_items(db: Session, projects: list, today: date) -> list[dict]:
    """One timeline row per project with credible dates, in the given order.

    ``projects`` are rows with ``id``, ``name``, ``project_number`` and
    ``superior_project_id``; each row pools its whole subtree."""

    root_ids = [p.id for p in projects]
    inputs = load_subtree_dates(db, root_ids, today)
    lifecycle = (
        dict(
            db.query(ProjectProgress.project_id, ProjectProgress.lifecycle_status).filter(
                ProjectProgress.project_id.in_(root_ids)
            )
        )
        if root_ids
        else {}
    )

    items: list[dict] = []
    for project in projects:
        data = inputs[project.id]
        result = build_timeline(
            today=today,
            pfas=data.pfas,
            fulda=data.split.fulda,
            infraplan=data.split.infraplan,
            gvfg=data.split.gvfg,
            manual_expected=data.split.manual,
            observations=data.evidence,
            pf_dates=data.pf_dates,
            parl_dates=data.parl_dates,
            construction_units=data.units,
            assumed_build_months=data.assumed_build_months,
            commissioning_parts=data.commissioning_parts,
        )
        if not result.has_credible_dates:
            continue

        items.append(
            {
                "project_id": project.id,
                "name": project.name,
                "project_number": project.project_number,
                "superior_project_id": project.superior_project_id,
                "lifecycle_status": lifecycle.get(project.id) or LifecycleStatus.AKTIV.value,
                "milestones": [
                    {
                        "kind": m.kind,
                        "phase": m.phase.value if m.phase else None,
                        "date": m.date,
                        "source": m.source,
                        "certainty": m.certainty,
                        "date_precision": m.precision.value,
                        "date_label": m.label,
                        "date_text": date_text(m.date, m.precision, m.label),
                        "derivation": m.derivation,
                    }
                    for m in result.milestones
                ],
                "construction_periods": [
                    {"start": start, "end": end} for start, end in result.construction_periods
                ],
                "pending_parts": [
                    {
                        "project_id": part.project_id,
                        "name": part.name,
                        "phase": part.phase.value if part.phase else None,
                    }
                    for part in result.pending_parts
                ],
            }
        )

    return items
