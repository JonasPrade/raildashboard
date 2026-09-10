"""Schemas for the constituency / members-of-parliament feature."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CommitteeRoleSchema(BaseModel):
    """Membership in one of the two committees this feature tracks."""

    key: str  # "verkehr" | "haushalt"
    label: str
    role: str | None = None
    role_label: str | None = None


class MandateSchema(BaseModel):
    """One member of parliament, seen through their mandate.

    ``is_direct_mandate`` and "ran here, entered over the list" are two different
    degrees of responsibility and stay apart all the way into the UI.
    """

    mandate_id: int
    politician_id: int
    name: str
    first_name: str | None = None
    last_name: str | None = None
    fraction: str | None = None
    party: str | None = None
    mandate_type: str | None = None
    is_direct_mandate: bool
    profile_url: str | None = None
    info: str | None = None
    committees: list[CommitteeRoleSchema] = []


class ConstituencySummarySchema(BaseModel):
    id: int
    number: int
    name: str
    state: str | None = None


class ProjectConstituencySchema(ConstituencySummarySchema):
    """A constituency touched by one project, with its weight."""

    length_km: float
    share: float
    overlap_kind: str  # "line" | "point"
    direct_mandates: list[MandateSchema] = []
    list_mandates: list[MandateSchema] = []
    # "No direct mandate held" is a statement, not a gap: since the electoral
    # reform it applies to 27 of the 299 constituencies.
    has_direct_mandate: bool
    has_any_mandate: bool


class ImportRunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    stats: Any = None
    error: str | None = None


class ProjectConstituenciesSchema(BaseModel):
    project_id: int
    has_geometry: bool
    constituencies: list[ProjectConstituencySchema] = []
    last_import: ImportRunSchema | None = None


class PoliticianProjectSchema(BaseModel):
    project_id: int
    name: str
    project_number: str | None = None
    length_km: float
    share: float
    overlap_kind: str
    constituency_number: int
    constituency_name: str


class PoliticianListItemSchema(BaseModel):
    politician_id: int
    mandate_id: int
    name: str
    first_name: str | None = None
    last_name: str | None = None
    fraction: str | None = None
    party: str | None = None
    mandate_type: str | None = None
    is_direct_mandate: bool
    profile_url: str | None = None
    constituency: ConstituencySummarySchema | None = None
    committees: list[CommitteeRoleSchema] = []
    project_count: int = 0


class PoliticianDetailSchema(PoliticianListItemSchema):
    projects: list[PoliticianProjectSchema] = []


class ConstituencyProjectSchema(BaseModel):
    project_id: int
    name: str
    project_number: str | None = None
    length_km: float
    share: float
    overlap_kind: str


class ConstituencyListItemSchema(ConstituencySummarySchema):
    project_count: int = 0
    mandate_count: int = 0
    has_direct_mandate: bool = False
    has_geometry: bool = False


class ConstituencyDetailSchema(ConstituencySummarySchema):
    projects: list[ConstituencyProjectSchema] = []
    direct_mandates: list[MandateSchema] = []
    list_mandates: list[MandateSchema] = []
    has_direct_mandate: bool
    has_any_mandate: bool


class ParliamentPeriodSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: int
    label: str
    parliament_label: str | None = None


class CommitteeSchema(BaseModel):
    key: str
    label: str
    member_count: int = 0


class ParliamentStatusSchema(BaseModel):
    """Everything the UI needs to say how current the data is."""

    period: ParliamentPeriodSchema | None = None
    last_politician_import: ImportRunSchema | None = None
    last_constituency_import: ImportRunSchema | None = None
    last_link_run: ImportRunSchema | None = None
    is_stale: bool = False
    stale_after_days: int = 60
    counts: dict[str, int] = {}
    coverage: dict[str, int] = {}
    fractions: list[str] = []
    committees: list[CommitteeSchema] = []
    geometry_attribution: str | None = None
