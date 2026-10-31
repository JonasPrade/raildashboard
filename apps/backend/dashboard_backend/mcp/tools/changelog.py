"""Change history of projects and project texts, and reverting one field change.

Every writing tool logs to the changelog; these tools let an agent check what it
(or anyone) changed and take a single field back — with the same rules as the
UI's revert button (``POST /projects/{id}/changelog/revert``).
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from dashboard_backend.crud.changelog import get_project_changelog as get_changelog_crud
from dashboard_backend.crud.changelog import get_project_text_changelog as get_text_changelog_crud
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.mcp.tools.projects import (
    MAX_LIMIT,
    READ_ONLY,
    WRITE,
    _project_dict,
    _project_or_error,
)
from dashboard_backend.services.changelog_revert import RevertError, revert_changelog_entry

# Values longer than this are cut; geometry values are never shown in full.
VALUE_LIMIT = 500
_GEOMETRY_FIELDS = {"geojson_representation", "centroid"}


def _value(field_name: str, raw: str | None) -> tuple[Any, bool]:
    """A stored (JSON-encoded) value for display: (value, truncated)."""
    if raw is None:
        return None, False
    if field_name in _GEOMETRY_FIELDS:
        return f"<Geometrie, {len(raw)} Zeichen>", True
    if len(raw) > VALUE_LIMIT:
        return raw[: VALUE_LIMIT - 1] + "…", True
    return raw, False


def _entry_dict(entry) -> dict[str, Any]:
    old, old_cut = _value(entry.field_name, entry.old_value)
    new, new_cut = _value(entry.field_name, entry.new_value)
    data = {"entry_id": entry.id, "field": entry.field_name, "old": old, "new": new}
    if old_cut or new_cut:
        data["truncated"] = True
    return data


def _event_dict(log, *, text: bool = False) -> dict[str, Any]:
    data = {
        "id": log.id,
        "timestamp": log.timestamp.isoformat(timespec="seconds"),
        "user": log.username_snapshot,
        "action": log.action,
        "changes": [_entry_dict(e) for e in sorted(log.entries, key=lambda e: e.id)],
    }
    if text:
        data["text_id"] = log.text_id
        data["text_header"] = log.text_header_snapshot
    return data


def _filter_events(events, field: str | None, since: date | None) -> list:
    if since is not None:
        start = datetime.combine(since, time.min)
        events = [log for log in events if log.timestamp >= start]
    if field:
        events = [log for log in events if any(e.field_name == field for e in log.entries)]
    return events


def get_project_changelog(
    project_id: int,
    field: str | None = None,
    since: date | None = None,
    limit: int = 30,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Change history of a project, newest first: per event timestamp, user,
    action (CREATE, PATCH, REVERT, …) and the changed fields with old and new
    value (stored as JSON text). Each change carries an ``entry_id`` — pass it
    to revert_project_change to take that one field back. Geometry values are
    replaced by their size, other values are cut after 500 characters
    (``truncated``).
    - field: only events that changed this field (e.g. "description",
      "finve_ids", "geojson_representation", "project_group_ids")
    - since: only events on or after this date (JJJJ-MM-TT)
    Paged with limit/offset; ``total`` counts all matching events."""
    get_principal(ctx)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        events = _filter_events(get_changelog_crud(db, project.id), field, since)
        return {
            "project_id": project.id,
            "project_name": project.name,
            "total": len(events),
            "offset": offset,
            "events": [_event_dict(log) for log in events[offset : offset + limit]],
        }


def get_project_text_changelog(
    project_id: int,
    text_id: int | None = None,
    since: date | None = None,
    limit: int = 30,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Change history of a project's texts, newest first (create, update,
    delete), with the text header at the time of the change — also for texts
    deleted since. text_id narrows to one text; since (JJJJ-MM-TT) to recent
    events. Text changes are not revertible through MCP: write the old content
    back with upsert_project_text."""
    get_principal(ctx)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        events = _filter_events(get_text_changelog_crud(db, project.id), None, since)
        if text_id is not None:
            events = [log for log in events if log.text_id == text_id]
        return {
            "project_id": project.id,
            "total": len(events),
            "offset": offset,
            "events": [_event_dict(log, text=True) for log in events[offset : offset + limit]],
        }


def revert_project_change(
    project_id: int, changelog_entry_id: int, *, ctx: Context
) -> dict[str, Any]:
    """Set one field of a project back to the old value recorded in a changelog
    entry (``entry_id`` from get_project_changelog) — the UI's revert button
    (requires ``project.edit``; FinVe links and Sammel-FinVe years also need
    ``finve.edit``). Only that field changes; later changes to other fields
    stay. The revert is itself logged (action REVERT) and can be reverted again.
    A geometry is refused while the project takes it from its subprojects.
    Returns the field and the project afterwards."""
    principal = get_principal(ctx)
    require(principal, "project.edit")
    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        user = load_user(db, principal)
        try:
            updated = revert_changelog_entry(
                db,
                project,
                changelog_entry_id,
                user,
                lambda permission: permission in principal.permissions,
            )
        except RevertError as exc:
            if exc.status_code == 404:
                raise ToolError(
                    f"Änderung {changelog_entry_id} gehört nicht zu Projekt {project_id} "
                    "(siehe get_project_changelog)."
                ) from exc
            if exc.status_code == 403:
                raise ToolError(
                    "FinVe-Zuordnungen zurücksetzen braucht zusätzlich das Recht 'finve.edit'."
                ) from exc
            raise ToolError(exc.detail) from exc
        latest = get_changelog_crud(db, project.id)
        return {
            "reverted_entry_id": changelog_entry_id,
            "revert_event": _event_dict(latest[0]) if latest else None,
            "project": _project_dict(updated),
        }


def register(server: MCPServer) -> None:
    server.add_tool(get_project_changelog, annotations=READ_ONLY)
    server.add_tool(get_project_text_changelog, annotations=READ_ONLY)
    server.add_tool(revert_project_change, annotations=WRITE)
