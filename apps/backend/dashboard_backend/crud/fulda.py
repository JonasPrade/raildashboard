"""DB access for the Fulda-Runde importer (feature-fulda-import.md).

An agent reads a Fulda answer (PDF) itself and records it via the MCP tools: one
``FuldaDocument`` per answer, one ``FuldaAnnouncement`` per statement. New
entries get their project assignment pre-filled with the top fuzzy matches
(marked as automatic in ``assignment_note``); the agent or an editor confirms or
corrects it. Confirming materialises the derived FULDA_RUNDE observations;
every change re-materialises the affected projects.
"""

from __future__ import annotations

from sqlalchemy import case, func
from sqlalchemy.orm import Session, load_only

from dashboard_backend.crud._importer_common import (
    apply_editable_fields,
    ensure_projects_exist,
    recompute_for,
)
from dashboard_backend.models.projects.fulda_announcement import FuldaAnnouncement
from dashboard_backend.models.projects.fulda_document import ANSWER_STATUSES, FuldaDocument
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.users import User
from dashboard_backend.services.fulda_categories import ATTRIBUTED_TO, get_category
from dashboard_backend.tasks.vib_matching import (
    suggest_projects_for_vib_entry,
    suggest_subproject_by_name,
)

AUTO_SUGGESTION_NOTE = "Automatischer Vorschlag (Namensabgleich), ungeprüft"

_DOCUMENT_FIELDS = {"year", "drucksache", "title", "document_date", "dip_url", "answer_status", "note"}
_ENTRY_FIELDS = {
    "raw_name",
    "abschnitt",
    "category",
    "expected_date",
    "question_ref",
    "page",
    "raw_text",
    "attributed_to",
    "assignment_note",
    "confirmed",
}

# Abschnitt values that name the whole project rather than a distinct subproject
# (so the suggestion stays on the superior project, not a leaf).
_GENERIC_ABSCHNITT = {"", "gesamtstrecke", "gesamtprojekt", "gesamtmaßnahme"}


class FuldaValidationError(ValueError):
    """Invalid input (unknown category, duplicate Drucksache, …); message is German."""


# --- Validation --------------------------------------------------------------


def _validate_document(payload: dict) -> None:
    status = payload.get("answer_status")
    if status is not None and status not in ANSWER_STATUSES:
        raise FuldaValidationError(
            f"Unbekannter Antwortstand '{status}'. Erlaubt: {', '.join(ANSWER_STATUSES)}."
        )
    for key in ("year", "drucksache", "document_date"):
        if key in payload and payload[key] in (None, ""):
            raise FuldaValidationError(f"'{key}' darf nicht leer sein.")


def _validate_entry(payload: dict) -> None:
    if "category" in payload and get_category(payload["category"]) is None:
        raise FuldaValidationError(
            f"Unbekannte Kategorie '{payload['category']}'. Siehe list_fulda_categories."
        )
    if "category" in payload:
        payload["category"] = get_category(payload["category"]).key
    attributed = payload.get("attributed_to")
    if attributed is not None and attributed not in ATTRIBUTED_TO:
        raise FuldaValidationError(
            f"Unbekannte Urheberschaft '{attributed}'. Erlaubt: {', '.join(ATTRIBUTED_TO)}."
        )
    if "raw_name" in payload and not (payload["raw_name"] or "").strip():
        raise FuldaValidationError("'raw_name' darf nicht leer sein.")


# --- Serialisation -----------------------------------------------------------


def _document_dict(doc: FuldaDocument, counts: dict | None = None) -> dict:
    counts = counts or {}
    return {
        "id": doc.id,
        "year": doc.year,
        "drucksache": doc.drucksache,
        "title": doc.title,
        "document_date": doc.document_date,
        "dip_url": doc.dip_url,
        "answer_status": doc.answer_status,
        "note": doc.note,
        "total": counts.get("total", 0),
        "assigned": counts.get("assigned", 0),
        "confirmed": counts.get("confirmed", 0),
        "created_at": doc.created_at,
        "username_snapshot": doc.username_snapshot,
    }


