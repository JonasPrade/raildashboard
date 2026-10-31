"""Bulk loader for the dated inputs of projects and their subtrees.

Shared by the multi-project timeline (all projects of a group) and the forecast
of one project, so both read a parent project the same way: pooled dates over
the whole subtree, the members' own construction intervals and the parts that
keep the commissioning open (feature-project-timeline.md → „Oberprojekte
schließen alle Teilabschnitte ein“).

All inputs come from a constant number of bulk queries over the roots and
their subtrees (no N+1). Stored observations and cached phases are read as
they are — no lazy resync per member.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from dashboard_backend.crud.projects.progress import (
    ExpectedSplit,
    _to_inputs,
    expected_report_dates,
    pfa_forecast_input,
    split_expected,
)
from dashboard_backend.models.associations.project_to_project_group import ProjectToProjectGroup
from dashboard_backend.models.projects.progress_enums import (
    LifecycleStatus,
    MainPhase,
    ObservationTrack,
)
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.vib.vib_entry import VibEntry, vib_entry_project
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry
from dashboard_backend.models.vib.vib_report import VibReport
from dashboard_backend.services.progress_derivation import ObservationInput
from dashboard_backend.services.progress_forecast import (
    CommissioningParts,
    ConcreteDate,
    PartCommissioning,
    PendingPart,
    PfaForecastInput,
    concrete_milestone_dates,
    reduce_expected,
)
from dashboard_backend.services.progress_materialization import (
    PfaInput,
    pfa_label,
    section_lacks_commissioning,
)
from dashboard_backend.services.progress_timeline import ConstructionUnitInput


@dataclass(frozen=True)
class _Pfa:
    """One PFA section as read for the bundling: forecast input plus the raw
    texts and the report it comes from."""

    forecast: PfaForecastInput
    raw: PfaInput
    report_key: tuple[int, date]  # (year, report date) — newest wins
    as_of: date | None


@dataclass
class SubtreeDates:
    """Pooled date inputs of one root project and its subtree."""

    pfas: list[PfaForecastInput] = field(default_factory=list)
    split: ExpectedSplit = field(default_factory=lambda: ExpectedSplit([], [], [], []))
    # The root's own expected dates (GVFG commissioning doubt reads them).
    own_split: ExpectedSplit = field(default_factory=lambda: ExpectedSplit([], [], [], []))
    evidence: list[ObservationInput] = field(default_factory=list)
    pf_dates: list[date] = field(default_factory=list)
    parl_dates: list[date] = field(default_factory=list)
    units: list[ConstructionUnitInput] = field(default_factory=list)
    assumed_build_months: int | None = None
    commissioning_parts: CommissioningParts | None = None


def subtrees(db: Session, root_ids: list[int]) -> tuple[dict[int, set[int]], dict[int, list[int]]]:
    """``{root_id: {root_id, *descendant_ids}}`` plus the child lists, with one
    query per depth level (drafts and archived projects excluded)."""

    children_by_parent: dict[int, list[int]] = {}
    frontier = list(root_ids)
    seen = set(root_ids)
    while frontier:
        rows = (
            db.query(Project.id, Project.superior_project_id)
            .filter(
                Project.superior_project_id.in_(frontier),
                Project.is_draft.is_(False),
                Project.is_archived.is_(False),
            )
            .all()
        )
        frontier = []
        for child_id, parent_id in rows:
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
    return result, children_by_parent


def _phase_of(progress: ProjectProgress | None) -> MainPhase | None:
    """Effective phase from the cache (override before computed); None when the
    planning state is unknown (same reading as ``_cached_known``)."""

    if progress is None:
        return None
    if progress.manual_phase_override:
        try:
            return MainPhase(progress.manual_phase_override)
        except ValueError:
            return None
    if (progress.computed_confidence or 0) <= 0 or not progress.computed_phase:
        return None
    try:
        return MainPhase(progress.computed_phase)
    except ValueError:
        return None


def _newest(pfas: list[_Pfa]) -> list[_Pfa]:
    """The sections of the newest report (the current PFA table)."""

    if not pfas:
        return []
    newest = max(p.report_key for p in pfas)
    return [p for p in pfas if p.report_key == newest]


def _section_part(pfa: _Pfa, owner: str) -> PartCommissioning | None:
    f = pfa.forecast
    if f.inbetriebnahme is None:
        return None
    return PartCommissioning(
        name=f"{owner}: {pfa_label(pfa.raw)}",
        date=ConcreteDate(
            date=f.inbetriebnahme, source="VIB-PFA", precision=f.inbetriebnahme_precision
        ),
    )


def load_subtree_dates(
    db: Session, root_ids: list[int], today: date
) -> dict[int, SubtreeDates]:
    """Dated inputs per root (see :class:`SubtreeDates`)."""

    if not root_ids:
        return {}
    members_by_root, children_by_parent = subtrees(db, root_ids)
    all_ids = sorted(set().union(*members_by_root.values()))

    names = dict(db.query(Project.id, Project.name).filter(Project.id.in_(all_ids)))

    # --- PFA milestone dates: via the VIB entry link and direct assignment ---
    pfas_by_project: dict[int, dict[int, _Pfa]] = {}
    # PFA id → subproject it is assigned to (VibPfaEntry.project_id), if any.
    pfa_owner: dict[int, int | None] = {}
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
        forecast = pfa_forecast_input(pfa, report)
        year = report.year if report is not None else 0
        pfas_by_project.setdefault(project_id, {})[pfa.id] = _Pfa(
            forecast=forecast,
            raw=PfaInput(
                id=pfa.id,
                nr_pfa=pfa.nr_pfa,
                abschnitt_label=pfa.abschnitt_label,
                datum_pfb=pfa.datum_pfb,
                baubeginn=pfa.baubeginn,
                inbetriebnahme=pfa.inbetriebnahme,
            ),
            report_key=(year, forecast.reported_on or date.min),
            as_of=forecast.reported_on,
        )

    # --- MAIN observations, split like the forecast / derivation read them ---
    expected_by_project: dict[int, list[ProgressObservation]] = {}
    evidence_by_project: dict[int, list[ProgressObservation]] = {}
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
    for project_id, months in (
        db.query(ProjectToProjectGroup.project_id, ProjectGroup.assumed_build_months)
        .join(ProjectGroup, ProjectGroup.id == ProjectToProjectGroup.project_group_id)
        .filter(
            ProjectToProjectGroup.project_id.in_(all_ids),
            ProjectGroup.assumed_build_months.isnot(None),
        )
    ):
        build_months[project_id] = max(build_months.get(project_id, 0), months)

    progress_by_project: dict[int, ProjectProgress] = {
        row.project_id: row
        for row in db.query(ProjectProgress).filter(ProjectProgress.project_id.in_(all_ids))
    }

    result: dict[int, SubtreeDates] = {}
    for root in root_ids:
        members = members_by_root.get(root, {root})
        out = SubtreeDates(assumed_build_months=build_months.get(root))
        # A PFA reachable from several members (parent link + subproject
        # assignment) counts once.
        pooled_pfas: dict[int, PfaForecastInput] = {}
        expected: list[ProgressObservation] = []
        evidence: list[ProgressObservation] = []
        parts: list[PartCommissioning] = []
        pending: list[PendingPart] = []
        for member in sorted(members, key=lambda m: (m != root, names.get(m) or "")):
            member_pfas = pfas_by_project.get(member, {})
            pooled_pfas.update({pid: p.forecast for pid, p in member_pfas.items()})
            expected.extend(expected_by_project.get(member, []))
            evidence.extend(evidence_by_project.get(member, []))
            progress = progress_by_project.get(member)
            if progress is not None:
                if progress.pf_date is not None:
                    out.pf_dates.append(progress.pf_date)
                if progress.parl_befassung_date is not None:
                    out.parl_dates.append(progress.parl_befassung_date)
            # The member's own sections: a PFA assigned to another member of
            # the subtree belongs to that member only (otherwise the parent's
            # VIB link would add the whole span as one interval).
            own = [
                pfa
                for pfa_id, pfa in member_pfas.items()
                if pfa_owner.get(pfa_id) == member or pfa_owner.get(pfa_id) not in members
            ]
            unit_split = split_expected(expected_by_project.get(member, []), reported)
            unit = ConstructionUnitInput(
                pfas=[p.forecast for p in own],
                fulda=unit_split.fulda,
                infraplan=unit_split.infraplan,
                gvfg=unit_split.gvfg,
                manual_expected=unit_split.manual,
                assumed_build_months=build_months.get(member),
            )
            out.units.append(unit)

            # --- Parts of the commissioning ---------------------------------
            if member != root and progress is not None and (
                progress.lifecycle_status == LifecycleStatus.ABGEBROCHEN.value
            ):
                continue  # a cancelled part never holds the project open
            name = names.get(member) or f"Projekt {member}"
            phase = _phase_of(progress)
            is_leaf = not any(c in members for c in children_by_parent.get(member, []))
            in_service = phase is MainPhase.IN_BETRIEB
            newest = _newest(own)
            if member != root and is_leaf:
                own_dates = concrete_milestone_dates(
                    pfas=unit.pfas,
                    fulda=unit.fulda,
                    infraplan=unit.infraplan,
                    gvfg=unit.gvfg,
                    manual_expected=unit.manual_expected,
                    today=today,
                    pfb_as_genehmigung=False,
                    assumed_build_months=unit.assumed_build_months,
                )
                ibn = own_dates.get(MainPhase.IN_BETRIEB)
                if ibn is not None:
                    parts.append(PartCommissioning(name=name, date=ibn))
                elif not in_service:
                    pending.append(PendingPart(name=name, project_id=member, phase=phase))
                    continue  # the leaf itself is open; its sections add nothing
            else:
                # Root and intermediate nodes: their own sections are parts.
                parts.extend(p for p in (_section_part(s, name) for s in newest) if p)
            if not in_service:
                for section in newest:
                    if section_lacks_commissioning(section.raw, section.as_of):
                        pending.append(
                            PendingPart(
                                name=f"{name}: {pfa_label(section.raw)}",
                                project_id=member,
                                phase=phase,
                            )
                        )

        out.pfas = list(pooled_pfas.values())
        pooled = split_expected(expected, reported)
        # Several manual entries per phase when a parent pools its subtree:
        # earliest start, latest commissioning (as the PFA sections).
        out.split = pooled._replace(manual=reduce_expected(pooled.manual))
        out.own_split = split_expected(expected_by_project.get(root, []), reported)
        out.evidence = _to_inputs(evidence)

        root_progress = progress_by_project.get(root)
        pinned_in_service = (
            root_progress is not None
            and root_progress.manual_phase_override == MainPhase.IN_BETRIEB.value
        )
        if pending and not pinned_in_service:
            own_claims = concrete_milestone_dates(
                pfas=[],
                fulda=out.own_split.fulda,
                infraplan=out.own_split.infraplan,
                gvfg=out.own_split.gvfg,
                manual_expected=[],
                today=today,
                pfb_as_genehmigung=False,
            )
            out.commissioning_parts = CommissioningParts(
                parts=tuple(parts),
                pending=tuple(pending),
                overall=own_claims.get(MainPhase.IN_BETRIEB),
                has_manual=any(c.phase is MainPhase.IN_BETRIEB for c in out.own_split.manual),
            )
        result[root] = out
    return result
