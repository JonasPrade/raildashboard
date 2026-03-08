from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Titel sub-entry (per-Titel breakdown within a Budget row)
# ---------------------------------------------------------------------------

class TitelEntryProposed(BaseModel):
    """Proposed values for a single BudgetTitelEntry extracted from the PDF."""

    titel_key: str
    kapitel: str
    titel_nr: str
    label: str
    is_nachrichtlich: bool = False
    cost_estimate_last_year: Optional[int] = None
    cost_estimate_aktuell: Optional[int] = None
    verausgabt_bis: Optional[int] = None
    bewilligt: Optional[int] = None
    ausgabereste_transferred: Optional[int] = None
    veranschlagt: Optional[int] = None
    vorhalten_future: Optional[int] = None


# ---------------------------------------------------------------------------
# Proposed values for a single row extracted from the PDF
# ---------------------------------------------------------------------------

class ProposedFinve(BaseModel):
    """Proposed Finve values from the PDF parser."""

    id: int  # FinVe-Nummer aus Spalte 2
    name: str
    starting_year: Optional[int] = None
    cost_estimate_original: Optional[int] = None


class ProposedBudget(BaseModel):
    """Proposed Budget values from the PDF parser."""

    budget_year: int
    lfd_nr: Optional[str] = None
    fin_ve: int
    bedarfsplan_number: Optional[str] = None
    cost_estimate_original: Optional[int] = None
    cost_estimate_last_year: Optional[int] = None
    cost_estimate_actual: Optional[int] = None
    delta_previous_year: Optional[int] = None
    delta_previous_year_relativ: Optional[float] = None
    delta_previous_year_reasons: Optional[str] = None
    spent_two_years_previous: Optional[int] = None
    allowed_previous_year: Optional[int] = None
    spending_residues: Optional[int] = None
    year_planned: Optional[int] = None
    next_years: Optional[int] = None


# ---------------------------------------------------------------------------
# Single parse result row (one FinVe entry from the PDF)
# ---------------------------------------------------------------------------

class HaushaltsParseResultSchema(BaseModel):
    """One FinVe row as returned by the PDF parser task."""

    finve_number: int
    name: str
    status: str  # "new" | "update" | "unmatched"
    proposed_finve: Optional[ProposedFinve] = None
    proposed_budget: Optional[ProposedBudget] = None
    proposed_titel_entries: list[TitelEntryProposed] = []
    # Existing project IDs associated with this FinVe (for "update"); editable for "new"
    project_ids: list[int] = []
    # Automatically suggested project IDs (computed during parse, read-only hint for UI)
    suggested_project_ids: list[int] = []


# ---------------------------------------------------------------------------
# Full task result (stored in HaushaltsParseResult.result_json)
# ---------------------------------------------------------------------------

class HaushaltsParseTaskResult(BaseModel):
    """Complete result returned by the parse_haushalt_pdf Celery task."""

    year: int
    rows: list[HaushaltsParseResultSchema] = []
    unmatched_rows: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Confirm request / response
# ---------------------------------------------------------------------------

class HaushaltsConfirmRowInput(BaseModel):
    """One row submitted in the confirm request (project_ids may be adjusted by user)."""

    finve_number: int
    status: str
    proposed_finve: Optional[ProposedFinve] = None
    proposed_budget: Optional[ProposedBudget] = None
    proposed_titel_entries: list[TitelEntryProposed] = []
    project_ids: list[int] = []


class HaushaltsConfirmRequest(BaseModel):
    parse_result_id: int
    rows: list[HaushaltsConfirmRowInput] = []
    unmatched_action: str = "save"  # "save" | "discard"


class HaushaltsConfirmResponse(BaseModel):
    finves_created: int
    finves_updated: int
    budgets_created: int
    budgets_updated: int
    unmatched_saved: int


# ---------------------------------------------------------------------------
# Unmatched budget row schemas
# ---------------------------------------------------------------------------

class UnmatchedBudgetRowSchema(BaseModel):
    id: int
    haushalt_year: int
    raw_finve_number: str
    raw_name: str
    raw_data: Optional[dict[str, Any]] = None
    resolved: bool
    resolved_finve_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolved_by_snapshot: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UnmatchedBudgetRowResolveRequest(BaseModel):
    finve_id: int


# ---------------------------------------------------------------------------
# ParseResultPublicSchema — metadata for GET list / detail endpoints
# ---------------------------------------------------------------------------

class ParseResultPublicSchema(BaseModel):
    id: int
    haushalt_year: int
    pdf_filename: str
    parsed_at: datetime
    username_snapshot: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    confirmed_by_snapshot: Optional[str] = None
    result_json: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
