"""Schemas for the Medien/Presse importer (#48)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MediaExtractInput(BaseModel):
    """Submit a press article by URL and/or pasted text for extraction."""

    url: str | None = None
    text: str | None = None


class MediaEntrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str | None = None
    publication: str | None = None
    published_date: date | None = None
    raw_text: str | None = None
    quote: str | None = None
    # MainPhase value the report asserts (editor-confirmable), None until set.
    asserted_phase: str | None = None
    observed_date: date | None = None
    suggested_project_id: int | None = None
    suggested_project_name: str | None = None
    project_id: int | None = None
    project_name: str | None = None
    confirmed: bool = False
    created_at: datetime | None = None
    username_snapshot: str | None = None


class MediaUpdateInput(BaseModel):
    """Patch a media report. Only provided fields are applied; ``project_id``
    may be set to null to clear the match."""

    url: str | None = None
    publication: str | None = None
    published_date: date | None = None
    asserted_phase: str | None = None
    observed_date: date | None = None
    quote: str | None = None
    project_id: int | None = None
    confirmed: bool | None = None
