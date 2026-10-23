"""Schemas of the Infraplan import (stage 1: parse drafts).

See docs/features/feature-infraplan-import.md. A parse result holds every row
of the measure tables in ``result_json`` (``InfraplanParseOutput``); the review
and confirmation (stage 2) work on these rows.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SectionKey = Literal["BP_A", "BP_B", "BP_C", "BP_D", "GVFG_A", "GVFG_C", "INVKG"]
AssignmentSource = Literal["NUMBER", "FUZZY", "MANUAL", "AGENT"]


class InfraplanCostRef(BaseModel):
    """Target of a cost reference ("Ref. Teil B 20 | E.…")."""

    section: str
    lfd_nr: int
    resolved: bool = False
    # Cost of the entry that finally carries it (references are followed).
    cost_mio: Optional[float] = None


class InfraplanSuggestion(BaseModel):
    """A project suggested for a row. ``reason``: NUMBER (number of an earlier
    year or the project's own number), GVFG_KEY, PREVIOUS_YEAR (same text in an
    earlier year), ALIAS (Deutschlandtakt id), CONTEXT (subproject of the
    parent named by the Bezeichnung), FUZZY (name). ``detail`` says what
    matched; ``previous_note`` is the note of the earlier year's assignment.
    ``redirected_from``: the hit was on this replaced project and moved to its
    successor (feature-project-replacement.md)."""

    project_id: int
    confidence: float
    reason: Literal["NUMBER", "GVFG_KEY", "PREVIOUS_YEAR", "ALIAS", "CONTEXT", "FUZZY"]
    detail: Optional[str] = None
    previous_year: Optional[int] = None
    previous_note: Optional[str] = None
    redirected_from: Optional[int] = None


class InfraplanParsedRow(BaseModel):
    """One table row as read from the PDF, values normalised, raw text kept."""

    row_key: str  # "<section>-<lfd_nr>", unique within a draft
    section: SectionKey
    lfd_nr: int
    page: int

    project_numbers_raw: Optional[str] = None
    project_numbers: list[str] = Field(default_factory=list)
    primary_number: Optional[str] = None

    bezeichnung: Optional[str] = None
    massnahme: Optional[str] = None
    laender: Optional[str] = None

    state_raw: Optional[str] = None
    lph_from: Optional[int] = None
    lph_to: Optional[int] = None
    under_construction: bool = False
    baurecht: bool = False

    ibn_raw: Optional[str] = None
    ibn_year: Optional[int] = None
    ibn_qualifier: Optional[Literal["OFFEN", "BIS", "SPANNE"]] = None

    cost_raw: Optional[str] = None
    cost_mio: Optional[float] = None
    cost_kind: Literal["GWU", "GESAMTKOSTEN"]
    cost_ref_raw: Optional[str] = None
    cost_ref: Optional[InfraplanCostRef] = None

    parl_raw: Optional[str] = None
    parl_state: Optional[
        Literal["ABGESCHLOSSEN", "LAEUFT", "VORGESEHEN", "NICHT_VEREINBART"]
    ] = None

    footnote_refs: list[int] = Field(default_factory=list)
    footnotes: dict[str, str] = Field(default_factory=dict)

    # Review state (stage 2): suggestions from the matcher, the chosen
    # projects and who/what chose them.
    suggestions: list[InfraplanSuggestion] = Field(default_factory=list)
    project_ids: list[int] = Field(default_factory=list)
    assignment_source: Optional[AssignmentSource] = None
    assignment_note: Optional[str] = None
    assigned_by: Optional[str] = None


class InfraplanSectionSummary(BaseModel):
    key: SectionKey
    title: str
    row_count: int
    pages: list[int]


class InfraplanWarning(BaseModel):
    """A plausibility finding. Any warning blocks an unforced confirmation."""

    kind: Literal[
        "GAP",
        "DUPLICATE",
        "UNRESOLVED_REF",
        "NO_LAYOUT",
        "EMPTY_SECTION",
        "UNREADABLE_TEXT",
        "UNPARSED_COST",
    ]
    section: Optional[str] = None
    lfd_nr: Optional[int] = None
    page: Optional[int] = None
    message: str


class InfraplanKpiPage(BaseModel):
    page: int
    kind: Literal["STEUERUNG", "INFORMATION"]
    title: str


class InfraplanParseOutput(BaseModel):
    """Content of ``infraplan_parse_result.result_json``."""

    sections: list[InfraplanSectionSummary]
    rows: list[InfraplanParsedRow]
    footnotes: dict[str, str] = Field(default_factory=dict)
    page_count: int = 0


class InfraplanParseResultListItem(BaseModel):
    """A draft without its rows — for the list view."""

    id: int
    year: int
    status: str
    file_name: str
    task_id: Optional[str] = None
    error_message: Optional[str] = None
    warnings_json: Optional[list[InfraplanWarning]] = None
    kpi_pages_json: Optional[list[InfraplanKpiPage]] = None
    created_at: datetime
    username_snapshot: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    confirmed_by_snapshot: Optional[str] = None
    row_count: Optional[int] = None
    assigned_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class InfraplanProjectRef(BaseModel):
    id: int
    name: str
    superior_project_id: Optional[int] = None
    is_draft: bool = False


class InfraplanMissingEntry(BaseModel):
    section: str
    lfd_nr: int
    primary_number: Optional[str] = None
    massnahme: Optional[str] = None


class InfraplanMissingProject(BaseModel):
    """A project with an entry in the previous year but none in this draft."""

    project_id: int
    project_name: str
    previous_year: int
    entries: list[InfraplanMissingEntry]


class InfraplanParseResultSchema(InfraplanParseResultListItem):
    """A draft with all parsed rows, the projects they reference and the
    comparison with the previous year."""

    result_json: Optional[InfraplanParseOutput] = None
    has_pdf: bool = False
    projects: dict[str, InfraplanProjectRef] = Field(default_factory=dict)
    previous_year: Optional[int] = None
    missing_from_previous: list[InfraplanMissingProject] = Field(default_factory=list)
    report_year_exists: bool = False


# --- Review (stage 2) ----------------------------------------------------------

EDITABLE_ROW_FIELDS = (
    "bezeichnung",
    "massnahme",
    "laender",
    "state_raw",
    "lph_from",
    "lph_to",
    "under_construction",
    "baurecht",
    "ibn_raw",
    "ibn_year",
    "ibn_qualifier",
    "cost_mio",
    "parl_raw",
    "parl_state",
)


class InfraplanRowValues(BaseModel):
    """Corrections of parsed values; only set fields are applied."""

    bezeichnung: Optional[str] = None
    massnahme: Optional[str] = None
    laender: Optional[str] = None
    state_raw: Optional[str] = None
    lph_from: Optional[int] = Field(None, ge=0, le=9)
    lph_to: Optional[int] = Field(None, ge=0, le=9)
    under_construction: Optional[bool] = None
    baurecht: Optional[bool] = None
    ibn_raw: Optional[str] = None
    ibn_year: Optional[int] = Field(None, ge=1990, le=2100)
    ibn_qualifier: Optional[Literal["OFFEN", "BIS", "SPANNE"]] = None
    cost_mio: Optional[float] = None
    parl_raw: Optional[str] = None
    parl_state: Optional[
        Literal["ABGESCHLOSSEN", "LAEUFT", "VORGESEHEN", "NICHT_VEREINBART"]
    ] = None


class InfraplanRowPatch(BaseModel):
    """Change the assignment and/or values of one draft row. ``project_ids``
    replaces the assignment (empty list = none); omitted = unchanged."""

    project_ids: Optional[list[int]] = None
    note: Optional[str] = None
    values: Optional[InfraplanRowValues] = None


class InfraplanApplySuggestions(BaseModel):
    min_confidence: float = Field(0.85, ge=0.0, le=1.0)
    # Rows that already carry an assignment are left alone unless False.
    only_unassigned: bool = True


class InfraplanApplyResult(BaseModel):
    applied: int
    unassigned: int


class InfraplanSubprojectCreate(BaseModel):
    # Without a parent the project is created on its own (draft, no geometry).
    parent_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=255)


class InfraplanSubprojectResult(BaseModel):
    project_id: int
    name: str
    row: InfraplanParsedRow


class InfraplanConfirmRequest(BaseModel):
    parse_result_id: int
    published_on: Optional[date] = None
    title: Optional[str] = Field(None, max_length=255)
    # Frontend only: confirm despite parser warnings.
    force: bool = False


class InfraplanConfirmResult(BaseModel):
    report_id: int
    year: int
    entries: int
    links: int
    unassigned: int
    projects_updated: int


class InfraplanReportSchema(BaseModel):
    id: int
    year: int
    title: Optional[str] = None
    published_on: Optional[date] = None
    parse_result_id: Optional[int] = None
    created_at: datetime
    entry_count: int = 0
    assigned_count: int = 0
    kpi_value_count: int = 0
    kpi_unchecked_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class InfraplanParseLaunchResponse(BaseModel):
    task_id: str
    parse_result_id: int
