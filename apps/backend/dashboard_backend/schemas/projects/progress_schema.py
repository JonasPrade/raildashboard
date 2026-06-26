"""Pydantic schemas for the project-progress / planning-state API.

Enums are expressed as ``Literal[...]`` unions so ``make gen-api`` emits clean
TypeScript string unions instead of opaque enum refs.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

# --- Literal aliases (mirror models.projects.progress_enums) -----------------

MainPhaseLiteral = Literal[
    "NICHT_GESTARTET", "VORPLANUNG", "GENEHMIGUNGSPLANUNG", "BAU", "IN_BETRIEB"
]
ParallelStateLiteral = Literal["OFFEN", "LAEUFT", "ABGESCHLOSSEN"]
LifecycleStatusLiteral = Literal["AKTIV", "PAUSIERT", "ABGEBROCHEN"]
SourceTypeLiteral = Literal[
    "VIB", "FINVE", "FULDA_RUNDE", "BAUPORTAL", "MEDIEN", "MANUELL"
]
TrackLiteral = Literal["MAIN", "PF", "PARL"]
# Documents can only be linked behind the PF / parliamentary tracks.
DocumentTrackLiteral = Literal["PF", "PARL"]


# --- Documents ---------------------------------------------------------------


class DocumentRefSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    file_path: str
    date: Optional[date] = None
    source: Optional[str] = None


class TrackDocumentSchema(BaseModel):
    """A document link scoped to a track, with the resolved document."""

    id: int
    track: DocumentTrackLiteral
    document: DocumentRefSchema


class LinkDocumentInput(BaseModel):
    document_id: int


class PfLinkSchema(BaseModel):
    """A single commented reference link for the Planfeststellung."""

    url: str
    comment: Optional[str] = None


# --- Observations ------------------------------------------------------------


class ProgressObservationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: SourceTypeLiteral
    track: TrackLiteral
    asserted_state: str
    observed_date: Optional[date] = None
    confidence: Optional[float] = None
    note: Optional[str] = None
    is_derived: bool
    is_expected: bool = False
    username_snapshot: Optional[str] = None
    created_at: datetime


class ProgressObservationCreate(BaseModel):
    source_type: SourceTypeLiteral = "MANUELL"
    track: TrackLiteral
    asserted_state: str
    observed_date: Optional[date] = None
    confidence: Optional[float] = None
    note: Optional[str] = None
    is_expected: bool = False


# --- Derivation breakdown ----------------------------------------------------


class SourceContributionSchema(BaseModel):
    """One observation annotated with its effective weight and decisive role."""

    observation_id: Optional[int] = None
    source_type: SourceTypeLiteral
    track: TrackLiteral
    asserted_state: str
    observed_date: Optional[date] = None
    effective_confidence: float
    was_decisive: bool


# --- Superior aggregation ----------------------------------------------------


class ProgressChildSchema(BaseModel):
    """A direct child shown under a superior project's aggregated progress.

    A child may itself be a superior (``is_superior``): then its planning state is
    a span over *its own* leaf descendants (``span_min_phase``..``span_max_phase``)
    rather than a single phase, so multi-level nesting stays visible at every level.
    """

    project_id: int
    name: str
    effective_phase: MainPhaseLiteral  # for a nested superior: the span's upper bound
    lifecycle_status: LifecycleStatusLiteral
    is_known: bool = True  # False → no phase info ("Unbekannt")
    is_superior: bool = False  # True → child has its own subprojects (show the span)
    span_min_phase: Optional[MainPhaseLiteral] = None
    span_max_phase: Optional[MainPhaseLiteral] = None


# --- PATCH input -------------------------------------------------------------


class ProjectProgressUpdate(BaseModel):
    has_planfeststellung: Optional[bool] = None
    parl_befassung_relevant: Optional[bool] = None  # null clears → group default
    lifecycle_status: Optional[LifecycleStatusLiteral] = None
    manual_phase_override: Optional[MainPhaseLiteral] = None
    manual_override_note: Optional[str] = None
    pf_state_override: Optional[ParallelStateLiteral] = None
    parl_state_override: Optional[ParallelStateLiteral] = None
    # Parliamentary involvement details (single editorial block).
    parl_befassung_text: Optional[str] = None
    parl_drucksache_url: Optional[str] = None
    parl_befassung_date: Optional[date] = None
    # Planfeststellung details (single editorial block, mirrors the parl one).
    pf_text: Optional[str] = None
    pf_date: Optional[date] = None
    pf_links: Optional[list[PfLinkSchema]] = None
    # Sentinel fields to explicitly clear a nullable override (since None in the
    # fields above is indistinguishable from "not provided" under exclude_unset).
    clear_phase_override: Optional[bool] = None
    clear_parl_relevant: Optional[bool] = None
    clear_parl_state_override: Optional[bool] = None
    clear_pf_state_override: Optional[bool] = None


# --- Forecast (Phase 3) ------------------------------------------------------


class ForecastStepSchema(BaseModel):
    phase: MainPhaseLiteral
    expected_date: Optional[date] = None
    source: str  # "VIB-PFA" | "Fulda-Runde" | "BVWP" | "Schätzung"


class ProgressForecastSchema(BaseModel):
    current_phase: MainPhaseLiteral
    remaining_text: Optional[str] = None
    estimated_phase_end: Optional[date] = None
    next_steps: list[ForecastStepSchema] = []
    has_data: bool = False


# --- Sammel-FinVe phase assignment (admin) -----------------------------------


class SammelFinveProjectRef(BaseModel):
    id: int
    name: str


class SammelFinveProgressSchema(BaseModel):
    finve_id: int
    name: Optional[str] = None
    starting_year: Optional[int] = None
    # Manual override (None = use auto-detection).
    progress_phase: Optional[MainPhaseLiteral] = None
    # Phase auto-detected from the Leistungsphase in the name (None = ambiguous).
    auto_phase: Optional[MainPhaseLiteral] = None
    # Effective phase used for derivation (manual ?? auto); None → needs assignment.
    effective_phase: Optional[MainPhaseLiteral] = None
    needs_assignment: bool
    projects: list[SammelFinveProjectRef] = []


class FinveProgressPhaseUpdate(BaseModel):
    # None clears the manual override (falls back to auto-detection).
    progress_phase: Optional[MainPhaseLiteral] = None


# --- GET response ------------------------------------------------------------


class ProjectProgressSchema(BaseModel):
    project_id: int

    # Effective (override-aware) headline.
    effective_phase: MainPhaseLiteral
    computed_phase: MainPhaseLiteral
    computed_confidence: float
    is_known: bool = True  # False → no phase info ("Unbekannt"), not NICHT_GESTARTET
    is_overridden: bool
    manual_override_note: Optional[str] = None
    computed_at: Optional[datetime] = None

    # Flags & lifecycle.
    has_planfeststellung: bool
    parl_befassung_relevant: bool  # resolved (override ?? group default)
    parl_befassung_relevant_override: Optional[bool] = None  # raw stored value
    lifecycle_status: LifecycleStatusLiteral

    # Resolved parallel tracks (null when the track is inactive).
    pf_state: Optional[ParallelStateLiteral] = None
    parl_state: Optional[ParallelStateLiteral] = None
    pf_state_override: Optional[ParallelStateLiteral] = None  # raw stored override
    parl_state_override: Optional[ParallelStateLiteral] = None  # raw stored override

    # Parliamentary involvement details (single editorial block).
    parl_befassung_text: Optional[str] = None
    parl_drucksache_url: Optional[str] = None
    parl_befassung_date: Optional[date] = None

    # Planfeststellung details (single editorial block, mirrors the parl one).
    pf_text: Optional[str] = None
    pf_date: Optional[date] = None
    pf_links: list[PfLinkSchema] = []

    # Breakdown.
    observations: list[ProgressObservationSchema] = []
    contributions: list[SourceContributionSchema] = []
    pf_documents: list[TrackDocumentSchema] = []
    parl_documents: list[TrackDocumentSchema] = []

    # Superior aggregation (null span → project treated as its own leaf).
    is_superior: bool = False
    span_min_phase: Optional[MainPhaseLiteral] = None
    span_max_phase: Optional[MainPhaseLiteral] = None
    children: list[ProgressChildSchema] = []

    # Forecast (Phase 3): remaining duration of the current phase + next steps.
    forecast: Optional[ProgressForecastSchema] = None
