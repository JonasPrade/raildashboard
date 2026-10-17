"""Schemas for the Fulda-Runde importer (feature-fulda-import.md)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

AnswerStatusLiteral = Literal["VOLLSTAENDIG", "TEILWEISE", "OHNE_ERGEBNIS"]
AttributedToLiteral = Literal["BMV", "DB"]
StatementKindLiteral = Literal["IST", "OHNE_FOLGEPHASE", "PROGNOSE", "NEUAUFNAHME"]


class FuldaDocumentSchema(BaseModel):
    """One evaluated answer of the Federal Government, with entry counters."""

    id: int
    year: int
    drucksache: str
    title: str | None = None
    document_date: date
    dip_url: str | None = None
    answer_status: AnswerStatusLiteral
    note: str | None = None
    total: int = 0
    assigned: int = 0
    confirmed: int = 0
    created_at: datetime | None = None
    username_snapshot: str | None = None


class FuldaEntrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int | None = None
    announcement_year: int
    drucksache: str | None = None
    document_date: date | None = None
    raw_name: str
    abschnitt: str | None = None
    category: str | None = None
    # Derived from the category (see FuldaCategorySchema).
    statement_kind: StatementKindLiteral | None = None
    phase: str | None = None
    expected_date: date | None = None
    question_ref: str | None = None
    page: int | None = None
    raw_text: str | None = None
    attributed_to: AttributedToLiteral | None = None
    assignment_note: str | None = None
    project_ids: list[int] = []
    project_names: list[str] = []
    confirmed: bool = False
    created_at: datetime | None = None
    username_snapshot: str | None = None


class FuldaCategorySchema(BaseModel):
    key: str
    label: str
    statement_kind: StatementKindLiteral
    # Phase asserted (IST/OHNE_FOLGEPHASE) or expected (PROGNOSE/NEUAUFNAHME);
    # null = hint only, no observation.
    phase: str | None = None


class FuldaConfirmSummary(BaseModel):
    """Result of confirming a whole year at once."""

    confirmed: int


class FuldaYearSummary(BaseModel):
    """One row of the year-overview table (entry counts + the year's documents)."""

    announcement_year: int
    total: int
    confirmed: int
    documents: list[FuldaDocumentSchema] = []


class FuldaUpdateInput(BaseModel):
    """Patch a Fulda announcement; ``project_ids`` replaces the whole assignment."""

    raw_name: str | None = None
    abschnitt: str | None = None
    category: str | None = None
    expected_date: date | None = None
    question_ref: str | None = None
    page: int | None = None
    raw_text: str | None = None
    attributed_to: AttributedToLiteral | None = None
    assignment_note: str | None = None
    project_ids: list[int] | None = None
    confirmed: bool | None = None
