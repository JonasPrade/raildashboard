"""Schemas of the confirmed Infraplan years: entries per project, cost
forecast, public year lists and KPIs (docs/features/feature-infraplan-import.md)."""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

KpiKind = Literal["STEUERUNG", "INFORMATION"]
KpiCategory = Literal["AUS_NEUBAU", "BESTANDSNETZ", "UEBERGEORDNET"]
KpiValueKind = Literal["IST", "ZIEL"]
KpiStatus = Literal["UNGEPRUEFT", "GEPRUEFT"]


class InfraplanEntrySchema(BaseModel):
    """One confirmed row of a year."""

    id: int
    report_year: int
    section: str
    section_title: str
    lfd_nr: int
    page: Optional[int] = None
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
    ibn_qualifier: Optional[str] = None
    cost_mio: Optional[float] = None
    cost_kind: Optional[str] = None
    cost_ref_raw: Optional[str] = None
    cost_ref_entry_id: Optional[int] = None
    # Cost of the entry that finally carries it (references followed).
    resolved_cost_mio: Optional[float] = None
    parl_raw: Optional[str] = None
    parl_state: Optional[str] = None
    footnotes: dict[str, str] = Field(default_factory=dict)


class InfraplanProjectEntrySchema(InfraplanEntrySchema):
    """An entry as linked to a project: with who linked it and why."""

    project_id: int
    project_name: Optional[str] = None
    assignment_source: Optional[str] = None
    assignment_note: Optional[str] = None


class InfraplanCostForecast(BaseModel):
    """Gesamtkostenprognose of a project from its newest Infraplan year.

    ``from_subprojects``: the project has no row of its own; the value sums
    its subprojects (collective GWU and references counted once)."""

    year: int
    total_mio: float
    label: str
    from_subprojects: bool = False
    is_gvfg: bool = False
    entry_ids: list[int] = Field(default_factory=list)
    footnotes: dict[str, str] = Field(default_factory=dict)


class ProjectInfraplanSchema(BaseModel):
    entries: list[InfraplanProjectEntrySchema] = Field(default_factory=list)
    latest_year: Optional[int] = None
    # The project had entries in an earlier year but has none in latest_year.
    missing_in_latest: bool = False
    cost_forecast: Optional[InfraplanCostForecast] = None


class InfraplanPublicReport(BaseModel):
    year: int
    title: Optional[str] = None
    published_on: Optional[date] = None
    entry_count: int = 0


class InfraplanReportEntrySchema(InfraplanEntrySchema):
    projects: list[dict] = Field(default_factory=list)  # [{id, name}]


# --- KPIs --------------------------------------------------------------------


class InfraplanKpiSchema(BaseModel):
    id: int
    key: str
    name: str
    unit: Optional[str] = None
    kind: str
    category: Optional[str] = None
    description: Optional[str] = None
    sort_order: int = 0


class InfraplanKpiValueSchema(BaseModel):
    id: int
    kpi_key: str
    report_year: int
    year: int
    value_kind: KpiValueKind
    series: Optional[str] = None
    value: float
    source_page: Optional[int] = None
    status: KpiStatus
    entered_by_snapshot: Optional[str] = None


class InfraplanKpiDefinitionInput(BaseModel):
    """A new KPI (stable ``key``) or a correction of an existing one."""

    key: str = Field(pattern=r"^[a-z0-9_]{3,100}$")
    name: str = Field(min_length=1, max_length=255)
    unit: Optional[str] = Field(None, max_length=50)
    kind: KpiKind
    category: Optional[KpiCategory] = None
    description: Optional[str] = None


class InfraplanKpiValueInput(BaseModel):
    """One value. ``value`` null removes the stored value of this slot."""

    kpi_key: str
    year: int = Field(ge=1990, le=2100)
    value_kind: KpiValueKind
    series: Optional[str] = Field(None, max_length=100)
    value: Optional[float] = None
    source_page: Optional[int] = Field(None, ge=1)


class InfraplanKpiValuesUpdate(BaseModel):
    values: list[InfraplanKpiValueInput] = Field(default_factory=list)
    definitions: list[InfraplanKpiDefinitionInput] = Field(default_factory=list)


class InfraplanKpiValuesResult(BaseModel):
    written: int
    removed: int
    definitions_created: int


class InfraplanKpiApproveResult(BaseModel):
    approved: int


class InfraplanKpiSeriesValue(BaseModel):
    report_year: int
    year: int
    value_kind: KpiValueKind
    series: Optional[str] = None
    value: float


class InfraplanPublicKpi(InfraplanKpiSchema):
    values: list[InfraplanKpiSeriesValue] = Field(default_factory=list)
