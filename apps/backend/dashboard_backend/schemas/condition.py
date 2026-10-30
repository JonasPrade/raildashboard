"""Schemas of the InfraGO-Zustandsbericht (docs/features/feature-zustandsbericht.md)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ConditionDomain = Literal["FAHRWEG", "PERSONENBAHNHOF"]
ConditionScope = Literal["GESAMT", "HLN", "FLN", "SE", "LAND"]
ConditionMetric = Literal[
    "WBW",
    "WBW_BEWERTET",
    "WBW_ANTEIL",
    "NOTE",
    "VERTEILUNG_WBW",
    "VERTEILUNG_MENGE",
    "MENGE_BEWERTET",
    "MENGE_GESAMT",
    "ERNEUERUNGSBEDARF_MENGE",
    "ERNEUERUNGSBEDARF_MRD",
    "NACHHOLBEDARF_MRD",
]
ConditionValueStatus = Literal["UNGEPRUEFT", "GEPRUEFT"]
ConditionReportStatus = Literal["ENTWURF", "FREIGEGEBEN"]


class ConditionAssetClassSchema(BaseModel):
    key: str
    domain: ConditionDomain
    trade: Optional[str] = None
    name: str
    unit: Optional[str] = None
    sort_order: int
    description: Optional[str] = None


class ConditionReportSchema(BaseModel):
    id: int
    year: int
    title: Optional[str] = None
    source_url: Optional[str] = None
    published_on: Optional[date] = None
    price_basis: Optional[str] = None
    note: Optional[str] = None
    status: ConditionReportStatus
    has_pdf: bool
    values_total: int
    values_unchecked: int
    accepted_mismatches: list[dict] = Field(default_factory=list)
    created_at: datetime
    released_at: Optional[datetime] = None
    released_by: Optional[str] = None


class ConditionPublicReport(BaseModel):
    year: int
    title: Optional[str] = None
    source_url: Optional[str] = None
    published_on: Optional[date] = None
    price_basis: Optional[str] = None
    released_at: Optional[datetime] = None


class ConditionValueSchema(BaseModel):
    id: int
    domain: ConditionDomain
    scope: ConditionScope
    region: Optional[str] = None
    class_key: Optional[str] = None
    metric: ConditionMetric
    grade: Optional[int] = None
    reference_year: int
    value: float
    source_page: Optional[int] = None
    source_ref: Optional[str] = None
    status: ConditionValueStatus


class ConditionSeriesValue(ConditionValueSchema):
    report_year: int


class ConditionPublicYear(BaseModel):
    """Everything /netzzustand needs for one year."""

    report: ConditionPublicReport
    classes: list[ConditionAssetClassSchema]
    values: list[ConditionValueSchema]


class ConditionReportCreate(BaseModel):
    year: int = Field(..., ge=2015, le=2100)
    title: Optional[str] = None
    source_url: Optional[str] = None
    published_on: Optional[date] = None
    price_basis: Optional[str] = None
    note: Optional[str] = None


class ConditionValueCorrection(BaseModel):
    value: float


class ConditionValueCorrectionResult(BaseModel):
    value: ConditionValueSchema
    warnings: list[str]


class ConditionTableErrors(BaseModel):
    table: str
    errors: list[str]


class ConditionCheckResult(BaseModel):
    year: int
    status: ConditionReportStatus
    values: int
    unchecked: int
    errors: list[ConditionTableErrors]
    gaps: list[str]
    accepted_mismatches: list[dict] = Field(default_factory=list)


class ConditionReleaseResult(BaseModel):
    released: int
