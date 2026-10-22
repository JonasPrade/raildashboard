"""DB access for the project-progress feature.

Phase 1 derives the headline from **manual** observations + flags + lifecycle
and caches the result on the ``project_progress`` row. The derivation itself is
delegated to the pure ``services.progress_derivation`` module. Phase 2 will add
``sync_derived_observations`` (materialise VIB/FinVe rows) and a real lazy
resync; the seams (``STALENESS_WINDOW``, ``is_derived`` guard) already exist.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import NamedTuple

from sqlalchemy.orm import Session, joinedload, selectinload

from dashboard_backend.models.associations.progress_track_document import (
    ProgressTrackDocument,
)
from dashboard_backend.models.change_tracking import ChangeLog, ChangeLogEntry
from dashboard_backend.models.projects.document import Document
from dashboard_backend.models.projects.progress_enums import (
    LifecycleStatus,
    MainPhase,
    ObservationTrack,
    ParallelState,
    SourceType,
)
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.users import User
from dashboard_backend.models.vib.vib_entry import VibEntry, vib_entry_project
from dashboard_backend.services.progress_derivation import (
    STALENESS_WINDOW,
    AggregationNode,
    DerivationResult,
    ObservationInput,
    aggregate_tree,
    derive_headline,
)
from dashboard_backend.services.gvfg_ibn_check import check_ibn_against_gvfg, known_ibn
from dashboard_backend.services.progress_dates import parse_flexible_date
from dashboard_backend.services.progress_forecast import (
    BvwpDurations,
    ExpectedDate,
    PfaForecastInput,
    build_forecast,
)
from dashboard_backend.services.progress_materialization import (
    DerivedSpec,
    PfaInput,
    bauportal_to_spec,
    finve_to_spec,
    fulda_to_spec,
    gvfg_entry_to_specs,
    gvfg_ibn_year,
    infraplan_entry_to_specs,
    infraplan_parl_relevant,
    media_to_spec,
    pfa_has_pf_evidence,
    pfa_to_specs,
    vib_entry_to_specs,
)
from dashboard_backend.models.projects.bauportal_status import BauportalStatus
from dashboard_backend.models.associations.fulda_announcement_to_project import (
    fulda_announcement_to_project,
)
from dashboard_backend.models.projects.fulda_announcement import FuldaAnnouncement
from dashboard_backend.models.projects.fulda_document import FuldaDocument
from dashboard_backend.models.projects.media_report import MediaReport
from dashboard_backend.models.projects.bvwp_project_data import BvwpProjectData
from dashboard_backend.models.gvfg import GvfgEntry, GvfgProgram, gvfg_entry_project
from dashboard_backend.models.infraplan import (
    InfraplanEntry,
    InfraplanEntryProject,
    InfraplanReport,
)
from dashboard_backend.crud import gvfg as gvfg_crud
from dashboard_backend.services.gvfg_parser import normalize_key
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry
from dashboard_backend.models.vib.vib_report import VibReport

# A project whose group membership includes a "BSWAG*" group (Bedarfsplan
# Schiene / BSWAG) defaults to parliamentary relevance. The nullable
# ``parl_befassung_relevant`` override stays authoritative when set.
BEDARFSPLAN_GROUP_SHORT_NAME_PREFIX = "BSWAG"


class DerivedObservationDeleteError(Exception):
    """Raised when a caller tries to delete a derived (materialised) observation."""


# --- Change tracking ---------------------------------------------------------
#
# Every user-triggered planning-state change lands in the project ``change_log``
# (REST and MCP alike). Field names carry the ``progress.`` prefix: they are not
# Project columns, so the revert endpoint rejects them — the entries are history.

CHANGELOG_PREFIX = "progress."

_TRACKED_PROGRESS_FIELDS = (
    "has_planfeststellung",
    "parl_befassung_relevant",
    "lifecycle_status",
    "manual_phase_override",
    "manual_override_note",
    "pf_state_override",
    "parl_state_override",
    "parl_befassung_text",
    "parl_drucksache_url",
    "parl_befassung_date",
    "pf_text",
    "pf_date",
    "pf_links",
)

_TRACK_LABELS = {"MAIN": "Hauptpfad", "PF": "Planfeststellung", "PARL": "Parlament"}


def _changelog_value(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, (date, datetime)):
        value = value.isoformat()
    return json.dumps(value, default=str, ensure_ascii=False)


def _snapshot(progress: ProjectProgress) -> dict:
    return {field: getattr(progress, field) for field in _TRACKED_PROGRESS_FIELDS}


def _log_progress_change(
    db: Session,
    project_id: int,
    user: User | None,
    action: str,
    changes: list[tuple[str, object, object]],
) -> ChangeLog | None:
    """Add a ChangeLog for the given ``(field, old, new)`` triples; unchanged
    fields are skipped. The caller commits."""
    entries = [
        ChangeLogEntry(
            field_name=CHANGELOG_PREFIX + field,
            old_value=_changelog_value(old),
            new_value=_changelog_value(new),
        )
        for field, old, new in changes
        if _changelog_value(old) != _changelog_value(new)
    ]
    if not entries:
        return None
    changelog = ChangeLog(
        project_id=project_id,
        user_id=user.id if user else None,
        username_snapshot=user.username if user else None,
        timestamp=datetime.utcnow(),
        action=action,
        entries=entries,
    )
    db.add(changelog)
    return changelog


def _snapshot_diff(before: dict, after: dict) -> list[tuple[str, object, object]]:
    return [(field, before[field], after[field]) for field in _TRACKED_PROGRESS_FIELDS]


def observation_summary(observation: ProgressObservation) -> str:
    """One readable line per observation for the change log."""
    parts = [
        f"#{observation.id} {_TRACK_LABELS.get(observation.track, observation.track)}: "
        f"{observation.asserted_state}"
    ]
    if observation.observed_date:
        date_text = observation.observed_date.strftime("%d.%m.%Y")
        parts.append(f"{date_text} (erwartet)" if observation.is_expected else date_text)
    parts.append(observation.source_type)
    if observation.confidence is not None:
        parts.append(f"Konfidenz {observation.confidence:g}")
    if observation.note:
        parts.append(observation.note)
    return " · ".join(parts)


# --- Internal helpers --------------------------------------------------------


def get_or_create_progress(db: Session, project_id: int) -> ProjectProgress:
    progress = (
        db.query(ProjectProgress)
        .filter(ProjectProgress.project_id == project_id)
        .first()
    )
    if progress is None:
        progress = ProjectProgress(
            project_id=project_id,
            lifecycle_status=LifecycleStatus.AKTIV.value,
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress


def resolve_parl_relevant(
    progress: ProjectProgress, project: Project, infraplan_relevant: bool | None = None
) -> bool:
    """Override wins; then the newest Infraplan statement on the Befassung
    (``nicht vereinbart`` → not relevant, see :func:`infraplan_parl_relevance`);
    otherwise default on for BSWAG* group membership."""

    if progress.parl_befassung_relevant is not None:
        return progress.parl_befassung_relevant
    if infraplan_relevant is not None:
        return infraplan_relevant
    return any(
        (g.short_name or "").upper().startswith(BEDARFSPLAN_GROUP_SHORT_NAME_PREFIX)
        for g in project.project_groups
    )


def infraplan_parl_relevance(db: Session, project_ids: list[int]) -> dict[int, bool]:
    """PaBe relevance "laut Infraplan" per project: the newest linked
    Bedarfsplan entry that states the Befassung decides. Projects without
    such an entry are missing from the result."""

    if not project_ids:
        return {}
    rows = (
        db.query(InfraplanEntryProject.project_id, InfraplanReport.year, InfraplanEntry.parl_state)
        .join(InfraplanEntry, InfraplanEntry.id == InfraplanEntryProject.entry_id)
        .join(InfraplanReport, InfraplanReport.id == InfraplanEntry.report_id)
        .filter(
            InfraplanEntryProject.project_id.in_(project_ids),
            InfraplanEntry.parl_state.isnot(None),
        )
        .all()
    )
    newest: dict[int, int] = {}
    result: dict[int, bool] = {}
    for project_id, year, parl_state in sorted(rows, key=lambda r: -r[1]):
        if newest.setdefault(project_id, year) != year:
            continue
        relevant = infraplan_parl_relevant(parl_state)
        # Several rows of the same year: one statement of relevance suffices.
        result[project_id] = bool(result.get(project_id)) or bool(relevant)
    return result


def resolve_skipped_phases(project: Project) -> set[MainPhase]:
    """Planning phases the project skips by group default (#164).

    A phase counts as skipped only when *every* group of the project skips it,
    so membership in one renewal group doesn't strip phases from a project that
    another group plans in full. No groups → nothing skipped.
    """

    groups = list(project.project_groups)
    if not groups:
        return set()
    per_group = [
        {phase for phase in (_enum_or_none(MainPhase, v) for v in (g.skipped_phases or [])) if phase}
        for g in groups
    ]
    return set.intersection(*per_group)


def resolve_hidden_phases(skipped: set[MainPhase], in_use: set[MainPhase]) -> list[str]:
    """Skipped phases the progress view hides: data wins, so a phase still shows
    when the project (or a subproject, or a dated forecast step) sits in it."""

    return [p.value for p in MainPhase if p in skipped and p not in in_use]


def _to_inputs(observations: list[ProgressObservation]) -> list[ObservationInput]:
    inputs: list[ObservationInput] = []
    for obs in observations:
        try:
            source = SourceType(obs.source_type)
            track = ObservationTrack(obs.track)
        except ValueError:
            continue  # ignore rows with unknown enum values
        inputs.append(
            ObservationInput(
                source_type=source,
                track=track,
                asserted_state=obs.asserted_state,
                observed_date=obs.observed_date,
                confidence=obs.confidence,
                note=obs.note,
                id=obs.id,
            )
        )
    return inputs


def _enum_or_none(enum_cls, value):
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


def pfa_forecast_input(pfa: VibPfaEntry, report: VibReport | None) -> PfaForecastInput:
    """PFA milestone dates plus the date of the VIB report they come from."""

    reported_on = None
    if report is not None:
        reported_on = report.report_date or date(report.year, 12, 31)
    return PfaForecastInput(
        datum_pfb=parse_flexible_date(pfa.datum_pfb),
        baubeginn=parse_flexible_date(pfa.baubeginn),
        inbetriebnahme=parse_flexible_date(pfa.inbetriebnahme),
        reported_on=reported_on,
    )


class ReportedOn(NamedTuple):
    """Date of the report a derived expected observation comes from."""

    fulda: dict[int, date]  # Fulda announcement id → answer date
    infraplan: dict[int, date]  # Infraplan entry id → publication date
    gvfg: dict[int, date]  # GVFG entry id → Stand of its edition


def _gvfg_stand(program: GvfgProgram) -> date:
    """Stand of an edition; 1 Jan of its first year when none was printed."""
    return program.stand or date(program.year_from, 1, 1)


def _infraplan_report_date(report: InfraplanReport) -> date:
    """Publication date of a year; the import date when none was given."""
    return report.published_on or report.created_at.date()


def expected_report_dates(
    db: Session, observations: list[ProgressObservation]
) -> ReportedOn:
    """Report dates for the derived expected rows in ``observations`` — one
    query per source for any number of rows."""

    announcement_ids = {
        o.fulda_announcement_id
        for o in observations
        if o.is_derived and o.fulda_announcement_id
    }
    entry_ids = {
        o.infraplan_entry_id for o in observations if o.is_derived and o.infraplan_entry_id
    }
    fulda: dict[int, date] = {}
    if announcement_ids:
        fulda = dict(
            db.query(FuldaAnnouncement.id, FuldaDocument.document_date)
            .join(FuldaDocument, FuldaDocument.id == FuldaAnnouncement.document_id)
            .filter(FuldaAnnouncement.id.in_(announcement_ids))
            .all()
        )
    infraplan: dict[int, date] = {}
    if entry_ids:
        infraplan = {
            entry_id: _infraplan_report_date(report)
            for entry_id, report in db.query(InfraplanEntry.id, InfraplanReport)
            .join(InfraplanReport, InfraplanReport.id == InfraplanEntry.report_id)
            .filter(InfraplanEntry.id.in_(entry_ids))
        }
    gvfg_ids = {o.gvfg_entry_id for o in observations if o.is_derived and o.gvfg_entry_id}
    gvfg: dict[int, date] = {}
    if gvfg_ids:
        gvfg = {
            entry_id: _gvfg_stand(program)
            for entry_id, program in db.query(GvfgEntry.id, GvfgProgram)
            .join(GvfgProgram, GvfgProgram.id == GvfgEntry.program_id)
            .filter(GvfgEntry.id.in_(gvfg_ids))
        }
    return ReportedOn(fulda=fulda, infraplan=infraplan, gvfg=gvfg)


class ExpectedSplit(NamedTuple):
    fulda: list[ExpectedDate]
    infraplan: list[ExpectedDate]
    manual: list[tuple[MainPhase, date]]
    gvfg: list[ExpectedDate]


def split_expected(
    observations: list[ProgressObservation], reported: ReportedOn
) -> ExpectedSplit:
    """Split dated expected MAIN observations into Fulda prognoses, Infraplan
    and GVFG commissioning years and manual entries.

    Derived claims carry the date of their report (``reported``, from
    :func:`expected_report_dates`) so the forecast can weigh them against
    VIB-PFA dates; hand-made entries (any source label) are editorial and
    always win.
    """

    split = ExpectedSplit([], [], [], [])
    for obs in observations:
        phase = _enum_or_none(MainPhase, obs.asserted_state)
        if phase is None or obs.observed_date is None:
            continue
        if obs.is_derived and obs.source_type == SourceType.FULDA_RUNDE.value:
            split.fulda.append(
                ExpectedDate(
                    phase=phase,
                    date=obs.observed_date,
                    reported_on=reported.fulda.get(obs.fulda_announcement_id),
                )
            )
        elif obs.is_derived and obs.source_type == SourceType.INFRAPLAN.value:
            split.infraplan.append(
                ExpectedDate(
                    phase=phase,
                    date=obs.observed_date,
                    reported_on=reported.infraplan.get(obs.infraplan_entry_id),
                )
            )
        elif obs.is_derived and obs.source_type == SourceType.GVFG.value:
            split.gvfg.append(
                ExpectedDate(
                    phase=phase,
                    date=obs.observed_date,
                    reported_on=reported.gvfg.get(obs.gvfg_entry_id),
                )
            )
        elif not obs.is_derived:
            split.manual.append((phase, obs.observed_date))
    return split


def derive_for_project(
    db: Session,
    project: Project,
    progress: ProjectProgress,
    today: date,
    *,
    persist_timestamp: bool = True,
    observations: list[ProgressObservation] | None = None,
    infraplan_relevance: dict[int, bool] | None = None,
) -> DerivationResult:
    """Run the pure derivation for one project and cache the computed values.

    ``persist_timestamp`` controls ``computed_at``, which doubles as the
    lazy-resync staleness marker: it is only bumped when a real derived-data
    resync happened, so cheap headline recomputes on every GET don't keep the
    cache perpetually "fresh" and starve the resync (see ``_ensure_fresh``).

    ``observations`` may pass pre-loaded non-expected observations and
    ``infraplan_relevance`` the pre-loaded PaBe relevance per project (both
    used by the batched superior aggregation); when None they are queried here.
    """

    # Expected (future) milestones never contribute to the current headline —
    # they only inform the forecast (see ``_build_forecast_for_project``).
    if observations is None:
        observations = (
            db.query(ProgressObservation)
            .filter(
                ProgressObservation.project_id == project.id,
                ProgressObservation.is_expected.is_(False),
            )
            .all()
        )
    result = derive_headline(
        _to_inputs(observations),
        has_pf=bool(progress.has_planfeststellung),
        parl_relevant=resolve_parl_relevant(
            progress,
            project,
            (
                infraplan_relevance
                if infraplan_relevance is not None
                else infraplan_parl_relevance(db, [project.id])
            ).get(project.id),
        ),
        lifecycle=_enum_or_none(LifecycleStatus, progress.lifecycle_status)
        or LifecycleStatus.AKTIV,
        manual_phase_override=_enum_or_none(MainPhase, progress.manual_phase_override),
        pf_state_override=_enum_or_none(ParallelState, progress.pf_state_override),
        parl_state_override=_enum_or_none(ParallelState, progress.parl_state_override),
        today=today,
    )
    # Cache the computed (not the override-effective) values for list views.
    progress.computed_phase = result.computed_phase.value
    progress.computed_confidence = result.computed_confidence
    if persist_timestamp:
        progress.computed_at = datetime.utcnow()
    return result


# --- Phase 2: materialisation of derived (VIB/FinVe) observations ------------


def sync_derived_observations(db: Session, project_id: int) -> int:
    """Delete and regenerate all ``is_derived=True`` observations for a project.

    Materialises observations from the currently linked VIB entries (status
    flags → MAIN, PFA → PF track) and FinVe records. Returns the number of
    derived rows written. Derived churn is intentionally **not** audited.
    """

    return sync_derived_observations_bulk(db, [project_id]).get(project_id, 0)


def sync_derived_observations_bulk(
    db: Session, project_ids: list[int]
) -> dict[int, int]:
    """Batched :func:`sync_derived_observations` for many projects at once.

    Loads each derived-observation source (VIB entries, assigned PFAs, FinVes,
    Bauportal, Medien, Fulda) with **one** query over all ``project_ids`` and
    groups in Python — the per-project materialisation rules are unchanged.
    Used by the superior aggregation so a stale subtree resyncs in a constant
    number of queries instead of ~10 per leaf. Returns ``{project_id: rows}``.
    """

    if not project_ids:
        return {}

    db.query(ProgressObservation).filter(
        ProgressObservation.project_id.in_(project_ids),
        ProgressObservation.is_derived.is_(True),
    ).delete(synchronize_session=False)

    specs_by_project: dict[int, list[DerivedSpec]] = {pid: [] for pid in project_ids}
    pf_evidence_projects: set[int] = set()

    # --- VIB entries linked to the projects (m:n) ---
    # Eager-load report + pfa_entries: both are touched per entry below and
    # would otherwise lazy-load with two extra queries per VIB entry.
    vib_rows = (
        db.query(VibEntry, vib_entry_project.c.project_id)
        .options(joinedload(VibEntry.report), selectinload(VibEntry.pfa_entries))
        .join(vib_entry_project, vib_entry_project.c.vib_entry_id == VibEntry.id)
        .filter(
            vib_entry_project.c.project_id.in_(project_ids),
            VibEntry.confirmed.is_(True),
        )
        .all()
    )
    for entry, project_id in vib_rows:
        report = entry.report
        # Use the authoritative report ``year`` (year-end), not ``report_date``:
        # the latter is freetext-parsed and observed to be unreliable
        # (e.g. 1993-12-31 stored on a 2023 report).
        observed = date(report.year, 12, 31) if report is not None else None
        # PFAs assigned to a (sub)project carry their own status on that
        # subproject (materialised by the assigned-PFA pass below). Here we only
        # render the PF track for the *unassigned* sections, and we suppress the
        # flattened entry-level MAIN once any section has been split out — the
        # parent then aggregates via its children's span.
        has_assigned_pfa = any(pfa.project_id is not None for pfa in entry.pfa_entries)
        pfas = [
            PfaInput(
                id=pfa.id,
                nr_pfa=pfa.nr_pfa,
                abschnitt_label=pfa.abschnitt_label,
                datum_pfb=pfa.datum_pfb,
                baubeginn=pfa.baubeginn,
                inbetriebnahme=pfa.inbetriebnahme,
            )
            for pfa in entry.pfa_entries
            if pfa.project_id is None
        ]
        if pfa_has_pf_evidence(pfas):
            pf_evidence_projects.add(project_id)
        specs_by_project[project_id].extend(
            vib_entry_to_specs(
                vib_entry_id=entry.id,
                status_planung=bool(entry.status_planung),
                status_bau=bool(entry.status_bau),
                status_abgeschlossen=bool(entry.status_abgeschlossen),
                observed_date=observed,
                has_planfeststellung_flag=False,
                pfas=pfas,
                emit_main=not has_assigned_pfa,
            )
        )

    # --- PFAs assigned directly to these projects (project as leaf subproject) ---
    # These belong to a VIB entry linked to the *parent*, so the m:n query above
    # does not reach them; query by the PFA→project assignment instead.
    # ``entry.report`` is read for every row below — eager-load it, otherwise
    # each assigned PFA costs one extra SELECT.
    assigned_pfa_rows = (
        db.query(VibPfaEntry, VibEntry)
        .join(VibEntry, VibEntry.id == VibPfaEntry.vib_entry_id)
        .options(joinedload(VibEntry.report))
        .filter(VibPfaEntry.project_id.in_(project_ids), VibEntry.confirmed.is_(True))
        .all()
    )
    for pfa, entry in assigned_pfa_rows:
        report = entry.report
        observed = date(report.year, 12, 31) if report is not None else None
        pfa_input = PfaInput(
            id=pfa.id,
            nr_pfa=pfa.nr_pfa,
            abschnitt_label=pfa.abschnitt_label,
            datum_pfb=pfa.datum_pfb,
            baubeginn=pfa.baubeginn,
            inbetriebnahme=pfa.inbetriebnahme,
        )
        if pfa_has_pf_evidence([pfa_input]):
            pf_evidence_projects.add(pfa.project_id)
        specs_by_project[pfa.project_id].extend(
            pfa_to_specs(
                pfa=pfa_input,
                vib_entry_id=entry.id,
                observed_fallback=observed,
            )
        )

    # --- FinVe records linked to the projects ---
    finve_rows = (
        db.query(Finve, FinveToProject.project_id)
        .join(FinveToProject, FinveToProject.finve_id == Finve.id)
        .filter(FinveToProject.project_id.in_(project_ids))
        .all()
    )
    seen_finve: set[tuple[int, int]] = set()
    for finve, project_id in finve_rows:
        if (project_id, finve.id) in seen_finve:
            continue  # a Sammel-FinVe can have several year-scoped links
        seen_finve.add((project_id, finve.id))
        finve_spec = finve_to_spec(
            finve_id=finve.id,
            is_sammel=bool(finve.is_sammel_finve),
            starting_year=finve.starting_year,
            name=finve.name,
            manual_phase=_enum_or_none(MainPhase, finve.progress_phase),
        )
        if finve_spec is not None:  # ambiguous Sammel-FinVe → skipped
            specs_by_project[project_id].append(finve_spec)

    # --- DB-Bauportal records confirm-matched to these projects ---
    bauportal_rows = (
        db.query(BauportalStatus)
        .filter(
            BauportalStatus.project_id.in_(project_ids),
            BauportalStatus.confirmed.is_(True),
        )
        .all()
    )
    for row in bauportal_rows:
        observed = row.fetched_at.date() if row.fetched_at is not None else None
        bauportal_spec = bauportal_to_spec(
            bauportal_status_id=row.id,
            status_raw=row.status_raw,
            projecttime_raw=row.projecttime_raw,
            observed_date=observed,
        )
        if bauportal_spec is not None:  # mixed/umbrella entry → no contribution
            specs_by_project[row.project_id].append(bauportal_spec)

    # --- Confirmed Medien/Presse reports matched to these projects ---
    media_rows = (
        db.query(MediaReport)
        .filter(
            MediaReport.project_id.in_(project_ids),
            MediaReport.confirmed.is_(True),
        )
        .all()
    )
    for row in media_rows:
        media_spec = media_to_spec(
            media_report_id=row.id,
            asserted_phase=row.asserted_phase,
            observed_date=row.observed_date or row.published_date,
            publication=row.publication,
            url=row.url,
            quote=row.quote,
        )
        if media_spec is not None:  # no valid phase yet → no contribution
            specs_by_project[row.project_id].append(media_spec)

    # --- Confirmed Fulda-Runde announcements matched to these projects ---
    fulda_rows = (
        db.query(FuldaAnnouncement, fulda_announcement_to_project.c.project_id)
        .join(
            fulda_announcement_to_project,
            fulda_announcement_to_project.c.fulda_announcement_id == FuldaAnnouncement.id,
        )
        .options(joinedload(FuldaAnnouncement.document))
        .filter(
            fulda_announcement_to_project.c.project_id.in_(project_ids),
            FuldaAnnouncement.confirmed.is_(True),
        )
        .all()
    )
    for row, project_id in fulda_rows:
        document = row.document
        fulda_spec = fulda_to_spec(
            fulda_announcement_id=row.id,
            category=row.category,
            document_date=document.document_date if document is not None else None,
            expected_date=row.expected_date,
            drucksache=document.drucksache if document is not None else None,
        )
        if fulda_spec is not None:  # hint-only category → no contribution
            specs_by_project[project_id].append(fulda_spec)

    # --- Infraplan entries linked to these projects (newest year per project) ---
    infraplan_evidence, infraplan_gvfg = _add_infraplan_specs(db, project_ids, specs_by_project)
    pf_evidence_projects |= infraplan_evidence

    # --- GVFG-Bundesprogramm: newest edition per Vorhaben linked to the projects ---
    _add_gvfg_specs(db, project_ids, specs_by_project, infraplan_gvfg)

    for project_id, specs in specs_by_project.items():
        for spec in specs:
            db.add(
                ProgressObservation(
                    project_id=project_id,
                    source_type=spec.source_type.value,
                    track=spec.track.value,
                    asserted_state=spec.asserted_state,
                    observed_date=spec.observed_date,
                    confidence=spec.confidence,
                    note=spec.note,
                    is_derived=True,
                    vib_entry_id=spec.vib_entry_id,
                    vib_pfa_entry_id=spec.vib_pfa_entry_id,
                    finve_id=spec.finve_id,
                    bauportal_status_id=spec.bauportal_status_id,
                    media_report_id=spec.media_report_id,
                    fulda_announcement_id=spec.fulda_announcement_id,
                    infraplan_entry_id=spec.infraplan_entry_id,
                    gvfg_entry_id=spec.gvfg_entry_id,
                    is_expected=spec.is_expected,
                )
            )

    # Auto-enable the PF lane when VIB documents a Planfeststellungsverfahren.
    if pf_evidence_projects:
        progress_rows = (
            db.query(ProjectProgress)
            .filter(ProjectProgress.project_id.in_(pf_evidence_projects))
            .all()
        )
        for progress in progress_rows:
            if not progress.has_planfeststellung:
                progress.has_planfeststellung = True

    db.flush()
    return {pid: len(specs) for pid, specs in specs_by_project.items()}


def _gvfg_stand_by_key(db: Session, keys: set[str]) -> dict[str, date]:
    """Stand of the newest GVFG edition per key (``stand``, else 1 Jan of its
    first year) — the rival of an Infraplan GVFG row (decision 22)."""

    if not keys:
        return {}
    newest: dict[str, date] = {}
    for key, stand, year_from in (
        db.query(GvfgEntry.key, GvfgProgram.stand, GvfgProgram.year_from)
        .join(GvfgProgram, GvfgProgram.id == GvfgEntry.program_id)
        .filter(GvfgEntry.key.in_(keys))
    ):
        when = stand or date(year_from, 1, 1)
        if key not in newest or when > newest[key]:
            newest[key] = when
    return newest


def _add_infraplan_specs(
    db: Session, project_ids: list[int], specs_by_project: dict[int, list[DerivedSpec]]
) -> tuple[set[int], set[tuple[int, str]]]:
    """Infraplan rows linked to the projects; only each project's newest year
    counts. A GVFG row yields phase and date only when the Infraplan is at
    least as recent as the newest GVFG edition with the same key. Returns the
    projects with ``durchgängiges Baurecht`` (Planfeststellung evidence) and
    the (project, GVFG key) pairs whose Infraplan row won that comparison —
    the GVFG edition then stays out (:func:`_add_gvfg_specs`)."""

    rows = (
        db.query(InfraplanEntry, InfraplanReport, InfraplanEntryProject.project_id)
        .join(InfraplanEntryProject, InfraplanEntryProject.entry_id == InfraplanEntry.id)
        .join(InfraplanReport, InfraplanReport.id == InfraplanEntry.report_id)
        .filter(InfraplanEntryProject.project_id.in_(project_ids))
        .all()
    )
    pf_evidence: set[int] = set()
    gvfg_won: set[tuple[int, str]] = set()
    if not rows:
        return pf_evidence, gvfg_won
    newest_year: dict[int, int] = {}
    for _entry, report, project_id in rows:
        newest_year[project_id] = max(newest_year.get(project_id, report.year), report.year)
    gvfg_keys = {
        key
        for entry, _report, _pid in rows
        if entry.section.startswith("GVFG") and (key := normalize_key(entry.primary_number))
    }
    gvfg_stand = _gvfg_stand_by_key(db, gvfg_keys)
    for entry, report, project_id in rows:
        if report.year != newest_year[project_id]:
            continue
        published = _infraplan_report_date(report)
        include = True
        if entry.section.startswith("GVFG"):
            key = normalize_key(entry.primary_number) or ""
            rival = gvfg_stand.get(key)
            include = rival is None or published >= rival
            if include and key:
                gvfg_won.add((project_id, key))
        specs_by_project[project_id].extend(
            infraplan_entry_to_specs(
                infraplan_entry_id=entry.id,
                section=entry.section,
                report_year=report.year,
                observed_date=published,
                lph_from=entry.lph_from,
                lph_to=entry.lph_to,
                under_construction=bool(entry.under_construction),
                baurecht=bool(entry.baurecht),
                ibn_year=entry.ibn_year,
                ibn_qualifier=entry.ibn_qualifier,
                parl_state=entry.parl_state,
                state_raw=entry.state_raw,
                include_phase_and_date=include,
            )
        )
        if include and entry.baurecht:
            pf_evidence.add(project_id)
    return pf_evidence, gvfg_won


def _add_gvfg_specs(
    db: Session,
    project_ids: list[int],
    specs_by_project: dict[int, list[DerivedSpec]],
    infraplan_won: set[tuple[int, str]],
) -> None:
    """GVFG Vorhaben linked to the projects, each from the newest edition that
    lists its key for the project. Skipped where the project's Infraplan row
    with the same key is at least as recent (decision 22: the more recent
    source wins, the Infraplan on a tie)."""

    rows = (
        db.query(GvfgEntry, GvfgProgram, gvfg_entry_project.c.project_id)
        .join(gvfg_entry_project, gvfg_entry_project.c.entry_id == GvfgEntry.id)
        .join(GvfgProgram, GvfgProgram.id == GvfgEntry.program_id)
        .filter(gvfg_entry_project.c.project_id.in_(project_ids))
        .all()
    )
    newest: dict[tuple[int, str], tuple[GvfgEntry, GvfgProgram]] = {}
    for entry, program, project_id in rows:
        current = newest.get((project_id, entry.key))
        if current is None or program.year_from > current[1].year_from:
            newest[(project_id, entry.key)] = (entry, program)
    for (project_id, key), (entry, program) in newest.items():
        if (project_id, key) in infraplan_won:
            continue
        specs_by_project[project_id].extend(
            gvfg_entry_to_specs(
                gvfg_entry_id=entry.id,
                edition=f"{program.year_from}–{program.year_to}",
                stand=_gvfg_stand(program),
                lph=entry.lph,
                construction_start=entry.construction_start,
                commissioning_planned=entry.commissioning_planned,
                commissioning_actual=entry.commissioning_actual,
            )
        )


def _ensure_fresh(
    db: Session,
    project: Project,
    progress: ProjectProgress,
    today: date,
    *,
    force: bool = False,
) -> DerivationResult:
    """Lazy resync: re-materialise derived observations only when the cache is
    stale (``computed_at`` older than ``STALENESS_WINDOW``) or ``force``."""

    stale = (
        force
        or progress.computed_at is None
        or (datetime.utcnow() - progress.computed_at) > STALENESS_WINDOW
    )
    if stale:
        sync_derived_observations(db, project.id)
    return derive_for_project(db, project, progress, today, persist_timestamp=stale)


def _build_forecast_for_project(
    db: Session,
    project_id: int,
    effective_phase: MainPhase,
    today: date,
    skipped_phases: set[MainPhase] | None = None,
) -> dict:
    """Gather forecast inputs (PFA dates, BVWP durations, Fulda announcements)
    and run the pure forecast. Returns a dict matching ProgressForecastSchema."""

    # PFA milestone dates from linked VIB entries.
    pfa_rows = (
        db.query(VibPfaEntry, VibReport)
        .join(VibEntry, VibEntry.id == VibPfaEntry.vib_entry_id)
        .outerjoin(VibReport, VibReport.id == VibEntry.vib_report_id)
        .join(vib_entry_project, vib_entry_project.c.vib_entry_id == VibEntry.id)
        .filter(vib_entry_project.c.project_id == project_id, VibEntry.confirmed.is_(True))
        .all()
    )
    pfas = [pfa_forecast_input(p, report) for p, report in pfa_rows]

    bvwp_row = (
        db.query(BvwpProjectData)
        .filter(BvwpProjectData.project_id == project_id)
        .first()
    )
    bvwp = None
    if bvwp_row is not None:
        bvwp = BvwpDurations(
            outstanding_planning=bvwp_row.bvwp_duration_of_outstanding_planning,
            build=bvwp_row.bvwp_duration_of_build,
            operating=bvwp_row.bvwp_duration_operating,
        )

    # Expected MAIN observations with a date: Fulda-Runde prognoses and Infraplan
    # commissioning years (derived) compete with VIB-PFA by weight; manual ones
    # are editorial and always win.
    expected_obs = (
        db.query(ProgressObservation)
        .filter(
            ProgressObservation.project_id == project_id,
            ProgressObservation.is_expected.is_(True),
            ProgressObservation.track == ObservationTrack.MAIN.value,
            ProgressObservation.observed_date.isnot(None),
        )
        .all()
    )
    split = split_expected(expected_obs, expected_report_dates(db, expected_obs))

    result = build_forecast(
        effective_phase=effective_phase,
        today=today,
        pfas=pfas,
        bvwp=bvwp,
        fulda=split.fulda,
        infraplan=split.infraplan,
        gvfg=split.gvfg,
        manual_expected=split.manual,
        skipped_phases=skipped_phases or set(),
    )
    return {
        "current_phase": result.current_phase.value,
        "remaining_text": result.remaining_text,
        "estimated_phase_end": result.estimated_phase_end,
        "next_steps": [
            {
                "phase": step.phase.value,
                "expected_date": step.expected_date,
                "source": step.source,
            }
            for step in result.next_steps
        ],
        "has_data": result.has_data,
        "ibn_doubt": _gvfg_ibn_doubt(db, project_id, effective_phase, split.infraplan),
    }


def _gvfg_ibn_doubt(
    db: Session, project_id: int, effective_phase: MainPhase, infraplan: list[ExpectedDate]
) -> dict | None:
    """Question the known commissioning year when the newest GVFG edition still
    funds the project (with its direct subprojects) after it. The year comes
    from the GVFG edition or the Infraplan, whichever is more recent
    (``known_ibn``); see ``services/gvfg_ibn_check.py``."""
    if effective_phase is MainPhase.IN_BETRIEB:
        return None
    entries = gvfg_crud.project_entries(db, project_id, with_subprojects=True)
    if not entries:
        return None
    program = entries[0].program  # newest edition first
    entries = [e for e in entries if e.program_id == program.id and e.part == "finanzrelevant"]
    if not entries:
        return None
    edition = f"{program.year_from}–{program.year_to}"

    # Same year as the forecast reads from the edition (tats., else gepl.).
    planned = [
        year
        for e in entries
        if (year := gvfg_ibn_year(e.commissioning_planned, e.commissioning_actual))
    ]
    gvfg = (_gvfg_stand(program), max(planned), edition) if planned else None
    claims = [c for c in infraplan if c.phase is MainPhase.IN_BETRIEB]
    infraplan_ibn = None
    if claims:
        published = max((c.reported_on for c in claims if c.reported_on), default=date.min)
        infraplan_ibn = (published, max(c.date for c in claims).year)
    ibn = known_ibn(gvfg, infraplan_ibn)
    if ibn is None:
        return None
    ibn_year, ibn_source = ibn

    amounts: dict[str, Decimal] = {}
    for entry in entries:
        line = next((a for a in entry.amounts if a.category == "SUM"), None)
        for label, value in ((line.periods or {}) if line else {}).items():
            if value is not None:
                amounts[label] = amounts.get(label, Decimal(0)) + Decimal(str(value))

    doubt = check_ibn_against_gvfg(ibn_year, ibn_source, edition, program.periods or [], amounts)
    if doubt is None:
        return None
    return {
        "ibn_year": doubt.ibn_year,
        "ibn_source": doubt.ibn_source,
        "edition": doubt.edition,
        "program_id": program.id,
        "entry_ids": [e.id for e in entries],
        "aid_after": float(doubt.aid_after),
        "aid_total": float(doubt.aid_total),
        "periods": [{"label": label, "aid": float(aid)} for label, aid in doubt.periods],
    }


# --- Read --------------------------------------------------------------------


def _load_subtree(db: Session, root_id: int) -> dict[int, list[Project]]:
    """Load all descendants of ``root_id`` with one IN-query per depth level.

    Returns ``{parent_id: [children]}``; project_groups are eager-loaded because
    the leaf derivation reads them (``resolve_parl_relevant``).
    """
    children_by_parent: dict[int, list[Project]] = {}
    frontier = [root_id]
    while frontier:
        rows = (
            db.query(Project)
            .options(selectinload(Project.project_groups))
            .filter(Project.superior_project_id.in_(frontier))
            .all()
        )
        frontier = []
        for child in rows:
            children_by_parent.setdefault(child.superior_project_id, []).append(child)
            frontier.append(child.id)
    return children_by_parent


def _bulk_get_or_create_progress(
    db: Session, project_ids: list[int]
) -> dict[int, ProjectProgress]:
    """Fetch ProjectProgress rows for all ids in one query; create missing rows
    in a single flush (no per-row commit)."""
    rows = (
        db.query(ProjectProgress)
        .filter(ProjectProgress.project_id.in_(project_ids))
        .all()
    )
    by_id = {row.project_id: row for row in rows}
    missing = [pid for pid in project_ids if pid not in by_id]
    for pid in missing:
        row = ProjectProgress(
            project_id=pid,
            lifecycle_status=LifecycleStatus.AKTIV.value,
        )
        db.add(row)
        by_id[pid] = row
    if missing:
        db.flush()
    return by_id


def _build_aggregation_node(db: Session, project: Project, today: date) -> AggregationNode:
    """Build a planning-state aggregation node for ``project`` and (recursively)
    all of its subprojects, so a superior at any depth spans its leaf descendants.

    Leaves carry their own derived phase; intermediate nodes carry a manual phase
    override (which pins the whole subtree) but never their own observations — the
    state lives at the leaves. See ``aggregate_tree`` for the aggregation rule.

    Batched (#89): the subtree, the ProjectProgress rows, the stale-leaf resync
    and the leaf observations are each loaded in a constant number of queries,
    so the query count is sublinear in the number of subprojects.
    """

    children_by_parent = _load_subtree(db, project.id)
    projects_by_id: dict[int, Project] = {project.id: project}
    for children in children_by_parent.values():
        for child in children:
            projects_by_id[child.id] = child

    progress_by_id = _bulk_get_or_create_progress(db, list(projects_by_id))

    leaf_ids = [pid for pid in projects_by_id if pid not in children_by_parent]

    # Stale leaves resync in one batched pass (same staleness rule as
    # ``_ensure_fresh``); their ``computed_at`` is bumped by the derivation.
    now = datetime.utcnow()
    stale_leaf_ids = {
        pid
        for pid in leaf_ids
        if progress_by_id[pid].computed_at is None
        or (now - progress_by_id[pid].computed_at) > STALENESS_WINDOW
    }
    if stale_leaf_ids:
        sync_derived_observations_bulk(db, list(stale_leaf_ids))

    # One query for all leaves' non-expected observations.
    obs_by_project: dict[int, list[ProgressObservation]] = {pid: [] for pid in leaf_ids}
    if leaf_ids:
        for obs in (
            db.query(ProgressObservation)
            .filter(
                ProgressObservation.project_id.in_(leaf_ids),
                ProgressObservation.is_expected.is_(False),
            )
            .all()
        ):
            obs_by_project[obs.project_id].append(obs)
    leaf_relevance = infraplan_parl_relevance(db, leaf_ids)

    def build(node_project: Project) -> AggregationNode:
        progress = progress_by_id[node_project.id]
        lifecycle = (
            _enum_or_none(LifecycleStatus, progress.lifecycle_status)
            or LifecycleStatus.AKTIV
        )
        children = children_by_parent.get(node_project.id, [])

        if not children:
            result = derive_for_project(
                db,
                node_project,
                progress,
                today,
                persist_timestamp=node_project.id in stale_leaf_ids,
                observations=obs_by_project.get(node_project.id, []),
                infraplan_relevance=leaf_relevance,
            )
            return AggregationNode(
                leaf_phase=result.effective_phase,
                leaf_is_known=result.is_known,
                project_id=node_project.id,
                name=node_project.name,
                lifecycle=lifecycle,
            )

        return AggregationNode(
            leaf_phase=MainPhase.NICHT_GESTARTET,  # unused for intermediate nodes
            leaf_is_known=False,
            manual_override=_enum_or_none(MainPhase, progress.manual_phase_override),
            children=[build(child) for child in children],
            project_id=node_project.id,
            name=node_project.name,
            lifecycle=lifecycle,
        )

    return build(project)


def get_progress_view(db: Session, project_id: int, today: date | None = None) -> dict | None:
    """Assemble the full progress view payload (dict matching ProjectProgressSchema).

    Returns ``None`` if the project does not exist.
    """

    today = today or date.today()
    # project_groups is read by resolve_parl_relevant() below — eager-load it
    # instead of paying a lazy SELECT on the way out.
    project = (
        db.query(Project)
        .options(selectinload(Project.project_groups))
        .filter(Project.id == project_id)
        .first()
    )
    if project is None:
        return None

    progress = get_or_create_progress(db, project_id)
    result = _ensure_fresh(db, project, progress, today)
    db.commit()

    observations = (
        db.query(ProgressObservation)
        .filter(ProgressObservation.project_id == project_id)
        .order_by(ProgressObservation.observed_date.desc().nullslast(), ProgressObservation.id.desc())
        .all()
    )

    pf_documents = _track_documents(db, project_id, ObservationTrack.PF)
    parl_documents = _track_documents(db, project_id, ObservationTrack.PARL)

    # Superior aggregation — recursive over the whole subtree so a superior at any
    # depth spans its leaf descendants (not a mid-level node's stale summary).
    is_superior = (
        db.query(Project.id)
        .filter(Project.superior_project_id == project_id)
        .first()
        is not None
    )
    child_payloads: list[dict] = []
    span_min = span_max = None
    effective_phase = result.effective_phase
    is_known = result.is_known
    if is_superior:
        root_node = _build_aggregation_node(db, project, today)
        db.commit()
        root_agg = aggregate_tree(root_node)
        # A manual override on the superior itself pins the whole project; otherwise
        # the headline is the aggregated span and "known" follows the leaves.
        if root_node.manual_override is None:
            effective_phase = root_agg.display_phase
            is_known = root_agg.is_known
            if root_agg.span is not None:
                span_min, span_max = root_agg.span[0].value, root_agg.span[1].value
        for child_node in root_node.children:
            child_agg = aggregate_tree(child_node)
            child_payloads.append(
                {
                    "project_id": child_node.project_id,
                    "name": child_node.name,
                    "effective_phase": child_agg.display_phase.value,
                    "lifecycle_status": child_node.lifecycle.value,
                    "is_known": child_agg.is_known,
                    "is_superior": child_agg.is_superior,
                    "span_min_phase": child_agg.span[0].value if child_agg.span else None,
                    "span_max_phase": child_agg.span[1].value if child_agg.span else None,
                }
            )

    skipped_phases = resolve_skipped_phases(project)
    forecast = _build_forecast_for_project(
        db, project_id, result.effective_phase, today, skipped_phases
    )
    in_use = {effective_phase}
    for value in (
        span_min,
        span_max,
        *(c[k] for c in child_payloads for k in ("effective_phase", "span_min_phase", "span_max_phase")),
        *(step["phase"] for step in forecast["next_steps"]),
    ):
        phase = _enum_or_none(MainPhase, value)
        if phase is not None:
            in_use.add(phase)

    return {
        "project_id": project_id,
        "effective_phase": effective_phase.value,
        "computed_phase": result.computed_phase.value,
        "computed_confidence": result.computed_confidence,
        "is_known": is_known,
        "is_overridden": result.is_overridden,
        "manual_override_note": progress.manual_override_note,
        "computed_at": progress.computed_at,
        "has_planfeststellung": bool(progress.has_planfeststellung),
        "parl_befassung_relevant": resolve_parl_relevant(
            progress, project, infraplan_parl_relevance(db, [project.id]).get(project.id)
        ),
        "parl_befassung_relevant_override": progress.parl_befassung_relevant,
        "lifecycle_status": result.lifecycle.value,
        "pf_state": result.pf_state.value if result.pf_state else None,
        "parl_state": result.parl_state.value if result.parl_state else None,
        "pf_state_override": progress.pf_state_override,
        "parl_state_override": progress.parl_state_override,
        "parl_befassung_text": progress.parl_befassung_text,
        "parl_drucksache_url": progress.parl_drucksache_url,
        "parl_befassung_date": progress.parl_befassung_date,
        "pf_text": progress.pf_text,
        "pf_date": progress.pf_date,
        "pf_links": progress.pf_links or [],
        "observations": observations,
        "contributions": [
            {
                "observation_id": c.id,
                "source_type": c.source_type.value,
                "track": c.track.value,
                "asserted_state": c.asserted_state,
                "observed_date": c.observed_date,
                "effective_confidence": c.effective_confidence,
                "was_decisive": c.was_decisive,
            }
            for c in result.contributions
        ],
        "pf_documents": pf_documents,
        "parl_documents": parl_documents,
        "is_superior": is_superior,
        "span_min_phase": span_min,
        "span_max_phase": span_max,
        "children": child_payloads,
        "hidden_phases": resolve_hidden_phases(skipped_phases, in_use),
        "forecast": forecast,
    }


def _track_documents(db: Session, project_id: int, track: ObservationTrack) -> list[dict]:
    rows = (
        db.query(ProgressTrackDocument, Document)
        .join(Document, Document.id == ProgressTrackDocument.document_id)
        .filter(
            ProgressTrackDocument.project_id == project_id,
            ProgressTrackDocument.track == track.value,
        )
        .all()
    )
    return [
        {"id": link.id, "track": link.track, "document": document}
        for link, document in rows
    ]


# --- Mutations ---------------------------------------------------------------


def update_progress(
    db: Session, project_id: int, payload: dict, user: User | None
) -> ProjectProgress | None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return None
    progress = get_or_create_progress(db, project_id)
    before = _snapshot(progress)

    simple_fields = {
        "has_planfeststellung",
        "parl_befassung_relevant",
        "lifecycle_status",
        "manual_phase_override",
        "manual_override_note",
        "pf_state_override",
        "parl_state_override",
        "parl_befassung_text",
        "parl_drucksache_url",
        "parl_befassung_date",
        "pf_text",
        "pf_date",
        "pf_links",
    }
    for key, value in payload.items():
        if key in simple_fields:
            setattr(progress, key, value)

    # Explicit clears (None is otherwise ambiguous with "not provided").
    if payload.get("clear_phase_override"):
        progress.manual_phase_override = None
        progress.manual_override_note = None
    if payload.get("clear_parl_relevant"):
        progress.parl_befassung_relevant = None
    if payload.get("clear_parl_state_override"):
        progress.parl_state_override = None
    if payload.get("clear_pf_state_override"):
        progress.pf_state_override = None

    # Setting any Planfeststellung signal (state or editorial detail) implies the
    # track is relevant — otherwise the data would be silently ignored by the
    # derivation. The explicit toggle still wins if the caller sets it in the same
    # request (handled above via simple_fields).
    pf_signal = any(
        payload.get(k) not in (None, "")
        for k in ("pf_state_override", "pf_text", "pf_date")
    ) or bool(payload.get("pf_links"))
    if pf_signal and "has_planfeststellung" not in payload:
        progress.has_planfeststellung = True

    _log_progress_change(db, project_id, user, "PATCH", _snapshot_diff(before, _snapshot(progress)))
    db.commit()
    db.refresh(progress)
    return progress


def create_observation(
    db: Session,
    project_id: int,
    data: dict,
    user: User | None,
) -> ProgressObservation | None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return None
    progress = get_or_create_progress(db, project_id)
    before = _snapshot(progress)

    observation = ProgressObservation(
        project_id=project_id,
        source_type=data.get("source_type", SourceType.MANUELL.value),
        track=data["track"],
        asserted_state=data["asserted_state"],
        observed_date=data.get("observed_date"),
        confidence=data.get("confidence"),
        note=data.get("note"),
        is_derived=False,
        is_expected=bool(data.get("is_expected", False)),
        created_by_user_id=user.id if user else None,
        username_snapshot=user.username if user else None,
    )
    db.add(observation)

    # Adding a manual observation on a parallel track implies the track is
    # relevant — otherwise the derivation would silently ignore it (it gates the
    # PF/parl state behind these flags). Mirrors the VIB auto-enable in
    # sync_derived_observations, so users don't have to toggle a second control.
    if data["track"] == ObservationTrack.PF.value:
        progress.has_planfeststellung = True
    elif data["track"] == ObservationTrack.PARL.value and progress.parl_befassung_relevant is None:
        progress.parl_befassung_relevant = True

    db.flush()  # assigns the id shown in the change log
    _log_progress_change(
        db,
        project_id,
        user,
        "CREATE",
        [("observation", None, observation_summary(observation))]
        + _snapshot_diff(before, _snapshot(progress)),
    )
    db.commit()
    db.refresh(observation)
    return observation


def delete_observation(
    db: Session, project_id: int, observation_id: int, user: User | None
) -> bool | None:
    """Delete a manual observation.

    Returns ``True`` on success, ``None`` if not found, and raises
    :class:`DerivedObservationDeleteError` for ``is_derived=True`` rows (these
    are regenerated by the importers and must never be hand-deleted).
    """

    observation = (
        db.query(ProgressObservation)
        .filter(
            ProgressObservation.id == observation_id,
            ProgressObservation.project_id == project_id,
        )
        .first()
    )
    if observation is None:
        return None
    if observation.is_derived:
        raise DerivedObservationDeleteError(
            "Derived observations are materialised from imports and cannot be deleted manually."
        )
    _log_progress_change(
        db, project_id, user, "DELETE", [("observation", observation_summary(observation), None)]
    )
    db.delete(observation)
    db.commit()
    return True


def _document_label(document: Document | None, document_id: int) -> str:
    return f"#{document_id} {document.title}" if document is not None else f"#{document_id}"


def link_track_document(
    db: Session, project_id: int, track: str, document_id: int, user: User | None
) -> ProgressTrackDocument | None:
    """Link a document behind the PF / PARL track. Returns None if project or
    document is missing; returns the existing link if already present."""

    project = db.query(Project).filter(Project.id == project_id).first()
    document = db.query(Document).filter(Document.id == document_id).first()
    if project is None or document is None:
        return None

    existing = (
        db.query(ProgressTrackDocument)
        .filter(
            ProgressTrackDocument.project_id == project_id,
            ProgressTrackDocument.track == track,
            ProgressTrackDocument.document_id == document_id,
        )
        .first()
    )
    if existing is not None:
        return existing

    link = ProgressTrackDocument(
        project_id=project_id, track=track, document_id=document_id
    )
    db.add(link)
    _log_progress_change(
        db,
        project_id,
        user,
        "CREATE",
        [(f"{track.lower()}_document", None, _document_label(document, document_id))],
    )
    db.commit()
    db.refresh(link)
    return link


def unlink_track_document(
    db: Session, project_id: int, track: str, document_id: int, user: User | None
) -> bool:
    link = (
        db.query(ProgressTrackDocument)
        .filter(
            ProgressTrackDocument.project_id == project_id,
            ProgressTrackDocument.track == track,
            ProgressTrackDocument.document_id == document_id,
        )
        .first()
    )
    if link is None:
        return False
    document = db.query(Document).filter(Document.id == document_id).first()
    _log_progress_change(
        db,
        project_id,
        user,
        "DELETE",
        [(f"{track.lower()}_document", _document_label(document, document_id), None)],
    )
    db.delete(link)
    db.commit()
    return True


def recompute_progress(db: Session, project_id: int, today: date | None = None) -> bool:
    """Force a recomputation of the cached headline.

    Phase 1: recomputes from manual observations + flags. Phase 2 will first
    call ``sync_derived_observations`` here.
    """

    today = today or date.today()
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return False
    progress = get_or_create_progress(db, project_id)
    _ensure_fresh(db, project, progress, today, force=True)
    db.commit()
    return True
