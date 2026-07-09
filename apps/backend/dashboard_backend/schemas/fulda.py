"""Schemas for the Fulda-Runde importer (#46)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class FuldaEntrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    announcement_year: int
    source_label: str | None = None
    document_date: date | None = None
    raw_name: str
    abschnitt: str | None = None
    category: str | None = None
    announced_phase: str | None = None
    expected_date: date | None = None
    # m:n project assignment (pre-filled with fuzzy suggestions at parse time).
    project_ids: list[int] = []
    project_names: list[str] = []
    confirmed: bool = False
    created_at: datetime | None = None
    username_snapshot: str | None = None


class FuldaConfirmSummary(BaseModel):
    """Result of confirming a whole year at once."""

    confirmed: int


class FuldaYearSummary(BaseModel):
    """One row of the year-overview table (entry counts + provenance per year)."""

    announcement_year: int
    total: int
    confirmed: int
    source_label: str | None = None
    document_date: date | None = None


class FuldaUpdateInput(BaseModel):
    """Patch a Fulda announcement; ``project_ids`` replaces the whole assignment."""

    announcement_year: int | None = None
    source_label: str | None = None
    document_date: date | None = None
    raw_name: str | None = None
    abschnitt: str | None = None
    category: str | None = None
    announced_phase: str | None = None
    expected_date: date | None = None
    project_ids: list[int] | None = None
    confirmed: bool | None = None
