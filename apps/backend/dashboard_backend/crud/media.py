"""DB access for the Medien/Presse importer (#48).

Creates draft media_report rows from a URL or pasted text (with optional LLM
extraction + fuzzy project match), lists them for the review UI, and on confirm
re-materialises the affected project's derived MEDIEN observation. Media reports
are editor-owned, so unlike derived observations they can be edited and deleted.
"""

from __future__ import annotations

from sqlalchemy.orm import Session, load_only

from dashboard_backend.crud._importer_common import (
    ProjectNotFoundError,
    apply_editable_fields,
    ensure_projects_exist,
    project_name_map,
    recompute_for,
)
from dashboard_backend.models.projects.media_report import MediaReport
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.users import User
from dashboard_backend.services.progress_dates import parse_flexible_date
from dashboard_backend.tasks.media_extraction import extract_media_report, fetch_url_text
from dashboard_backend.tasks.vib_matching import suggest_project_for_bauportal

_EDITABLE_FIELDS = {
    "url",
    "publication",
    "published_date",
    "asserted_phase",
    "observed_date",
    "quote",
    "confirmed",
}


def create_from_input(
    db: Session, *, url: str | None, text: str | None, user: User | None
) -> dict:
    """Fetch (if only a URL is given), run extraction, and store a draft.

    Raises ``ValueError`` if neither URL nor text is provided. Network failures
    from URL fetching propagate as ``httpx.HTTPError`` for the endpoint to map.
    """

    url = (url or "").strip() or None
    text = (text or "").strip() or None
    if url is None and text is None:
        raise ValueError("Either a URL or article text is required.")

    if text is None and url is not None:
        text = fetch_url_text(url)

    extracted = extract_media_report(text or "", url=url)

    suggested_project_id = None
    if extracted.get("project_name"):
        # The fuzzy matcher only reads id/name — skip the heavy columns
        # (geojson_representation can be MBs per row).
        projects = (
            db.query(Project)
            .options(load_only(Project.id, Project.name))
            .all()
        )
        suggested_project_id = suggest_project_for_bauportal(
            extracted["project_name"], projects
        )

    published_date = parse_flexible_date(extracted.get("published_date"))
    observed_date = parse_flexible_date(extracted.get("observed_date")) or published_date

    row = MediaReport(
        url=url,
        publication=extracted.get("publication"),
        published_date=published_date,
        raw_text=text,
        quote=extracted.get("quote"),
        asserted_phase=extracted.get("phase"),
        observed_date=observed_date,
        suggested_project_id=suggested_project_id,
        confirmed=False,
        created_by_user_id=user.id if user else None,
        username_snapshot=user.username if user else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _entry_dict(row, project_name_map(db, [row.project_id, row.suggested_project_id]))


def _entry_dict(row: MediaReport, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "url": row.url,
        "publication": row.publication,
        "published_date": row.published_date,
        "raw_text": row.raw_text,
        "quote": row.quote,
        "asserted_phase": row.asserted_phase,
        "observed_date": row.observed_date,
        "suggested_project_id": row.suggested_project_id,
        "suggested_project_name": names.get(row.suggested_project_id),
        "project_id": row.project_id,
        "project_name": names.get(row.project_id),
        "confirmed": row.confirmed,
        "created_at": row.created_at,
        "username_snapshot": row.username_snapshot,
    }


def list_entries(db: Session, *, only_unconfirmed: bool = False) -> list[dict]:
    query = db.query(MediaReport)
    if only_unconfirmed:
        query = query.filter(MediaReport.confirmed.is_(False))
    rows = query.order_by(MediaReport.created_at.desc(), MediaReport.id.desc()).all()
    # One batched name lookup for all rows (was one query per row).
    names = project_name_map(
        db, [i for row in rows for i in (row.project_id, row.suggested_project_id)]
    )
    return [_entry_dict(row, names) for row in rows]


def update_entry(db: Session, entry_id: int, payload: dict) -> dict | None:
    """Patch editable fields. Setting ``project_id`` is allowed (incl. null to
    clear). Re-materialises previously- and newly-linked projects."""

    row = db.query(MediaReport).filter(MediaReport.id == entry_id).first()
    if row is None:
        return None

    old_project_id = row.project_id

    if "project_id" in payload:
        new_pid = payload["project_id"]
        if new_pid is not None:
            ensure_projects_exist(db, [new_pid])
        row.project_id = new_pid

    apply_editable_fields(row, payload, _EDITABLE_FIELDS)

    db.commit()

    recompute_for(db, [old_project_id, row.project_id])

    db.refresh(row)
    return _entry_dict(row, project_name_map(db, [row.project_id, row.suggested_project_id]))


def delete_entry(db: Session, entry_id: int) -> bool:
    row = db.query(MediaReport).filter(MediaReport.id == entry_id).first()
    if row is None:
        return False
    linked_project_id = row.project_id
    db.delete(row)
    db.commit()
    recompute_for(db, [linked_project_id])
    return True
