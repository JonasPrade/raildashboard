from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session, selectinload

from dashboard_backend.models.change_tracking import ChangeLog, ChangeLogEntry, TextChangeLog, TextChangeLogEntry
from dashboard_backend.models.projects import Project
from dashboard_backend.models.projects.project_text import ProjectText

# Fields that should not be tracked in the changelog (large/computed/geometric values)
_SKIP_FIELDS = {"centroid"}

# Fields tracked for project texts (excludes internal timestamps)
_TEXT_TRACKED_FIELDS = ("header", "text", "weblink", "logo_url", "type")


def create_changelog_for_patch(
    db: Session,
    project: Project,
    update_data: dict,
    user_id: int | None,
    username_snapshot: str | None,
    action: str = "PATCH",
) -> ChangeLog | None:
    """Compare current project field values against update_data and create a ChangeLog.

    Only records fields that actually changed. Returns the ChangeLog object added to
    the session (not yet committed), or None if no fields differ.
    The caller is responsible for committing the session.
    """
    entries = []
    for field, new_val in update_data.items():
        if field in _SKIP_FIELDS:
            continue
        old_val = getattr(project, field, None)
        if old_val == new_val:
            continue
        entries.append(
            ChangeLogEntry(
                field_name=field,
                old_value=json.dumps(old_val) if old_val is not None else None,
                new_value=json.dumps(new_val) if new_val is not None else None,
            )
        )

    if not entries:
        return None

    changelog = ChangeLog(
        project_id=project.id,
        user_id=user_id,
        username_snapshot=username_snapshot,
        timestamp=datetime.utcnow(),
        action=action,
        entries=entries,
    )
    db.add(changelog)
    return changelog


def get_project_changelog(db: Session, project_id: int) -> list[ChangeLog]:
    """Return all ChangeLog records for a project, newest first."""
    return (
        db.query(ChangeLog)
        .options(selectinload(ChangeLog.entries))
        .filter(ChangeLog.project_id == project_id)
        .order_by(ChangeLog.timestamp.desc())
        .all()
    )


def get_changelog_entry(db: Session, entry_id: int, project_id: int) -> ChangeLogEntry | None:
    """Fetch a ChangeLogEntry, verifying it belongs to the given project."""
    return (
        db.query(ChangeLogEntry)
        .join(ChangeLog)
        .filter(ChangeLogEntry.id == entry_id, ChangeLog.project_id == project_id)
        .first()
    )


# ---------------------------------------------------------------------------
# Text change tracking
# ---------------------------------------------------------------------------


def _make_text_entries(fields: tuple[str, ...], old_obj: ProjectText | None, new_data: dict | None) -> list[TextChangeLogEntry]:
    """Build TextChangeLogEntry list by comparing old object values against new_data dict.

    For CREATE: old_obj is None, new_data holds all field values.
    For DELETE: old_obj holds all field values, new_data is None.
    For PATCH:  both are provided; only changed fields are recorded.
    """
    entries = []
    for field in fields:
        old_val = getattr(old_obj, field, None) if old_obj else None
        new_val = new_data.get(field) if new_data else None
        if old_val == new_val:
            continue
        entries.append(
            TextChangeLogEntry(
                field_name=field,
                old_value=json.dumps(old_val) if old_val is not None else None,
                new_value=json.dumps(new_val) if new_val is not None else None,
            )
        )
    return entries


def _add_text_changelog(
    db: Session,
    text_id: int | None,
    project_id: int | None,
    text_header_snapshot: str | None,
    user_id: int | None,
    username_snapshot: str | None,
    entries: list[TextChangeLogEntry],
    action: str,
) -> TextChangeLog:
    changelog = TextChangeLog(
        text_id=text_id,
        project_id=project_id,
        text_header_snapshot=text_header_snapshot,
        user_id=user_id,
        username_snapshot=username_snapshot,
        timestamp=datetime.utcnow(),
        action=action,
        entries=entries,
    )
    db.add(changelog)
    return changelog


def create_text_changelog_for_create(
    db: Session,
    text: ProjectText,
    project_id: int | None,
    user_id: int | None,
    username_snapshot: str | None,
) -> TextChangeLog:
    """Record a CREATE event for a new project text. Caller must commit."""
    entries = _make_text_entries(_TEXT_TRACKED_FIELDS, old_obj=None, new_data={f: getattr(text, f, None) for f in _TEXT_TRACKED_FIELDS})
    return _add_text_changelog(db, text.id, project_id, text.header, user_id, username_snapshot, entries, "CREATE")


def create_text_changelog_for_patch(
    db: Session,
    text: ProjectText,
    update_data: dict,
    project_id: int | None,
    user_id: int | None,
    username_snapshot: str | None,
) -> TextChangeLog | None:
    """Record a PATCH event for a project text. Only changed fields are stored.

    Adds the changelog to the session without committing — caller's commit picks it up.
    Returns None if no fields actually changed.
    """
    entries = _make_text_entries(_TEXT_TRACKED_FIELDS, old_obj=text, new_data=update_data)
    if not entries:
        return None
    return _add_text_changelog(db, text.id, project_id, text.header, user_id, username_snapshot, entries, "PATCH")


def create_text_changelog_for_delete(
    db: Session,
    text: ProjectText,
    project_id: int | None,
    user_id: int | None,
    username_snapshot: str | None,
) -> TextChangeLog:
    """Record a DELETE event for a project text.

    Adds the changelog to the session without committing. The caller then deletes
    the text; the database SET NULL rule nulls out text_change_log.text_id afterwards.
    """
    entries = _make_text_entries(_TEXT_TRACKED_FIELDS, old_obj=text, new_data=None)
    return _add_text_changelog(db, text.id, project_id, text.header, user_id, username_snapshot, entries, "DELETE")


def get_project_text_changelog(db: Session, project_id: int) -> list[TextChangeLog]:
    """Return all TextChangeLog records for a project, newest first."""
    return (
        db.query(TextChangeLog)
        .options(selectinload(TextChangeLog.entries))
        .filter(TextChangeLog.project_id == project_id)
        .order_by(TextChangeLog.timestamp.desc())
        .all()
    )
