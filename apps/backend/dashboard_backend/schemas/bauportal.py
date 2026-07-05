"""Schemas for the DB-Bauportal importer (#47)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BauportalEntrySchema(BaseModel):
    """One fetched Bauportal record with its suggested / confirmed match."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    bauportal_id: int
    parent_bauportal_id: int | None = None
    shorttitle: str
    status_raw: str | None = None
    # MainPhase the status maps to (None for mixed / umbrella entries).
    mapped_phase: str | None = None
    projecttime_raw: str | None = None
    url: str | None = None
    lat: float | None = None
    lng: float | None = None
    fetched_at: datetime | None = None
    suggested_project_id: int | None = None
    suggested_project_name: str | None = None
    project_id: int | None = None
    project_name: str | None = None
    confirmed: bool = False


class BauportalImportSummary(BaseModel):
    fetched: int
    created: int
    updated: int
    skipped: int


class BauportalUpdateInput(BaseModel):
    """Set the assigned project and/or confirm the match for one entry.

    Both fields are optional; ``project_id`` may be ``null`` to clear the match.
    """

    project_id: int | None = None
    confirmed: bool | None = None


class BauportalConfirmSummary(BaseModel):
    """Result of confirming all assigned entries at once."""

    confirmed: int
