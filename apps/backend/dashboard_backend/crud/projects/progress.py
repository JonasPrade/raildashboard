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
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.users import User
from dashboard_backend.services.progress_derivation import (
    DerivationResult,
    ObservationInput,
    aggregate_span,
    derive_headline,
)

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


def derive_for_project(
    db: Session,
    project: Project,
    progress: ProjectProgress,
    today: date,
) -> DerivationResult:
    """Run the pure derivation for one project and cache the computed values."""

    observations = (
        db.query(ProgressObservation)
        .filter(ProgressObservation.project_id == project.id)
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
    # Cache the computed (not the override-effective) values.
    progress.computed_phase = result.computed_phase.value
    progress.computed_confidence = result.computed_confidence
    progress.computed_at = datetime.utcnow()
    return result


# --- Read --------------------------------------------------------------------


def get_progress_view(db: Session, project_id: int, today: date | None = None) -> dict | None:
    """Assemble the full progress view payload (dict matching ProjectProgressSchema).

    Returns ``None`` if the project does not exist.
    """

    today = today or date.today()
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return None

    progress = get_or_create_progress(db, project_id)
    result = derive_for_project(db, project, progress, today)
    db.commit()

    observations = (
        db.query(ProgressObservation)
        .filter(ProgressObservation.project_id == project_id)
        .order_by(ProgressObservation.observed_date.desc().nullslast(), ProgressObservation.id.desc())
        .all()
    )

    pf_documents = _track_documents(db, project_id, ObservationTrack.PF)
    parl_documents = _track_documents(db, project_id, ObservationTrack.PARL)

    # Superior aggregation over leaf children.
    children = (
        db.query(Project).filter(Project.superior_project_id == project_id).all()
    )
    is_superior = len(children) > 0
    child_payloads: list[dict] = []
    span_min = span_max = None
    if is_superior:
        child_phases: list[MainPhase] = []
        for child in children:
            child_progress = get_or_create_progress(db, child.id)
            child_result = derive_for_project(db, child, child_progress, today)
            child_phases.append(child_result.effective_phase)
            child_payloads.append(
                {
                    "project_id": child.id,
                    "name": child.name,
                    "effective_phase": child_result.effective_phase.value,
                    "lifecycle_status": child_result.lifecycle.value,
                }
            )
        db.commit()
        span = aggregate_span(child_phases)
        if span is not None:
            span_min, span_max = span[0].value, span[1].value

    return {
        "project_id": project_id,
        "effective_phase": result.effective_phase.value,
        "computed_phase": result.computed_phase.value,
        "computed_confidence": result.computed_confidence,
        "is_overridden": result.is_overridden,
        "manual_override_note": progress.manual_override_note,
        "computed_at": progress.computed_at,
        "has_planfeststellung": bool(progress.has_planfeststellung),
        "parl_befassung_relevant": resolve_parl_relevant(progress, project),
        "parl_befassung_relevant_override": progress.parl_befassung_relevant,
        "lifecycle_status": result.lifecycle.value,
        "pf_state": result.pf_state.value if result.pf_state else None,
        "parl_state": result.parl_state.value if result.parl_state else None,
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
    get_or_create_progress(db, project_id)

    observation = ProgressObservation(
        project_id=project_id,
        source_type=data.get("source_type", SourceType.MANUELL.value),
        track=data["track"],
        asserted_state=data["asserted_state"],
        observed_date=data.get("observed_date"),
        confidence=data.get("confidence"),
        note=data.get("note"),
        is_derived=False,
        created_by_user_id=user.id if user else None,
        username_snapshot=user.username if user else None,
    )
    db.add(observation)
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
    derive_for_project(db, project, progress, today)
    db.commit()
    return True
