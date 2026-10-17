from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GvfgParseResultSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pdf_filename: str
    year_from: int | None
    year_to: int | None
    is_annex: bool
    status: str
    error_message: str | None
    parsed_at: datetime
    username_snapshot: str | None
    confirmed_at: datetime | None
    confirmed_by_snapshot: str | None


class GvfgParseResultDetail(GvfgParseResultSummary):
    # services.gvfg_parser.ParseResult.to_json() + "suggestions"
    result_json: dict[str, Any] | None


class GvfgConfirmRequest(BaseModel):
    # key → project ids (empty list: no project)
    assignments: dict[str, list[int]] = Field(default_factory=dict)
    # keys that get a new project
    create_projects: list[str] = Field(default_factory=list)


class GvfgConfirmResponse(BaseModel):
    entries: int
    links: int
    projects_created: int
    groups_added: int


class GvfgPeriodSchema(BaseModel):
    label: str
    year_from: int | None
    year_to: int | None
    kind: str


class GvfgProgramSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    year_from: int
    year_to: int
    title: str
    stand: date | None
    has_annex: bool
    periods: list[GvfgPeriodSchema]


class GvfgAmountSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    computed: bool
    cost_total: Decimal | None
    cost_eligible: Decimal | None
    aid_total: Decimal | None
    periods: dict[str, Decimal]


class GvfgProjectRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class GvfgEntrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_id: int
    key: str
    key_raw: str
    land: str
    kind: str
    part: str
    city: str | None
    name: str | None
    lph: str | None
    funding_type: str | None
    funding_rate: int | None
    start_year: int | None
    construction_start: int | None
    commissioning_planned: int | None
    commissioning_actual: int | None
    amounts: list[GvfgAmountSchema]
    projects: list[GvfgProjectRef]


class GvfgProjectEntrySchema(GvfgEntrySchema):
    program: GvfgProgramSchema
