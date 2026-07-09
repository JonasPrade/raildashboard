"""DB access for the Fulda-Runde importer (#46).

Parses an uploaded "Antwort der Bundesregierung" PDF (OCR + LLM) into
per-(project, category) draft rows whose project assignment is pre-filled with
the top fuzzy-match candidates (m:n, like VIB — the editor adjusts via a
MultiSelect). On confirm/edit/delete the affected projects' derived FULDA_RUNDE
observations are re-materialised. Rows are editor-owned (editable / deletable),
and whole years can be dropped at once.
"""

from __future__ import annotations

from sqlalchemy.orm import Session, load_only

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
from dashboard_backend.tasks.vib_matching import (
    suggest_projects_for_vib_entry,
    suggest_subproject_for_pfa,
)

_EDITABLE_FIELDS = {
    "announcement_year",
    "source_label",
    "document_date",
    "raw_name",
    "abschnitt",
    "category",
    "announced_phase",
    "expected_date",
    "confirmed",
}

# Abschnitt values that name the whole project rather than a distinct subproject
# (so the observation stays on the superior project, not a leaf).
_GENERIC_ABSCHNITT = {"", "gesamtstrecke", "gesamtprojekt", "gesamtmaßnahme"}


def _resolve_leaf_ids(
    superior_ids: list[int],
    abschnitt: str | None,
    children_by_superior: dict[int, list[Project]],
) -> list[int]:
    """Pick the leaf project(s) to pre-assign for one extracted Fulda row.

    The Abschnitt is the subproject: if it names a distinct section and a
    matching subproject exists under one of the fuzzy-matched superior projects,
    pre-fill that leaf; otherwise fall back to the superior matches. Never
    creates subprojects — the editor confirms/corrects in the review.
    """
    if not superior_ids:
        return []
    norm = (abschnitt or "").strip().lower()
    if norm in _GENERIC_ABSCHNITT:
        return superior_ids
    candidates: list[Project] = []
    for sid in superior_ids:
        candidates.extend(children_by_superior.get(sid, []))
    if not candidates:
        return superior_ids
    sub_id = suggest_subproject_for_pfa(abschnitt, candidates)
    return [sub_id] if sub_id is not None else superior_ids


def parse_and_store(
    db: Session, *, pdf_bytes: bytes, year: int, user: User | None
) -> dict:
    """OCR + LLM extract a Fulda PDF and store draft announcement rows for ``year``.

    Each row's project assignment is pre-filled with the top fuzzy-match
    candidates so the editor reviews suggestions directly instead of searching.
    Re-parsing the same year first drops that year's still-unconfirmed drafts, so
    a fresh upload replaces the old suggestions without touching confirmed rows.
    Returns a summary ``{ocr_status, created, source_label}``.
    """

    full_text, _ocr_model, ocr_status = ocr_fulda_pdf(pdf_bytes)
    extracted = extract_fulda_announcements(full_text)

    document_date = parse_flexible_date(extracted.get("document_date"))
    source_label = extracted.get("source_label")
    # The fuzzy matcher only reads id/name/superior_project_id — don't drag
    # geojson_representation (potentially MBs per row) along for every project.
    projects = (
        db.query(Project)
        .options(load_only(Project.id, Project.name, Project.superior_project_id))
        .all()
    )
    by_id = {p.id: p for p in projects}
    children_by_superior: dict[int, list[Project]] = {}
    for p in projects:
        if p.superior_project_id is not None:
            children_by_superior.setdefault(p.superior_project_id, []).append(p)

    db.query(FuldaAnnouncement).filter(
        FuldaAnnouncement.announcement_year == year,
        FuldaAnnouncement.confirmed.is_(False),
    ).delete(synchronize_session=False)

    created = 0
    for item in extracted["items"]:
        phase = fulda_category_to_phase(item["category"])
        abschnitt = item.get("abschnitt")
        superior_ids = suggest_projects_for_vib_entry(item["project_name"], projects)
        leaf_ids = _resolve_leaf_ids(superior_ids, abschnitt, children_by_superior)
        row = FuldaAnnouncement(
            announcement_year=year,
            source_label=source_label,
            document_date=document_date,
            raw_name=item["project_name"],
            abschnitt=abschnitt,
            category=item["category"],
            announced_phase=phase.value if phase is not None else None,
            expected_date=None,
            projects=[by_id[pid] for pid in leaf_ids if pid in by_id],
            confirmed=False,
            created_by_user_id=user.id if user else None,
            username_snapshot=user.username if user else None,
        )
        db.add(row)
        created += 1

    db.commit()
    return {"ocr_status": ocr_status, "created": created, "source_label": source_label}


