"""Schemas for the Fulda-Runde importer (#46)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class FuldaEntrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_label: str | None = None
    document_date: date | None = None
    raw_name: str
    category: str | None = None
    announced_phase: str | None = None
    expected_date: date | None = None
    suggested_project_id: int | None = None
    suggested_project_name: str | None = None
    project_id: int | None = None
    project_name: str | None = None
    confirmed: bool = False
    created_at: datetime | None = None
    username_snapshot: str | None = None


class FuldaParseSummary(BaseModel):
    ocr_status: str
    created: int
    source_label: str | None = None


class FuldaUpdateInput(BaseModel):
    """Patch a Fulda announcement; ``project_id`` may be null to clear."""

    source_label: str | None = None
    document_date: date | None = None
    raw_name: str | None = None
    category: str | None = None
    announced_phase: str | None = None
    expected_date: date | None = None
    project_id: int | None = None
    confirmed: bool | None = None
