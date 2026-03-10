from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from dashboard_backend.models.haushalt.budget_change_log import BudgetChangeLog, BudgetChangeLogEntry
from dashboard_backend.models.haushalt.budget_titel_entry import BudgetTitelEntry
from dashboard_backend.models.haushalt.finve_change_log import FinveChangeLog, FinveChangeLogEntry
from dashboard_backend.models.haushalt.haushalt_titel import HaushaltTitel
from dashboard_backend.models.haushalt.haushalts_parse_result import HaushaltsParseResult
from dashboard_backend.models.haushalt.unmatched_budget_row import UnmatchedBudgetRow
from dashboard_backend.models.projects.budget import Budget
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.schemas.haushalt_import import (
    ProposedBudget,
    ProposedFinve,
    TitelEntryProposed,
    UnmatchedBudgetRowSchema,
)

if TYPE_CHECKING:
    from dashboard_backend.models.users import User


# ---------------------------------------------------------------------------
# HaushaltTitel
# ---------------------------------------------------------------------------

def get_or_create_haushalt_titel(
    db: Session,
    titel_key: str,
    kapitel: str,
    titel_nr: str,
    label: str,
    is_nachrichtlich: bool = False,
) -> tuple[HaushaltTitel, bool]:
    """Return an existing HaushaltTitel or create a new one.

    Returns (instance, created) where created=True means a new row was inserted.
    """
    existing = db.query(HaushaltTitel).filter(HaushaltTitel.titel_key == titel_key).first()
    if existing:
        return existing, False

    titel = HaushaltTitel(
        titel_key=titel_key,
        kapitel=kapitel,
        titel_nr=titel_nr,
        label=label,
        is_nachrichtlich=is_nachrichtlich,
    )
    db.add(titel)
    db.flush()
    return titel, True


# ---------------------------------------------------------------------------
# HaushaltsParseResult
# ---------------------------------------------------------------------------

def save_parse_result(
    db: Session,
    year: int,
    filename: str,
    user: "User | None",
    status: str,
    result_json: dict | None,
    error: str | None,
) -> HaushaltsParseResult:
    """Persist a new HaushaltsParseResult row and flush it to get an ID."""
    record = HaushaltsParseResult(
        haushalt_year=year,
        pdf_filename=filename,
        parsed_by_user_id=user.id if user else None,
        username_snapshot=user.username if user else None,
        status=status,
        result_json=result_json,
        error_message=error,
    )
    db.add(record)
    db.flush()
    return record


def get_parse_result(db: Session, parse_result_id: int) -> HaushaltsParseResult | None:
    return db.query(HaushaltsParseResult).filter(HaushaltsParseResult.id == parse_result_id).first()


def list_parse_results(db: Session) -> list[HaushaltsParseResult]:
    return (
        db.query(HaushaltsParseResult)
        .order_by(HaushaltsParseResult.parsed_at.desc())
        .all()
    )


def delete_parse_result(db: Session, parse_result_id: int) -> bool:
    """Delete a parse result.

    If it was already confirmed, also removes all Budget rows (and their
    BudgetTitelEntry children via CASCADE) and BudgetChangeLog entries for
    that haushalt_year so the year can be re-imported cleanly.

    Returns True when something was deleted, False when not found.
    """
    record = get_parse_result(db, parse_result_id)
    if not record:
        return False

    if record.confirmed_at is not None:
        year = record.haushalt_year
        # Remove change-log entries first (no cascade from Budget side)
        db.query(BudgetChangeLog).filter(BudgetChangeLog.haushalt_year == year).delete(
            synchronize_session=False
        )
        # Delete budgets for this year – CASCADE removes BudgetTitelEntry rows
        db.query(Budget).filter(Budget.budget_year == year).delete(
            synchronize_session=False
        )

    db.delete(record)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Finve upsert
# ---------------------------------------------------------------------------

_FINVE_TRACKED_FIELDS = ("name", "starting_year", "cost_estimate_original", "is_sammel_finve")