def _entry_dict(row: FuldaAnnouncement) -> dict:
    linked = sorted(row.projects, key=lambda p: (p.name or ""))
    return {
        "id": row.id,
        "announcement_year": row.announcement_year,
        "source_label": row.source_label,
        "document_date": row.document_date,
        "raw_name": row.raw_name,
        "abschnitt": row.abschnitt,
        "category": row.category,
        "announced_phase": row.announced_phase,
        "expected_date": row.expected_date,
        "project_ids": [p.id for p in linked],
        "project_names": [p.name for p in linked if p.name],
        "confirmed": row.confirmed,
        "created_at": row.created_at,
        "username_snapshot": row.username_snapshot,
    }


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
    """Per-year overview rows (total/confirmed counts + provenance), newest first.

    Drives the year-overview table that is the importer's landing view; clicking
    a year opens its detail (the five phase tables).
    """
    from sqlalchemy import case, func

    rows = (
        db.query(
            FuldaAnnouncement.announcement_year.label("year"),
            func.count(FuldaAnnouncement.id).label("total"),
            func.sum(
                case((FuldaAnnouncement.confirmed.is_(True), 1), else_=0)
            ).label("confirmed"),
            func.max(FuldaAnnouncement.source_label).label("source_label"),
            func.max(FuldaAnnouncement.document_date).label("document_date"),
        )
        .group_by(FuldaAnnouncement.announcement_year)
        .order_by(FuldaAnnouncement.announcement_year.desc())
        .all()
    )
    return [
        {
            "announcement_year": r.year,
            "total": int(r.total or 0),
            "confirmed": int(r.confirmed or 0),
            "source_label": r.source_label,
            "document_date": r.document_date,
        }
        for r in rows
    ]


def list_entries(
    db: Session, *, only_unconfirmed: bool = False, year: int | None = None
) -> list[dict]:
    query = db.query(FuldaAnnouncement)
    if year is not None:
        query = query.filter(FuldaAnnouncement.announcement_year == year)
    if only_unconfirmed:
        query = query.filter(FuldaAnnouncement.confirmed.is_(False))
    rows = query.order_by(
        FuldaAnnouncement.announcement_year.desc(),
        FuldaAnnouncement.confirmed,  # unconfirmed first
        FuldaAnnouncement.raw_name,
    ).all()
    return [_entry_dict(row) for row in rows]


def _set_projects(db: Session, row: FuldaAnnouncement, project_ids: list[int]) -> None:
    wanted = list(dict.fromkeys(project_ids))  # dedupe, keep order
    if wanted:
        found = db.query(Project).filter(Project.id.in_(wanted)).all()
        found_ids = {p.id for p in found}
        missing = [pid for pid in wanted if pid not in found_ids]
        if missing:
            raise ValueError(f"Project(s) not found: {missing}")
        row.projects = found
    else:
        row.projects = []


def update_entry(db: Session, entry_id: int, payload: dict) -> dict | None:
    row = db.query(FuldaAnnouncement).filter(FuldaAnnouncement.id == entry_id).first()
    if row is None:
        return None

    old_project_ids = {p.id for p in row.projects}
    if "project_ids" in payload and payload["project_ids"] is not None:
        _set_projects(db, row, payload["project_ids"])

    for key, value in payload.items():
        if key in _EDITABLE_FIELDS:
            setattr(row, key, value)

    db.commit()
    db.refresh(row)
    new_project_ids = {p.id for p in row.projects}
    for affected in old_project_ids | new_project_ids:
        recompute_progress(db, affected)

    return _entry_dict(row)


def delete_entry(db: Session, entry_id: int) -> bool:
    row = db.query(FuldaAnnouncement).filter(FuldaAnnouncement.id == entry_id).first()
    if row is None:
        return False
    linked_ids = {p.id for p in row.projects}
    db.delete(row)
    db.commit()
    for pid in linked_ids:
        recompute_progress(db, pid)
    return True


def confirm_year(db: Session, year: int) -> int:
    """Confirm every still-open entry of a year that has a project assigned.

    Skips entries without any linked project (they cannot be materialised).
    Re-materialises the affected projects once at the end. Returns the number of
    newly confirmed entries. Confirmed entries stay editable afterwards — changing
    their assignment re-materialises again via ``update_entry``.
    """
    rows = (
        db.query(FuldaAnnouncement)
        .filter(
            FuldaAnnouncement.announcement_year == year,
            FuldaAnnouncement.confirmed.is_(False),
        )
        .all()
    )
    affected: set[int] = set()
    count = 0
    for row in rows:
        if not row.projects:
            continue
        row.confirmed = True
        affected.update(p.id for p in row.projects)
        count += 1
    db.commit()
    for pid in affected:
        recompute_progress(db, pid)
    return count


def delete_year(db: Session, year: int) -> int:
    """Delete all Fulda announcements of a year; re-materialise affected projects.

    Returns the number of deleted rows.
    """
    rows = (
        db.query(FuldaAnnouncement)
        .filter(FuldaAnnouncement.announcement_year == year)
        .all()
    )
    if not rows:
        return 0
    affected: set[int] = set()
    for row in rows:
        affected.update(p.id for p in row.projects)
        db.delete(row)
    db.commit()
    for pid in affected:
        recompute_progress(db, pid)
    return len(rows)
