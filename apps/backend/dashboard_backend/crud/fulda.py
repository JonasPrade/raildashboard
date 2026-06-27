"""DB access for the Fulda-Runde importer (#46).

Parses an uploaded Kleine-Anfrage PDF (OCR + LLM) into per-(project, category)
draft rows with fuzzy match suggestions, lists them for review, and on confirm
re-materialises the affected project's derived FULDA_RUNDE observation. Rows are
editor-owned (editable / deletable).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from dashboard_backend.crud.projects.progress import recompute_progress
from dashboard_backend.models.projects.fulda_announcement import FuldaAnnouncement
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.users import User
from dashboard_backend.services.progress_dates import parse_flexible_date
from dashboard_backend.services.progress_materialization import fulda_category_to_phase
from dashboard_backend.tasks.fulda_extraction import (
    extract_fulda_announcements,
    ocr_fulda_pdf,
)
from dashboard_backend.tasks.vib_matching import suggest_project_for_bauportal

_EDITABLE_FIELDS = {
    "source_label",
    "document_date",
    "raw_name",
    "category",
    "announced_phase",
    "expected_date",
    "confirmed",
}


def parse_and_store(db: Session, *, pdf_bytes: bytes, user: User | None) -> dict:
    """OCR + LLM extract a Fulda PDF and store draft announcement rows.

    Returns a summary ``{ocr_status, created, source_label}``.
    """

    full_text, _ocr_model, ocr_status = ocr_fulda_pdf(pdf_bytes)
    extracted = extract_fulda_announcements(full_text)

    document_date = parse_flexible_date(extracted.get("document_date"))
    source_label = extracted.get("source_label")
    projects = db.query(Project).all()

    created = 0
    for item in extracted["items"]:
        phase = fulda_category_to_phase(item["category"])
        row = FuldaAnnouncement(
            source_label=source_label,
            document_date=document_date,
            raw_name=item["project_name"],
            category=item["category"],
            announced_phase=phase.value if phase is not None else None,
            expected_date=None,
            suggested_project_id=suggest_project_for_bauportal(item["project_name"], projects),
            confirmed=False,
            created_by_user_id=user.id if user else None,
            username_snapshot=user.username if user else None,
        )
        db.add(row)
        created += 1

    db.commit()
    return {"ocr_status": ocr_status, "created": created, "source_label": source_label}


def _project_name_map(db: Session, ids: list[int | None]) -> dict[int, str]:
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    rows = db.query(Project.id, Project.name).filter(Project.id.in_(wanted)).all()
    return {row.id: row.name for row in rows}


def _entry_dict(db: Session, row: FuldaAnnouncement, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "source_label": row.source_label,
        "document_date": row.document_date,
        "raw_name": row.raw_name,
        "category": row.category,
        "announced_phase": row.announced_phase,
        "expected_date": row.expected_date,
        "suggested_project_id": row.suggested_project_id,
        "suggested_project_name": names.get(row.suggested_project_id),
        "project_id": row.project_id,
        "project_name": names.get(row.project_id),
        "confirmed": row.confirmed,
        "created_at": row.created_at,
        "username_snapshot": row.username_snapshot,
    }


def list_entries(db: Session, *, only_unconfirmed: bool = False) -> list[dict]:
    query = db.query(FuldaAnnouncement)
    if only_unconfirmed:
        query = query.filter(FuldaAnnouncement.project_id.is_(None))
    rows = query.order_by(
        FuldaAnnouncement.project_id.isnot(None),  # unmatched first
        FuldaAnnouncement.raw_name,
    ).all()
    names = _project_name_map(
        db, [r.project_id for r in rows] + [r.suggested_project_id for r in rows]
    )
    return [_entry_dict(db, row, names) for row in rows]


def update_entry(db: Session, entry_id: int, payload: dict) -> dict | None:
    row = db.query(FuldaAnnouncement).filter(FuldaAnnouncement.id == entry_id).first()
    if row is None:
        return None

    old_project_id = row.project_id
    if "project_id" in payload:
        new_pid = payload["project_id"]
        if new_pid is not None:
            exists = db.query(Project.id).filter(Project.id == new_pid).first()
            if exists is None:
                raise ValueError(f"Project {new_pid} not found")
        row.project_id = new_pid

    for key, value in payload.items():
        if key in _EDITABLE_FIELDS:
            setattr(row, key, value)

    db.commit()
    for affected in {old_project_id, row.project_id} - {None}:
        recompute_progress(db, affected)

    db.refresh(row)
    names = _project_name_map(db, [row.project_id, row.suggested_project_id])
    return _entry_dict(db, row, names)


def delete_entry(db: Session, entry_id: int) -> bool:
    row = db.query(FuldaAnnouncement).filter(FuldaAnnouncement.id == entry_id).first()
    if row is None:
        return False
    linked_project_id = row.project_id
    db.delete(row)
    db.commit()
    if linked_project_id is not None:
        recompute_progress(db, linked_project_id)
    return True