def _entry_dict(row: FuldaAnnouncement) -> dict:
    linked = sorted(row.projects, key=lambda p: (p.name or ""))
    cat = get_category(row.category)
    doc = row.document
    return {
        "id": row.id,
        "document_id": row.document_id,
        "announcement_year": row.announcement_year,
        "drucksache": doc.drucksache if doc is not None else None,
        "document_date": doc.document_date if doc is not None else None,
        "raw_name": row.raw_name,
        "abschnitt": row.abschnitt,
        "category": row.category,
        "statement_kind": cat.kind if cat is not None else None,
        "phase": cat.phase.value if cat is not None and cat.phase is not None else None,
        "expected_date": row.expected_date,
        "question_ref": row.question_ref,
        "page": row.page,
        "raw_text": row.raw_text,
        "attributed_to": row.attributed_to,
        "assignment_note": row.assignment_note,
        "project_ids": [p.id for p in linked],
        "project_names": [p.name for p in linked if p.name],
        "confirmed": row.confirmed,
        "created_at": row.created_at,
        "username_snapshot": row.username_snapshot,
    }


# --- Documents ---------------------------------------------------------------


def _document_counts(db: Session) -> dict[int, dict]:
    from dashboard_backend.models.associations.fulda_announcement_to_project import (
        fulda_announcement_to_project as link,
    )

    assigned_ids = (
        db.query(link.c.fulda_announcement_id).distinct().subquery()
    )
    rows = (
        db.query(
            FuldaAnnouncement.document_id,
            func.count(FuldaAnnouncement.id),
            func.sum(case((FuldaAnnouncement.id.in_(db.query(assigned_ids)), 1), else_=0)),
            func.sum(case((FuldaAnnouncement.confirmed.is_(True), 1), else_=0)),
        )
        .filter(FuldaAnnouncement.document_id.isnot(None))
        .group_by(FuldaAnnouncement.document_id)
        .all()
    )
    return {
        doc_id: {"total": int(t or 0), "assigned": int(a or 0), "confirmed": int(c or 0)}
        for doc_id, t, a, c in rows
    }


def list_documents(db: Session, *, year: int | None = None) -> list[dict]:
    query = db.query(FuldaDocument)
    if year is not None:
        query = query.filter(FuldaDocument.year == year)
    docs = query.order_by(FuldaDocument.year.desc(), FuldaDocument.document_date.desc()).all()
    counts = _document_counts(db)
    return [_document_dict(d, counts.get(d.id)) for d in docs]


def get_document(db: Session, document_id: int) -> FuldaDocument | None:
    return db.query(FuldaDocument).filter(FuldaDocument.id == document_id).first()


def create_document(db: Session, payload: dict, user: User | None) -> dict:
    _validate_document(payload)
    for key in ("year", "drucksache", "document_date"):
        if payload.get(key) in (None, ""):
            raise FuldaValidationError(f"'{key}' ist Pflicht.")
    drucksache = payload["drucksache"].strip()
    existing = db.query(FuldaDocument).filter(FuldaDocument.drucksache == drucksache).first()
    if existing is not None:
        raise FuldaValidationError(
            f"Drucksache {drucksache} ist schon als Dokument {existing.id} erfasst."
        )
    doc = FuldaDocument(
        **{k: v for k, v in payload.items() if k in _DOCUMENT_FIELDS},
        created_by_user_id=user.id if user else None,
        username_snapshot=user.username if user else None,
    )
    doc.drucksache = drucksache
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _document_dict(doc)


def update_document(db: Session, document_id: int, payload: dict) -> dict | None:
    doc = get_document(db, document_id)
    if doc is None:
        return None
    _validate_document(payload)
    apply_editable_fields(doc, payload, _DOCUMENT_FIELDS)
    affected: set[int] = set()
    if "year" in payload or "document_date" in payload:
        # Year is copied onto the entries; the date drives the observations.
        for row in doc.entries:
            row.announcement_year = doc.year
            affected.update(p.id for p in row.projects)
    db.commit()
    db.refresh(doc)
    recompute_for(db, affected)
    return _document_dict(doc, _document_counts(db).get(doc.id))


