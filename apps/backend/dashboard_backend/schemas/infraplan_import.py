"""Schemas of the Infraplan import (stage 1: parse drafts).

See docs/features/feature-infraplan-import.md. A parse result holds every row
of the measure tables in ``result_json`` (``InfraplanParseOutput``); the review
and confirmation (stage 2) work on these rows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SectionKey = Literal["BP_A", "BP_B", "BP_C", "BP_D", "GVFG_A", "GVFG_C", "INVKG"]


class InfraplanCostRef(BaseModel):
    """Target of a cost reference ("Ref. Teil B 20 | E.…")."""

    section: str
    lfd_nr: int
    resolved: bool = False
    # Cost of the entry that finally carries it (references are followed).
    cost_mio: Optional[float] = None


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


class InfraplanSectionSummary(BaseModel):
    key: SectionKey
    title: str
    row_count: int
    pages: list[int]


class InfraplanWarning(BaseModel):
    """A plausibility finding. Any warning blocks an unforced confirmation."""

    kind: Literal["GAP", "DUPLICATE", "UNRESOLVED_REF", "NO_LAYOUT", "EMPTY_SECTION"]
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

    model_config = ConfigDict(from_attributes=True)


class InfraplanParseResultSchema(InfraplanParseResultListItem):
    """A draft with all parsed rows."""

    result_json: Optional[InfraplanParseOutput] = None
    has_pdf: bool = False


class InfraplanParseLaunchResponse(BaseModel):
    task_id: str
    parse_result_id: int
