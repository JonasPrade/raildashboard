from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session, selectinload

from dashboard_backend.models.change_tracking import ChangeLog, ChangeLogEntry
from dashboard_backend.models.projects import Project

# Fields that should not be tracked in the changelog (large/computed/geometric values)
_SKIP_FIELDS = {"centroid"}


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