def upsert_finve(
    db: Session,
    proposed: ProposedFinve,
    user: "User | None",
    haushalt_year: int,
) -> tuple[Finve, bool, FinveChangeLog | None]:
    """Insert or update a Finve record.

    Returns (finve, created, changelog).
    """
    existing = db.query(Finve).filter(Finve.id == proposed.id).first()

    if existing is None:
        finve = Finve(
            id=proposed.id,
            name=proposed.name,
            starting_year=proposed.starting_year,
            cost_estimate_original=proposed.cost_estimate_original,
            is_sammel_finve=proposed.is_sammel_finve,
        )
        db.add(finve)
        db.flush()

        changelog = FinveChangeLog(
            finve_id=finve.id,
            haushalt_year=haushalt_year,
            username_snapshot=user.username if user else None,
            timestamp=datetime.utcnow(),
            action="CREATE",
            entries=[
                FinveChangeLogEntry(field_name=f, old_value=None, new_value=json.dumps(getattr(finve, f)))
                for f in _FINVE_TRACKED_FIELDS
                if getattr(finve, f) is not None
            ],
        )
        db.add(changelog)
        return finve, True, changelog

    # Update existing finve, track only changed fields
    update_data = proposed.model_dump(exclude={"id"})
    entries = []
    for field, new_val in update_data.items():
        if field not in _FINVE_TRACKED_FIELDS:
            continue
        old_val = getattr(existing, field)
        if old_val == new_val:
            continue
        entries.append(
            FinveChangeLogEntry(
                field_name=field,
                old_value=json.dumps(old_val) if old_val is not None else None,
                new_value=json.dumps(new_val) if new_val is not None else None,
            )
        )
        setattr(existing, field, new_val)

    changelog = None
    if entries:
        changelog = FinveChangeLog(
            finve_id=existing.id,
            haushalt_year=haushalt_year,
            username_snapshot=user.username if user else None,
            timestamp=datetime.utcnow(),
            action="UPDATE",
            entries=entries,
        )
        db.add(changelog)

    return existing, False, changelog


# ---------------------------------------------------------------------------
# Budget upsert
# ---------------------------------------------------------------------------

_BUDGET_TRACKED_FIELDS = (
    "lfd_nr",
    "bedarfsplan_number",
    "cost_estimate_original",
    "cost_estimate_last_year",
    "cost_estimate_actual",
    "delta_previous_year",
    "delta_previous_year_relativ",
    "delta_previous_year_reasons",
    "spent_two_years_previous",
    "allowed_previous_year",
    "spending_residues",
    "year_planned",
    "next_years",
    "sammel_finve",
)


def upsert_budget(
    db: Session,
    proposed: ProposedBudget,
    user: "User | None",
    haushalt_year: int,
) -> tuple[Budget, bool, BudgetChangeLog | None]:
    """Insert or update a Budget record (unique on budget_year + fin_ve).

    Returns (budget, created, changelog).
    """
    existing = (
        db.query(Budget)
        .filter(Budget.budget_year == proposed.budget_year, Budget.fin_ve == proposed.fin_ve)
        .first()
    )

    if existing is None:
        budget = Budget(
            budget_year=proposed.budget_year,
            fin_ve=proposed.fin_ve,
            lfd_nr=proposed.lfd_nr,
            bedarfsplan_number=proposed.bedarfsplan_number,
            cost_estimate_original=proposed.cost_estimate_original,
            cost_estimate_last_year=proposed.cost_estimate_last_year,
            cost_estimate_actual=proposed.cost_estimate_actual,
            delta_previous_year=proposed.delta_previous_year,
            delta_previous_year_relativ=proposed.delta_previous_year_relativ,
            delta_previous_year_reasons=proposed.delta_previous_year_reasons,
            spent_two_years_previous=proposed.spent_two_years_previous,
            allowed_previous_year=proposed.allowed_previous_year,
            spending_residues=proposed.spending_residues,
            year_planned=proposed.year_planned,
            next_years=proposed.next_years,
            sammel_finve=proposed.sammel_finve,
        )
        db.add(budget)
        db.flush()

        changelog = BudgetChangeLog(
            budget_id=budget.id,
            haushalt_year=haushalt_year,
            username_snapshot=user.username if user else None,
            timestamp=datetime.utcnow(),
            action="CREATE",
            entries=[
                BudgetChangeLogEntry(field_name=f, old_value=None, new_value=json.dumps(getattr(budget, f)))
                for f in _BUDGET_TRACKED_FIELDS
                if getattr(budget, f) is not None
            ],
        )
        db.add(changelog)
        return budget, True, changelog

    # Update existing budget
    update_data = proposed.model_dump(exclude={"budget_year", "fin_ve"})
    entries = []
    for field, new_val in update_data.items():
        if field not in _BUDGET_TRACKED_FIELDS:
            continue
        old_val = getattr(existing, field)
        if old_val == new_val:
            continue
        entries.append(
            BudgetChangeLogEntry(
                field_name=field,
                old_value=json.dumps(old_val) if old_val is not None else None,
                new_value=json.dumps(new_val) if new_val is not None else None,
            )
        )
        setattr(existing, field, new_val)

    changelog = None
    if entries:
        changelog = BudgetChangeLog(
            budget_id=existing.id,
            haushalt_year=haushalt_year,
            username_snapshot=user.username if user else None,
            timestamp=datetime.utcnow(),
            action="UPDATE",
            entries=entries,
        )
        db.add(changelog)

    return existing, False, changelog


