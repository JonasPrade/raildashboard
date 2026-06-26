"""DB access for the project-progress feature.

Phase 1 derives the headline from **manual** observations + flags + lifecycle
and caches the result on the ``project_progress`` row. The derivation itself is
delegated to the pure ``services.progress_derivation`` module. Phase 2 will add
``sync_derived_observations`` (materialise VIB/FinVe rows) and a real lazy
resync; the seams (``STALENESS_WINDOW``, ``is_derived`` guard) already exist.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from dashboard_backend.models.associations.progress_track_document import (
    ProgressTrackDocument,
)
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
from dashboard_backend.services.progress_dates import parse_flexible_date
from dashboard_backend.services.progress_forecast import (
    BvwpDurations,
    PfaForecastInput,
    build_forecast,
)
from dashboard_backend.services.progress_materialization import (
    DerivedSpec,
    PfaInput,
    finve_to_spec,
    pfa_has_pf_evidence,
    pfa_to_specs,
    vib_entry_to_specs,
)
from dashboard_backend.models.projects.bvwp_project_data import BvwpProjectData
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry

# A project whose group membership includes a "BSWAG*" group (Bedarfsplan
# Schiene / BSWAG) defaults to parliamentary relevance. The nullable
# ``parl_befassung_relevant`` override stays authoritative when set.
BEDARFSPLAN_GROUP_SHORT_NAME_PREFIX = "BSWAG"


class DerivedObservationDeleteError(Exception):
    """Raised when a caller tries to delete a derived (materialised) observation."""


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


def resolve_parl_relevant(progress: ProjectProgress, project: Project) -> bool:
    """Override wins; otherwise default on for BSWAG* group membership."""

    if progress.parl_befassung_relevant is not None:
        return progress.parl_befassung_relevant
    return any(
        (g.short_name or "").upper().startswith(BEDARFSPLAN_GROUP_SHORT_NAME_PREFIX)
        for g in project.project_groups
    )


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


def _phase_date_pairs(
    observations: list[ProgressObservation],
) -> list[tuple[MainPhase, date]]:
    pairs: list[tuple[MainPhase, date]] = []
    for obs in observations:
        phase = _enum_or_none(MainPhase, obs.asserted_state)
        if phase is not None:
            pairs.append((phase, obs.observed_date))
    return pairs


def derive_for_project(
    db: Session,
    project: Project,
    progress: ProjectProgress,
    today: date,
    *,
    persist_timestamp: bool = True,
) -> DerivationResult:
    """Run the pure derivation for one project and cache the computed values.

    ``persist_timestamp`` controls ``computed_at``, which doubles as the
    lazy-resync staleness marker: it is only bumped when a real derived-data
    resync happened, so cheap headline recomputes on every GET don't keep the
    cache perpetually "fresh" and starve the resync (see ``_ensure_fresh``).
    """

    # Expected (future) milestones never contribute to the current headline —
    # they only inform the forecast (see ``_build_forecast_for_project``).
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
        parl_relevant=resolve_parl_relevant(progress, project),
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

    db.query(ProgressObservation).filter(
        ProgressObservation.project_id == project_id,
        ProgressObservation.is_derived.is_(True),
    ).delete(synchronize_session=False)

    specs: list[DerivedSpec] = []
    any_pf_evidence = False

    # --- VIB entries linked to the project (m:n) ---
    vib_entries = (
        db.query(VibEntry)
        .join(vib_entry_project, vib_entry_project.c.vib_entry_id == VibEntry.id)
        .filter(vib_entry_project.c.project_id == project_id)
        .all()
    )
    for entry in vib_entries:
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
            any_pf_evidence = True
        specs.extend(
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

    # --- PFAs assigned directly to this project (project as leaf subproject) ---
    # These belong to a VIB entry linked to the *parent*, so the m:n query above
    # does not reach them; query by the PFA→project assignment instead.
    assigned_pfa_rows = (
        db.query(VibPfaEntry, VibEntry)
        .join(VibEntry, VibEntry.id == VibPfaEntry.vib_entry_id)
        .filter(VibPfaEntry.project_id == project_id)
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
            any_pf_evidence = True
        specs.extend(
            pfa_to_specs(
                pfa=pfa_input,
                vib_entry_id=entry.id,
                observed_fallback=observed,
            )
        )

    # --- FinVe records linked to the project ---
    finve_rows = (
        db.query(Finve, FinveToProject.haushalt_year)
        .join(FinveToProject, FinveToProject.finve_id == Finve.id)
        .filter(FinveToProject.project_id == project_id)
        .all()
    )
    seen_finve: set[int] = set()
    for finve, _year in finve_rows:
        if finve.id in seen_finve:
            continue  # a Sammel-FinVe can have several year-scoped links
        seen_finve.add(finve.id)
        finve_spec = finve_to_spec(
            finve_id=finve.id,
            is_sammel=bool(finve.is_sammel_finve),
            starting_year=finve.starting_year,
            name=finve.name,
            manual_phase=_enum_or_none(MainPhase, finve.progress_phase),
        )
        if finve_spec is not None:  # ambiguous Sammel-FinVe → skipped
            specs.append(finve_spec)

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
            )
        )

    # Auto-enable the PF lane when VIB documents a Planfeststellungsverfahren.
    if any_pf_evidence:
        progress = (
            db.query(ProjectProgress)
            .filter(ProjectProgress.project_id == project_id)
            .first()
        )
        if progress is not None and not progress.has_planfeststellung:
            progress.has_planfeststellung = True

    db.flush()
    return len(specs)


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
    db: Session, project_id: int, effective_phase: MainPhase, today: date
) -> dict:
    """Gather forecast inputs (PFA dates, BVWP durations, Fulda announcements)
    and run the pure forecast. Returns a dict matching ProgressForecastSchema."""

    # PFA milestone dates from linked VIB entries.
    pfa_rows = (
        db.query(VibPfaEntry)
        .join(VibEntry, VibEntry.id == VibPfaEntry.vib_entry_id)
        .join(vib_entry_project, vib_entry_project.c.vib_entry_id == VibEntry.id)
        .filter(vib_entry_project.c.project_id == project_id)
        .all()
    )
    pfas = [
        PfaForecastInput(
            datum_pfb=parse_flexible_date(p.datum_pfb),
            baubeginn=parse_flexible_date(p.baubeginn),
            inbetriebnahme=parse_flexible_date(p.inbetriebnahme),
        )
        for p in pfa_rows
    ]

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

    # Fulda-Runde announcements: manual MAIN observations with a date.
    fulda_obs = (
        db.query(ProgressObservation)
        .filter(
            ProgressObservation.project_id == project_id,
            ProgressObservation.source_type == SourceType.FULDA_RUNDE.value,
            ProgressObservation.track == ObservationTrack.MAIN.value,
            ProgressObservation.observed_date.isnot(None),
        )
        .all()
    )
    fulda = _phase_date_pairs(fulda_obs)

    # Manual expected milestones (is_expected=True): editorial future dates that
    # override all derived sources in the forecast.
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
    manual_expected = _phase_date_pairs(expected_obs)

    result = build_forecast(
        effective_phase=effective_phase,
        today=today,
        pfas=pfas,
        bvwp=bvwp,
        fulda=fulda,
        manual_expected=manual_expected,
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
    }


# --- Read --------------------------------------------------------------------


def _build_aggregation_node(db: Session, project: Project, today: date) -> AggregationNode:
    """Build a planning-state aggregation node for ``project`` and (recursively)
    all of its subprojects, so a superior at any depth spans its leaf descendants.

    Leaves carry their own derived phase; intermediate nodes carry a manual phase
    override (which pins the whole subtree) but never their own observations — the
    state lives at the leaves. See ``aggregate_tree`` for the aggregation rule.
    """

    children = (
        db.query(Project).filter(Project.superior_project_id == project.id).all()
    )
    progress = get_or_create_progress(db, project.id)
    lifecycle = (
        _enum_or_none(LifecycleStatus, progress.lifecycle_status) or LifecycleStatus.AKTIV
    )

    if not children:
        result = _ensure_fresh(db, project, progress, today)
        return AggregationNode(
            leaf_phase=result.effective_phase,
            leaf_is_known=result.is_known,
            project_id=project.id,
            name=project.name,
            lifecycle=lifecycle,
        )

    return AggregationNode(
        leaf_phase=MainPhase.NICHT_GESTARTET,  # unused for intermediate nodes
        leaf_is_known=False,
        manual_override=_enum_or_none(MainPhase, progress.manual_phase_override),
        children=[_build_aggregation_node(db, child, today) for child in children],
        project_id=project.id,
        name=project.name,
        lifecycle=lifecycle,
    )


def get_progress_view(db: Session, project_id: int, today: date | None = None) -> dict | None:
    """Assemble the full progress view payload (dict matching ProjectProgressSchema).

    Returns ``None`` if the project does not exist.
    """

    today = today or date.today()
    project = db.query(Project).filter(Project.id == project_id).first()
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
        "parl_befassung_relevant": resolve_parl_relevant(progress, project),
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
        "forecast": _build_forecast_for_project(
            db, project_id, result.effective_phase, today
        ),
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


def update_progress(db: Session, project_id: int, payload: dict) -> ProjectProgress | None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return None
    progress = get_or_create_progress(db, project_id)

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

    db.commit()
    db.refresh(observation)
    return observation


def delete_observation(db: Session, project_id: int, observation_id: int) -> bool | None:
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
    db.delete(observation)
    db.commit()
    return True


def link_track_document(
    db: Session, project_id: int, track: str, document_id: int
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
    db.commit()
    db.refresh(link)
    return link


def unlink_track_document(
    db: Session, project_id: int, track: str, document_id: int
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