def delete_document(db: Session, document_id: int) -> bool:
    doc = get_document(db, document_id)
    if doc is None:
        return False
    affected = {p.id for row in doc.entries for p in row.projects}
    db.delete(doc)
    db.commit()
    recompute_for(db, affected)
    return True


# --- Suggestions ---------------------------------------------------------------


class _Matcher:
    """Fuzzy project suggestions for Fulda lines (superior project → leaf).

    Loads id/name/superior once — never the (potentially huge) geometry.
    """

    def __init__(self, db: Session):
        self.projects = (
            db.query(Project)
            .options(load_only(Project.id, Project.name, Project.superior_project_id))
            .all()
        )
        self.children: dict[int, list[Project]] = {}
        for p in self.projects:
            if p.superior_project_id is not None:
                self.children.setdefault(p.superior_project_id, []).append(p)

    def suggest(self, raw_name: str, abschnitt: str | None) -> list[int]:
        """The Abschnitt is the subproject: if it names a distinct section and a
        matching subproject exists under a matched superior, suggest that leaf;
        otherwise the superior matches."""

        superior_ids = suggest_projects_for_vib_entry(raw_name, self.projects)
        if not superior_ids:
            return []
        if (abschnitt or "").strip().lower() in _GENERIC_ABSCHNITT:
            return superior_ids
        candidates = [c for sid in superior_ids for c in self.children.get(sid, [])]
        if not candidates:
            return superior_ids
        sub_id = suggest_subproject_by_name(abschnitt, candidates)
        return [sub_id] if sub_id is not None else superior_ids


# --- Entries -------------------------------------------------------------------


def add_entries(
    db: Session, document_id: int, items: list[dict], user: User | None
) -> list[dict]:
    """Create announcement rows for a document, all-or-nothing.

    Each item needs ``raw_name``, ``category`` and ``raw_text``. The project
    assignment is pre-filled with fuzzy suggestions (``assignment_note`` says
    so); nothing is confirmed here.
    """

    doc = get_document(db, document_id)
    if doc is None:
        raise FuldaValidationError(f"Dokument {document_id} gibt es nicht.")
    for index, item in enumerate(items):
        for key in ("raw_name", "category", "raw_text"):
            if not str(item.get(key) or "").strip():
                raise FuldaValidationError(f"Eintrag {index + 1}: '{key}' ist Pflicht.")
        try:
            _validate_entry(item)
        except FuldaValidationError as exc:
            raise FuldaValidationError(f"Eintrag {index + 1}: {exc}") from exc

    matcher = _Matcher(db)
    by_id = {p.id: p for p in matcher.projects}
    rows: list[FuldaAnnouncement] = []
    for item in items:
        suggested = matcher.suggest(item["raw_name"], item.get("abschnitt"))
        row = FuldaAnnouncement(
            document_id=doc.id,
            announcement_year=doc.year,
            **{k: v for k, v in item.items() if k in _ENTRY_FIELDS and k != "confirmed"},
            projects=[by_id[pid] for pid in suggested if pid in by_id],
            confirmed=False,
            created_by_user_id=user.id if user else None,
            username_snapshot=user.username if user else None,
        )
        if suggested and not row.assignment_note:
            row.assignment_note = AUTO_SUGGESTION_NOTE
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return [_entry_dict(row) for row in rows]


def get_entry(db: Session, entry_id: int) -> FuldaAnnouncement | None:
    return db.query(FuldaAnnouncement).filter(FuldaAnnouncement.id == entry_id).first()


