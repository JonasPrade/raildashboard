from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, joinedload

from dashboard_backend.models.vib.vib_draft_report import VibDraftReport
from dashboard_backend.models.vib.vib_entry import VibEntry
from dashboard_backend.models.vib.vib_entry_project import vib_entry_project
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry
from dashboard_backend.models.vib.vib_report import VibReport
from dashboard_backend.schemas.vib import (
    VibConfirmEntryInput,
    VibConfirmResponse,
    VibEntryUpdateSchema,
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
    ocr_raw_text: str | None = None,
    ocr_status: str | None = None,
    ocr_model: str | None = None,
    ocr_images_json: str | None = None,
) -> VibDraftReport:
    """Upsert the raw parse result JSON for a given task_id.

    If a draft for this task_id already exists (e.g. task retried) it is
    replaced so the latest result is always current.
    """
    existing = db.query(VibDraftReport).filter(VibDraftReport.task_id == task_id).first()
    if existing:
        existing.raw_result_json = raw_result_json
        existing.year = year
        existing.ocr_raw_text = ocr_raw_text
        existing.ocr_status = ocr_status
        existing.ocr_model = ocr_model
        existing.ocr_images_json = ocr_images_json
        db.flush()
        return existing

    draft = VibDraftReport(
        task_id=task_id,
        year=year,
        raw_result_json=raw_result_json,
        created_by_user_id=user.id if user else None,
        ocr_raw_text=ocr_raw_text,
        ocr_status=ocr_status,
        ocr_model=ocr_model,
        ocr_images_json=ocr_images_json,
    )
    db.add(draft)
    db.flush()
    return draft


def get_draft_by_task_id(db: Session, task_id: str) -> VibDraftReport | None:
    return db.query(VibDraftReport).filter(VibDraftReport.task_id == task_id).first()


def list_drafts(db: Session) -> list[VibDraftReport]:
    """Return all drafts ordered by creation date, newest first."""
    return db.query(VibDraftReport).order_by(VibDraftReport.created_at.desc()).all()


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
        imported_at=datetime.now(timezone.utc),
        imported_by_user_id=user.id if user else None,
    )
    db.add(report)
    db.flush()  # get report.id

    entries_created = 0
    pfa_entries_created = 0

    for entry_data in entries:
        vib_entry = VibEntry(
            vib_report_id=report.id,
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
            sonstiges=entry_data.sonstiges,
            strecklaenge_km=entry_data.strecklaenge_km,
            gesamtkosten_mio_eur=entry_data.gesamtkosten_mio_eur,
            entwurfsgeschwindigkeit=entry_data.entwurfsgeschwindigkeit,
            planungsstand=entry_data.planungsstand,
            status_planung=entry_data.status_planung,
            status_bau=entry_data.status_bau,
            status_abgeschlossen=entry_data.status_abgeschlossen,
        )
        db.add(vib_entry)
        db.flush()  # get vib_entry.id

        if entry_data.project_ids:
            unique_pids = list(dict.fromkeys(entry_data.project_ids))
            db.execute(
                vib_entry_project.insert(),
                [{"vib_entry_id": vib_entry.id, "project_id": pid} for pid in unique_pids],
            )

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
        .join(vib_entry_project, vib_entry_project.c.vib_entry_id == VibEntry.id)
        .filter(vib_entry_project.c.project_id == project_id)
        .join(VibEntry.report)
        .order_by(VibReport.year.desc())
        .options(
            joinedload(VibEntry.pfa_entries),
            joinedload(VibEntry.projects),
            joinedload(VibEntry.report),
        )
        .all()
    )


# ---------------------------------------------------------------------------
# VibEntry PATCH
# ---------------------------------------------------------------------------

_SCALAR_FIELDS = [
    "vib_name_raw", "category", "verkehrliche_zielsetzung",
    "durchgefuehrte_massnahmen", "noch_umzusetzende_massnahmen",
    "bauaktivitaeten", "teilinbetriebnahmen", "sonstiges", "raw_text",
    "strecklaenge_km", "gesamtkosten_mio_eur", "entwurfsgeschwindigkeit",
    "planungsstand", "status_planung", "status_bau", "status_abgeschlossen",
]


def get_vib_entry_full(db: Session, entry_id: int) -> VibEntry | None:
    """Load a VibEntry with pfa_entries, projects, and report eager-loaded."""
    return (
        db.query(VibEntry)
        .filter(VibEntry.id == entry_id)
        .options(
            joinedload(VibEntry.pfa_entries),
            joinedload(VibEntry.projects),
            joinedload(VibEntry.report),
        )
        .first()
    )


def update_vib_entry(db: Session, entry_id: int, data: VibEntryUpdateSchema) -> VibEntry | None:
    """Apply a partial update to a confirmed VibEntry.

    - Scalar fields: applied when non-None in data.
    - pfa_entries: if provided, all existing children are replaced.
    - project_ids: if provided, all existing project links are replaced.
    Returns the updated entry (relationships eager-loaded), or None if not found.
    """
    entry = get_vib_entry_full(db, entry_id)
    if entry is None:
        return None

    # Apply scalar fields
    for field in _SCALAR_FIELDS:
        value = getattr(data, field)
        if value is not None:
            setattr(entry, field, value)

    # Replace PFA children
    if data.pfa_entries is not None:
        entry.pfa_entries.clear()
        db.flush()
        for pfa_data in data.pfa_entries:
            entry.pfa_entries.append(VibPfaEntry(
                vib_entry_id=entry_id,
                abschnitt_label=pfa_data.abschnitt_label,
                nr_pfa=pfa_data.nr_pfa,
                oertlichkeit=pfa_data.oertlichkeit,
                entwurfsplanung=pfa_data.entwurfsplanung,
                abschluss_finve=pfa_data.abschluss_finve,
                datum_pfb=pfa_data.datum_pfb,
                baubeginn=pfa_data.baubeginn,
                inbetriebnahme=pfa_data.inbetriebnahme,
            ))

    # Replace project links
    if data.project_ids is not None:
        db.execute(
            vib_entry_project.delete().where(
                vib_entry_project.c.vib_entry_id == entry_id
            )
        )
        if data.project_ids:
            unique_pids = list(dict.fromkeys(data.project_ids))
            db.execute(
                vib_entry_project.insert(),
                [{"vib_entry_id": entry_id, "project_id": pid} for pid in unique_pids],
            )

    db.flush()
    db.expire(entry)
    return get_vib_entry_full(db, entry_id)
