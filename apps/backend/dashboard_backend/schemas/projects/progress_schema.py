"""Pydantic schemas for the project-progress / planning-state API.

Enums are expressed as ``Literal[...]`` unions so ``make gen-api`` emits clean
TypeScript string unions instead of opaque enum refs.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, Optional, get_args

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, computed_field

from dashboard_backend.services.date_precision import date_text

# --- Literal aliases (mirror models.projects.progress_enums) -----------------

MainPhaseLiteral = Literal[
    "NICHT_GESTARTET", "VORPLANUNG", "GENEHMIGUNGSPLANUNG", "BAU", "IN_BETRIEB"
]
# Only the planning phases may be skipped per project group (#164) — start,
# construction and operation are always part of a project's life.
SkippablePhaseLiteral = Literal["VORPLANUNG", "GENEHMIGUNGSPLANUNG"]
ParallelStateLiteral = Literal["OFFEN", "LAEUFT", "ABGESCHLOSSEN"]
LifecycleStatusLiteral = Literal["AKTIV", "PAUSIERT", "ABGEBROCHEN", "ERSETZT"]


def _known_lifecycle(value: object) -> object:
    """Read a stored lifecycle value this code does not know as AKTIV.

    A rollback to an older release must not fail on a value written by a newer
    one (Expand/Contract, docs/features/feature-project-replacement.md → W4)."""
    return value if value in get_args(LifecycleStatusLiteral) else "AKTIV"


# Response fields only — input (PATCH, MCP) still rejects unknown values.
LifecycleStatusRead = Annotated[LifecycleStatusLiteral, BeforeValidator(_known_lifecycle)]
SourceTypeLiteral = Literal[
    "VIB", "FINVE", "FULDA_RUNDE", "BAUPORTAL", "MEDIEN", "INFRAPLAN", "GVFG", "MANUELL"
]
# Sources an editor may record by hand. The Fulda-Runde is read only through its
# importer (feature-fulda-import.md, W3), never as a manual observation.
ManualSourceTypeLiteral = Literal["VIB", "FINVE", "BAUPORTAL", "MEDIEN", "INFRAPLAN", "MANUELL"]
TrackLiteral = Literal["MAIN", "PF", "PARL"]
DatePrecisionLiteral = Literal["EXACT", "MONTH", "YEAR", "NOT_BEFORE", "ASSUMED"]
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
    # Sort value only — shown always through ``date_text`` (with precision).
    observed_date: Optional[date] = None
    date_precision: DatePrecisionLiteral = "EXACT"
    date_label: Optional[str] = None
    confidence: Optional[float] = None
    note: Optional[str] = None
    is_derived: bool
    is_expected: bool = False
    username_snapshot: Optional[str] = None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def date_text(self) -> Optional[str]:
        """Display text of the date at its precision („2028“, „nach 2031“)."""
        return date_text(self.observed_date, self.date_precision, self.date_label)


DATE_PRECISION_HELP = (
    "How precisely the date is known: EXACT = published day, MONTH = only the "
    "month (stored as the 1st), YEAR = only the year (stored as 1 Jan), "
    "NOT_BEFORE = only a lower bound, no date (store the first possible day, "
    "e.g. 2032-01-01 for „nach 2031“), ASSUMED = derived from a rule, not "
    "published (e.g. Baubeginn + 6 months)."
)


class ProgressObservationCreate(BaseModel):
    source_type: ManualSourceTypeLiteral = "MANUELL"
    track: TrackLiteral
    asserted_state: str
    observed_date: Optional[date] = None
    date_precision: DatePrecisionLiteral = Field(default="EXACT", description=DATE_PRECISION_HELP)
    date_label: Optional[str] = Field(default=None, max_length=120)
    confidence: Optional[float] = None
    note: Optional[str] = None
    is_expected: bool = False


class ProgressObservationUpdate(BaseModel):
    """Partial change of a manual observation; omitted fields stay as they are.
    ``clear_date_label`` removes the label (null is ambiguous with "omitted")."""

    observed_date: Optional[date] = None
    date_precision: Optional[DatePrecisionLiteral] = Field(default=None, description=DATE_PRECISION_HELP)
    date_label: Optional[str] = Field(default=None, max_length=120)
    clear_date_label: bool = False
    confidence: Optional[float] = None
    note: Optional[str] = None
    is_expected: Optional[bool] = None


# --- Derivation breakdown ----------------------------------------------------


class SourceContributionSchema(BaseModel):
    """One observation annotated with its effective weight and decisive role."""

    observation_id: Optional[int] = None
    source_type: SourceTypeLiteral
    track: TrackLiteral
    asserted_state: str
    observed_date: Optional[date] = None  # sort value; shown as ``date_text``
    date_precision: DatePrecisionLiteral = "EXACT"
    date_text: Optional[str] = None
    effective_confidence: float  # trust × recency; decides credibility only
    was_decisive: bool
    trust: float = 0.0  # explicit confidence, else the source default (no recency)
    is_lower_bound: bool = False  # FinVe: "at least this phase", does not age
    in_conflict: bool = False  # side of a reported set-back conflict


class PhaseConflictSchema(BaseModel):
    """A newer status report asserts a lower phase than older information.

    ``applied``: the report set the headline back (trust at least that of every
    contradicting observation); otherwise it was held back.
    """

    observation_id: Optional[int] = None
    source_type: SourceTypeLiteral
    asserted_phase: MainPhaseLiteral
    observed_date: Optional[date] = None  # sort value; shown as ``date_text``
    date_precision: DatePrecisionLiteral = "EXACT"
    date_text: Optional[str] = None
    trust: float
    contradicted_ids: list[Optional[int]] = []
    contradicted_phase: MainPhaseLiteral
    applied: bool


class ProgressConflictRowSchema(BaseModel):
    """One project in the admin list of planning-state conflicts."""

    project_id: int
    project_name: str
    project_number: Optional[str] = None
    computed_phase: MainPhaseLiteral
    conflict: PhaseConflictSchema
    # The contradicted observations, for the admin table.
    contradicted: list[SourceContributionSchema] = []


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
    lifecycle_status: LifecycleStatusRead
    is_known: bool = True  # False → no phase info ("Unbekannt")
    is_superior: bool = False  # True → child has its own subprojects (show the span)
    span_min_phase: Optional[MainPhaseLiteral] = None
    span_max_phase: Optional[MainPhaseLiteral] = None


# --- Lifecycle references ----------------------------------------------------


class LifecycleProjectRef(BaseModel):
    """Successor / replaced project named in the lifecycle overlay."""

    id: int
    name: str
    project_number: Optional[str] = None


# --- PATCH input -------------------------------------------------------------


class ProjectProgressUpdate(BaseModel):
    has_planfeststellung: Optional[bool] = None
    parl_befassung_relevant: Optional[bool] = None  # null clears → group default
    lifecycle_status: Optional[LifecycleStatusLiteral] = None
    # Successor — required with ERSETZT, rejected with any other status.
    # Switching to AKTIV clears successor, note and date.
    replaced_by_project_id: Optional[int] = None
    lifecycle_note: Optional[str] = None  # "" clears
    lifecycle_date: Optional[date] = None
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
    clear_lifecycle_date: Optional[bool] = None


# --- Forecast (Phase 3) ------------------------------------------------------


class ForecastStepSchema(BaseModel):
    phase: MainPhaseLiteral
    # Sort value only — shown through ``date_text``.
    expected_date: Optional[date] = None
    # "VIB-PFA" | "Fulda-Runde" | "Infraplan" | "GVFG" | "Manuell" | "Annahme" | "BVWP" | "Schätzung"
    source: str
    date_precision: DatePrecisionLiteral = "EXACT"
    date_label: Optional[str] = None
    # Display text with precision („nach 2031“, „ca. 07/2028 (Annahme)“).
    date_text: Optional[str] = None
    # How an ASSUMED / derived date came about („Annahme: 6 Monate Bauzeit“).
    derivation: Optional[str] = None


class IbnDoubtPeriodSchema(BaseModel):
    label: str
    aid: float  # Mio. €


class IbnDoubtSchema(BaseModel):
    """The GVFG-Finanzreihe still funds the project after its known
    commissioning year — that year is doubtful (the forecast stays as is)."""

    ibn_year: int
    ibn_source: str  # "Infraplan" or "GVFG <edition>" (Inbetriebnahme gepl.), the more recent
    edition: str  # newest GVFG edition, e.g. "2025–2029"
    program_id: int
    entry_ids: list[int]
    aid_after: float  # Mio. € in year columns after ibn_year
    aid_total: float  # Mio. € in all year columns
    periods: list[IbnDoubtPeriodSchema] = []


class ProgressForecastSchema(BaseModel):
    current_phase: MainPhaseLiteral
    remaining_text: Optional[str] = None
    estimated_phase_end: Optional[date] = None
    estimated_phase_end_precision: DatePrecisionLiteral = "EXACT"
    next_steps: list[ForecastStepSchema] = []
    has_data: bool = False
    ibn_doubt: Optional[IbnDoubtSchema] = None


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
    lifecycle_status: LifecycleStatusRead
    lifecycle_note: Optional[str] = None
    lifecycle_date: Optional[date] = None
    # ERSETZT: the successor (null when it was deleted). ``replaces``: projects
    # that name this one as their successor.
    replaced_by: Optional[LifecycleProjectRef] = None
    replaces: list[LifecycleProjectRef] = []

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
    conflict: Optional[PhaseConflictSchema] = None
    pf_documents: list[TrackDocumentSchema] = []
    parl_documents: list[TrackDocumentSchema] = []

    # Superior aggregation (null span → project treated as its own leaf).
    is_superior: bool = False
    span_min_phase: Optional[MainPhaseLiteral] = None
    span_max_phase: Optional[MainPhaseLiteral] = None
    children: list[ProgressChildSchema] = []

    # Planning phases the project's groups skip (#164) and the view hides — all
    # groups must skip a phase, and it still shows while data places the project
    # (or a subproject / dated forecast step) in it.
    hidden_phases: list[SkippablePhaseLiteral] = []

    # Forecast (Phase 3): remaining duration of the current phase + next steps.
    forecast: Optional[ProgressForecastSchema] = None


# --- Multi-project timeline ("Zeitstrahl") -----------------------------------


class TimelineMilestoneSchema(BaseModel):
    # PHASE = start of ``phase``; PFB = Planfeststellung; PARL = parl. involvement.
    kind: Literal["PHASE", "PFB", "PARL"]
    phase: Optional[MainPhaseLiteral] = None
    date: date
    source: str  # "VIB-PFA" | "Fulda-Runde" | "Manuell" | source label for evidence
    # CONCRETE = dated milestone; EVIDENCE = "spätestens seit" from an observation.
    certainty: Literal["CONCRETE", "EVIDENCE"]
    # ``date`` is the sort value; NOT_BEFORE = lower bound only (no date).
    date_precision: DatePrecisionLiteral = "EXACT"
    date_label: Optional[str] = None
    date_text: Optional[str] = None  # display text with precision
    derivation: Optional[str] = None  # how an ASSUMED date came about


class TimelinePeriodSchema(BaseModel):
    start: date
    end: date


class ProjectTimelineSchema(BaseModel):
    project_id: int
    name: str
    project_number: Optional[str] = None
    superior_project_id: Optional[int] = None
    lifecycle_status: LifecycleStatusRead
    milestones: list[TimelineMilestoneSchema] = []
    # Superior whose subprojects build in separate stages: the disjoint
    # construction periods (union of the members' Baubeginn–IB intervals).
    # Empty when construction is one continuous period.
    construction_periods: list[TimelinePeriodSchema] = []


class ProjectGroupTimelineSchema(BaseModel):
    group_id: int
    # Only projects with at least one concrete milestone.
    items: list[ProjectTimelineSchema] = []
    # Projects of the group left out for lack of credible dates.
    without_dates_count: int = 0
