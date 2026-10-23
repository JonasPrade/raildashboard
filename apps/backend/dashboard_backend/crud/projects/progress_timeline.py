"""DB access for the multi-project timeline ("Zeitstrahl") of a project group.

All inputs are loaded with a constant number of bulk queries over the group's
projects and their subtrees; the per-row assembly is the pure
:func:`services.progress_timeline.build_timeline`. Stored observations are read
as they are — no lazy resync per project (that would cost ~10 queries each);
the detail page's GET keeps them fresh.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from dashboard_backend.crud.projects.projects import replaced_project_ids
from dashboard_backend.crud.projects.progress import (
    _to_inputs,
    expected_report_dates,
    pfa_forecast_input,
    split_expected,
)
from dashboard_backend.models.projects.progress_enums import (
    LifecycleStatus,
    ObservationTrack,
)
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.associations.project_to_project_group import ProjectToProjectGroup
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.vib.vib_entry import VibEntry, vib_entry_project
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry
from dashboard_backend.models.vib.vib_report import VibReport
from dashboard_backend.services.date_precision import date_text
from dashboard_backend.services.progress_forecast import PfaForecastInput
from dashboard_backend.services.progress_timeline import ConstructionUnitInput, build_timeline


def _subtrees(db: Session, root_ids: list[int]) -> dict[int, set[int]]:
    """``{root_id: {root_id, *descendant_ids}}`` with one query per depth level.

    Replaced descendants (lifecycle ERSETZT) and their subtrees are left out: their
    successor carries the scheme (feature-project-replacement.md, W3)."""

    children_by_parent: dict[int, list[int]] = {}
    frontier = list(root_ids)
    seen = set(root_ids)
    while frontier:
        rows = (
            db.query(Project.id, Project.superior_project_id)
            .filter(Project.superior_project_id.in_(frontier), Project.is_draft.is_(False))
            .all()
        )
        frontier = []
        replaced = replaced_project_ids(db, [child_id for child_id, _ in rows])
        for child_id, parent_id in rows:
            if child_id in replaced:
                continue
            if child_id in seen:
                continue  # defensive: never loop on a broken hierarchy
            seen.add(child_id)
            children_by_parent.setdefault(parent_id, []).append(child_id)
            frontier.append(child_id)

    result: dict[int, set[int]] = {}
    for root in root_ids:
        members = {root}
        stack = [root]
        while stack:
            for child in children_by_parent.get(stack.pop(), []):
                if child not in members:
                    members.add(child)
                    stack.append(child)
        result[root] = members
    return result


def get_group_timeline(
    db: Session, group_id: int, *, only_superior: bool = True, today: date | None = None
) -> dict:
    """Timeline payload (matching ``ProjectGroupTimelineSchema``) for a group."""

    today = today or date.today()

    query = (
        db.query(Project.id, Project.name, Project.project_number, Project.superior_project_id)
        .join(Project.project_groups)
        .filter(ProjectGroup.id == group_id, Project.is_draft.is_(False))
    )
    if only_superior:
        query = query.filter(Project.superior_project_id.is_(None))
    projects = query.order_by(Project.name).all()

    root_ids = [p.id for p in projects]
    subtrees = _subtrees(db, root_ids)
    all_ids = sorted(set().union(*subtrees.values())) if subtrees else []

    # --- PFA milestone dates: via the VIB entry link and direct assignment ---
    pfas_by_project: dict[int, dict[int, PfaForecastInput]] = {}
    # PFA id → subproject it is assigned to (VibPfaEntry.project_id), if any.
    pfa_owner: dict[int, int | None] = {}
    if all_ids:
        linked = (
            db.query(VibPfaEntry, VibReport, vib_entry_project.c.project_id)
            .join(VibEntry, VibEntry.id == VibPfaEntry.vib_entry_id)
            .outerjoin(VibReport, VibReport.id == VibEntry.vib_report_id)
            .join(vib_entry_project, vib_entry_project.c.vib_entry_id == VibEntry.id)
            .filter(vib_entry_project.c.project_id.in_(all_ids), VibEntry.confirmed.is_(True))
            .all()
        )
        assigned = (
            db.query(VibPfaEntry, VibReport, VibPfaEntry.project_id)
            .join(VibEntry, VibEntry.id == VibPfaEntry.vib_entry_id)
            .outerjoin(VibReport, VibReport.id == VibEntry.vib_report_id)
            .filter(VibPfaEntry.project_id.in_(all_ids), VibEntry.confirmed.is_(True))
            .all()
        )
        for pfa, report, project_id in [*linked, *assigned]:
            pfa_owner[pfa.id] = pfa.project_id
            pfas_by_project.setdefault(project_id, {})[pfa.id] = pfa_forecast_input(pfa, report)

    # --- MAIN observations, split like the forecast / derivation read them ---
    expected_by_project: dict[int, list[ProgressObservation]] = {}
    evidence_by_project: dict[int, list[ProgressObservation]] = {}
    if all_ids:
        for obs in (
            db.query(ProgressObservation)
            .filter(
                ProgressObservation.project_id.in_(all_ids),
                ProgressObservation.track == ObservationTrack.MAIN.value,
            )
            .all()
        ):
            if obs.is_expected:
                if obs.observed_date is not None:
                    expected_by_project.setdefault(obs.project_id, []).append(obs)
            else:
                evidence_by_project.setdefault(obs.project_id, []).append(obs)

    reported = expected_report_dates(
        db, [obs for rows in expected_by_project.values() for obs in rows]
    )

    # Assumed build period per project from its groups (longest wins, as in
    # resolve_assumed_build_months).
    build_months: dict[int, int] = {}
    if all_ids:
        for project_id, months in (
            db.query(ProjectToProjectGroup.project_id, ProjectGroup.assumed_build_months)
            .join(ProjectGroup, ProjectGroup.id == ProjectToProjectGroup.project_group_id)
            .filter(
                ProjectToProjectGroup.project_id.in_(all_ids),
                ProjectGroup.assumed_build_months.isnot(None),
            )
        ):
            build_months[project_id] = max(build_months.get(project_id, 0), months)

    progress_by_project: dict[int, ProjectProgress] = {}
    if all_ids:
        progress_by_project = {
            row.project_id: row
            for row in db.query(ProjectProgress).filter(ProjectProgress.project_id.in_(all_ids))
        }

    items: list[dict] = []
    for project in projects:
        members = subtrees.get(project.id, {project.id})
        # A PFA reachable from several members (parent link + subproject
        # assignment) counts once.
        pfas: dict[int, PfaForecastInput] = {}
        expected: list[ProgressObservation] = []
        evidence: list[ProgressObservation] = []
        pf_dates: list[date] = []
        parl_dates: list[date] = []
        units: list[ConstructionUnitInput] = []
        for member in members:
            pfas.update(pfas_by_project.get(member, {}))
            expected.extend(expected_by_project.get(member, []))
            evidence.extend(evidence_by_project.get(member, []))
            progress = progress_by_project.get(member)
            if progress is not None:
                if progress.pf_date is not None:
                    pf_dates.append(progress.pf_date)
                if progress.parl_befassung_date is not None:
                    parl_dates.append(progress.parl_befassung_date)
            # The member's own construction interval: a PFA assigned to another
            # member of the subtree belongs to that member only (otherwise the
            # superior's VIB link would add the whole span as one interval).
            own_pfas = [
                pfa
                for pfa_id, pfa in pfas_by_project.get(member, {}).items()
                if pfa_owner.get(pfa_id) == member or pfa_owner.get(pfa_id) not in members
            ]
            unit_split = split_expected(expected_by_project.get(member, []), reported)
            units.append(
                ConstructionUnitInput(
                    pfas=own_pfas,
                    fulda=unit_split.fulda,
                    infraplan=unit_split.infraplan,
                    gvfg=unit_split.gvfg,
                    manual_expected=unit_split.manual,
                    assumed_build_months=build_months.get(member),
                )
            )

        split = split_expected(expected, reported)
        result = build_timeline(
            today=today,
            pfas=list(pfas.values()),
            fulda=split.fulda,
            infraplan=split.infraplan,
            gvfg=split.gvfg,
            manual_expected=split.manual,
            observations=_to_inputs(evidence),
            pf_dates=pf_dates,
            parl_dates=parl_dates,
            construction_units=units,
            assumed_build_months=build_months.get(project.id),
        )
        if not result.has_credible_dates:
            continue

        own_progress = progress_by_project.get(project.id)
        items.append(
            {
                "project_id": project.id,
                "name": project.name,
                "project_number": project.project_number,
                "superior_project_id": project.superior_project_id,
                "lifecycle_status": (
                    own_progress.lifecycle_status if own_progress else LifecycleStatus.AKTIV.value
                ),
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
            }
        )

    return {
        "group_id": group_id,
        "items": items,
        "without_dates_count": len(projects) - len(items),
    }
