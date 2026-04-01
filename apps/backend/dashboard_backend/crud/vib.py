from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, joinedload

from dashboard_backend.models.vib.vib_draft_report import VibDraftReport
from dashboard_backend.models.vib.vib_entry import VibEntry
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry
from dashboard_backend.models.vib.vib_report import VibReport
from dashboard_backend.schemas.vib import (
    VibConfirmEntryInput,
    VibConfirmResponse,
)

if TYPE_CHECKING:
    from dashboard_backend.models.users import User


# ---------------------------------------------------------------------------
# VibDraftReport (raw parse result persisted before user confirmation)
# ---------------------------------------------------------------------------

def save_draft_report(
    db: Session,
    task_id: str,
    year: int,
    raw_result_json: str,
    user: "User | None",
) -> VibDraftReport:
    """Upsert the raw parse result JSON for a given task_id.

    If a draft for this task_id already exists (e.g. task retried) it is
    replaced so the latest result is always current.
    """
    existing = db.query(VibDraftReport).filter(VibDraftReport.task_id == task_id).first()
    if existing:
        existing.raw_result_json = raw_result_json
        existing.year = year
        db.flush()
        return existing

    draft = VibDraftReport(
        task_id=task_id,
        year=year,
        raw_result_json=raw_result_json,
        created_by_user_id=user.id if user else None,
    )
    db.add(draft)
    db.flush()
    return draft


def get_draft_by_task_id(db: Session, task_id: str) -> VibDraftReport | None:
    return db.query(VibDraftReport).filter(VibDraftReport.task_id == task_id).first()


def delete_draft(db: Session, task_id: str) -> None:
    db.query(VibDraftReport).filter(VibDraftReport.task_id == task_id).delete()


def update_draft_ai_result(db: Session, task_id: str, raw_result_json: str) -> bool:
    """Replace the raw_result_json of an existing draft. Returns False if not found."""
    draft = get_draft_by_task_id(db, task_id)
    if draft is None:
        return False
    draft.raw_result_json = raw_result_json
    db.flush()
    return True


# ---------------------------------------------------------------------------
# VibReport queries
# ---------------------------------------------------------------------------

def get_report_by_year(db: Session, year: int) -> VibReport | None:
    return db.query(VibReport).filter(VibReport.year == year).first()


def get_report(db: Session, report_id: int) -> VibReport | None:
    return db.query(VibReport).filter(VibReport.id == report_id).first()


def list_reports(db: Session) -> list[VibReport]:
    return db.query(VibReport).order_by(VibReport.year.desc()).all()


def delete_report(db: Session, report_id: int) -> bool:
    """Delete a VibReport and all its entries (cascade). Returns True when deleted."""
    report = get_report(db, report_id)
    if not report:
        return False
    db.delete(report)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Confirm: create VibReport + VibEntry + VibPfaEntry rows
# ---------------------------------------------------------------------------

def create_vib_report_with_entries(
    db: Session,
    year: int,
    drucksache_nr: str | None,
    report_date_str: str | None,
    entries: list[VibConfirmEntryInput],
    user: "User | None",
) -> VibConfirmResponse:
    """Write a confirmed VIB import to the database.

    Creates one VibReport and one VibEntry per input entry, together with all
    VibPfaEntry child rows.  The caller must call db.commit() after this
    function returns.
    """
    parsed_date: date | None = None
    if report_date_str:
        try:
            parsed_date = date.fromisoformat(report_date_str)
        except ValueError:
            parsed_date = None

    report = VibReport(
        year=year,
        drucksache_nr=drucksache_nr,
        report_date=parsed_date,
        imported_at=datetime.utcnow(),
        imported_by_user_id=user.id if user else None,
    )
    db.add(report)
    db.flush()  # get report.id

    entries_created = 0
    pfa_entries_created = 0

    for entry_data in entries:
        vib_entry = VibEntry(
            vib_report_id=report.id,
            project_id=entry_data.project_id,
            vib_section=entry_data.vib_section,
            vib_lfd_nr=entry_data.vib_lfd_nr,
            vib_name_raw=entry_data.vib_name_raw,
            category=entry_data.category,
            raw_text=entry_data.raw_text,
            bauaktivitaeten=entry_data.bauaktivitaeten,
            teilinbetriebnahmen=entry_data.teilinbetriebnahmen,
            verkehrliche_zielsetzung=entry_data.verkehrliche_zielsetzung,
            durchgefuehrte_massnahmen=entry_data.durchgefuehrte_massnahmen,
            noch_umzusetzende_massnahmen=entry_data.noch_umzusetzende_massnahmen,
            strecklaenge_km=entry_data.strecklaenge_km,
            gesamtkosten_mio_eur=entry_data.gesamtkosten_mio_eur,
            entwurfsgeschwindigkeit=entry_data.entwurfsgeschwindigkeit,
            planungsstand=entry_data.planungsstand,
            project_status=entry_data.project_status,
        )
        db.add(vib_entry)
        db.flush()  # get vib_entry.id
        entries_created += 1

        for pfa_data in entry_data.pfa_entries:
            db.add(VibPfaEntry(
                vib_entry_id=vib_entry.id,
                abschnitt_label=pfa_data.abschnitt_label,
                nr_pfa=pfa_data.nr_pfa,
                oertlichkeit=pfa_data.oertlichkeit,
                entwurfsplanung=pfa_data.entwurfsplanung,
                abschluss_finve=pfa_data.abschluss_finve,
                datum_pfb=pfa_data.datum_pfb,
                baubeginn=pfa_data.baubeginn,
                inbetriebnahme=pfa_data.inbetriebnahme,
            ))
            pfa_entries_created += 1

    return VibConfirmResponse(
        report_id=report.id,
        entries_created=entries_created,
        pfa_entries_created=pfa_entries_created,
    )


# ---------------------------------------------------------------------------
# Project-detail view
# ---------------------------------------------------------------------------

def get_vib_entries_for_project(db: Session, project_id: int) -> list[VibEntry]:
    """Return all VibEntry rows linked to a project, newest report year first."""
    return (
        db.query(VibEntry)
        .filter(VibEntry.project_id == project_id)
        .join(VibEntry.report)
        .order_by(VibReport.year.desc())
        .options(
            joinedload(VibEntry.pfa_entries),
            joinedload(VibEntry.report),
        )
        .all()
    )