# ---------------------------------------------------------------------------
# BudgetTitelEntry upsert
# ---------------------------------------------------------------------------

def upsert_budget_titel_entries(
    db: Session,
    budget_id: int,
    titel_entries: list[TitelEntryProposed],
) -> None:
    """Insert or update BudgetTitelEntry rows for the given budget."""
    for entry_data in titel_entries:
        titel, _ = get_or_create_haushalt_titel(
            db,
            titel_key=entry_data.titel_key,
            kapitel=entry_data.kapitel,
            titel_nr=entry_data.titel_nr,
            label=entry_data.label,
            is_nachrichtlich=entry_data.is_nachrichtlich,
        )

        existing = (
            db.query(BudgetTitelEntry)
            .filter(BudgetTitelEntry.budget_id == budget_id, BudgetTitelEntry.titel_id == titel.id)
            .first()
        )
        if existing:
            existing.cost_estimate_last_year = entry_data.cost_estimate_last_year
            existing.cost_estimate_aktuell = entry_data.cost_estimate_aktuell
            existing.verausgabt_bis = entry_data.verausgabt_bis
            existing.bewilligt = entry_data.bewilligt
            existing.ausgabereste_transferred = entry_data.ausgabereste_transferred
            existing.veranschlagt = entry_data.veranschlagt
            existing.vorhalten_future = entry_data.vorhalten_future
        else:
            db.add(
                BudgetTitelEntry(
                    budget_id=budget_id,
                    titel_id=titel.id,
                    cost_estimate_last_year=entry_data.cost_estimate_last_year,
                    cost_estimate_aktuell=entry_data.cost_estimate_aktuell,
                    verausgabt_bis=entry_data.verausgabt_bis,
                    bewilligt=entry_data.bewilligt,
                    ausgabereste_transferred=entry_data.ausgabereste_transferred,
                    veranschlagt=entry_data.veranschlagt,
                    vorhalten_future=entry_data.vorhalten_future,
                )
            )


# ---------------------------------------------------------------------------
# UnmatchedBudgetRow
# ---------------------------------------------------------------------------

def save_unmatched_rows(
    db: Session,
    rows: list[dict],
    year: int,
) -> int:
    """Persist a list of unmatched raw rows. Returns the count saved."""
    for raw in rows:
        db.add(
            UnmatchedBudgetRow(
                haushalt_year=year,
                raw_finve_number=str(raw.get("raw_finve_number", "")),
                raw_name=str(raw.get("raw_name", "")),
                raw_data=raw,
            )
        )
    return len(rows)


def list_unmatched_rows(db: Session, resolved: bool | None = None) -> list[UnmatchedBudgetRow]:
    q = db.query(UnmatchedBudgetRow)
    if resolved is not None:
        q = q.filter(UnmatchedBudgetRow.resolved == resolved)
    return q.order_by(UnmatchedBudgetRow.haushalt_year.desc()).all()


def get_unmatched_row(db: Session, row_id: int) -> UnmatchedBudgetRow | None:
    return db.query(UnmatchedBudgetRow).filter(UnmatchedBudgetRow.id == row_id).first()


def resolve_unmatched_row(
    db: Session,
    row_id: int,
    finve_id: int,
    user: "User | None",
) -> UnmatchedBudgetRow | None:
    """Mark an unmatched row as resolved and link it to the given Finve."""
    row = get_unmatched_row(db, row_id)
    if row is None:
        return None
    row.resolved = True
    row.resolved_finve_id = finve_id
    row.resolved_at = datetime.utcnow()
    row.resolved_by_snapshot = user.username if user else None
    db.flush()
    return row