def list_years(db: Session) -> list[int]:
    """Distinct Fulda-Runde years present, newest first (for the year filter)."""
    rows = (
        db.query(FuldaAnnouncement.announcement_year)
        .distinct()
        .order_by(FuldaAnnouncement.announcement_year.desc())
        .all()
    )
    return [r[0] for r in rows]


def list_year_summaries(db: Session) -> list[dict]:
    """Per-year overview rows (counts + the year's documents), newest first."""

    years: dict[int, dict] = {}
    for doc in list_documents(db):
        summary = years.setdefault(
            doc["year"],
            {"announcement_year": doc["year"], "total": 0, "confirmed": 0, "documents": []},
        )
        summary["total"] += doc["total"]
        summary["confirmed"] += doc["confirmed"]
        summary["documents"].append(doc)
    return [years[y] for y in sorted(years, reverse=True)]


def list_entries(
    db: Session,
    *,
    only_unconfirmed: bool = False,
    year: int | None = None,
    document_id: int | None = None,
) -> list[dict]:
    query = db.query(FuldaAnnouncement)
    if year is not None:
        query = query.filter(FuldaAnnouncement.announcement_year == year)
    if document_id is not None:
        query = query.filter(FuldaAnnouncement.document_id == document_id)
    if only_unconfirmed:
        query = query.filter(FuldaAnnouncement.confirmed.is_(False))
    rows = query.order_by(
        FuldaAnnouncement.announcement_year.desc(),
        FuldaAnnouncement.confirmed,  # unconfirmed first
        FuldaAnnouncement.id,
    ).all()
    return [_entry_dict(row) for row in rows]


def update_entry(db: Session, entry_id: int, payload: dict) -> dict | None:
    """Patch one entry; ``project_ids`` replaces the whole assignment."""

    row = get_entry(db, entry_id)
    if row is None:
        return None
    _validate_entry(payload)

    old_project_ids = {p.id for p in row.projects}
    if payload.get("project_ids") is not None:
        row.projects = ensure_projects_exist(db, payload["project_ids"])
    apply_editable_fields(row, payload, _ENTRY_FIELDS)

    db.commit()
    db.refresh(row)
    recompute_for(db, old_project_ids | {p.id for p in row.projects})
    return _entry_dict(row)


def delete_entry(db: Session, entry_id: int) -> bool:
    row = get_entry(db, entry_id)
    if row is None:
        return False
    linked_ids = {p.id for p in row.projects}
    db.delete(row)
    db.commit()
    recompute_for(db, linked_ids)
    return True


def _confirm(db: Session, rows: list[FuldaAnnouncement]) -> int:
    """Confirm every open row that has a project; re-materialise once."""

    affected: set[int] = set()
    count = 0
    for row in rows:
        if row.confirmed or not row.projects:
            continue
        row.confirmed = True
        affected.update(p.id for p in row.projects)
        count += 1
    db.commit()
    recompute_for(db, affected)
    return count


def confirm_year(db: Session, year: int) -> int:
    """Confirm all assigned, still-open entries of a year. Returns the count."""
    rows = db.query(FuldaAnnouncement).filter(FuldaAnnouncement.announcement_year == year).all()
    return _confirm(db, rows)


def confirm_document(db: Session, document_id: int) -> int:
    """Confirm all assigned, still-open entries of a document. Returns the count."""
    rows = (
        db.query(FuldaAnnouncement).filter(FuldaAnnouncement.document_id == document_id).all()
    )
    return _confirm(db, rows)


def delete_year(db: Session, year: int) -> int:
    """Delete all documents and entries of a year; returns the deleted entry count."""

    rows = db.query(FuldaAnnouncement).filter(FuldaAnnouncement.announcement_year == year).all()
    docs = db.query(FuldaDocument).filter(FuldaDocument.year == year).all()
    if not rows and not docs:
        return 0
    affected = {p.id for row in rows for p in row.projects}
    for row in rows:
        db.delete(row)
    for doc in docs:
        db.delete(doc)
    db.commit()
    recompute_for(db, affected)
    return max(len(rows), 1)

