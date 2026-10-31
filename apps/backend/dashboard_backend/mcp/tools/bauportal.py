"""DB-Bauportal tools: read the fetched entries and maintain their project
assignment. Fetching from the external API stays in the admin area.

Same right as the REST endpoints (``progress.edit``), also for reading.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from dashboard_backend.crud import bauportal as bauportal_crud
from dashboard_backend.crud.projects.archive import archived_warnings
from dashboard_backend.mcp.context import get_principal, require, tool_session
from dashboard_backend.mcp.tools.projects import READ_ONLY, WRITE

PERMISSION = "progress.edit"

_COMPACT = (
    "id",
    "bauportal_id",
    "shorttitle",
    "status_raw",
    "projecttime_raw",
    "url",
    "project_id",
    "project_name",
    "suggested_project_id",
    "suggested_project_name",
    "confirmed",
    "fetched_at",
)


def _json(entry: dict) -> dict:
    out = dict(entry)
    if out.get("fetched_at") is not None:
        out["fetched_at"] = out["fetched_at"].isoformat()
    return out


def list_bauportal_entries(
    search: str | None = None,
    project_id: int | None = None,
    only_unconfirmed: bool = False,
    only_without_project: bool = False,
    limit: int = 100,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """DB-Bauportal entries, compact (requires ``progress.edit``): id,
    bauportal_id, shorttitle, status_raw, projecttime_raw, url, project_id with
    name, suggested project, confirmed, fetched_at. Unconfirmed first.
    search: part of the title. project_id: entries assigned to this project.
    only_unconfirmed: not yet confirmed. only_without_project: no project
    assigned. Paged with limit/offset; ``total`` counts all matches. One entry
    in full (raw record, mapped phase): get_bauportal_entry."""
    require(get_principal(ctx), PERMISSION)
    limit = max(1, min(limit, 500))
    with tool_session(ctx) as db:
        rows = bauportal_crud.list_entries(
            db,
            only_unconfirmed=only_unconfirmed,
            search=search,
            project_id=project_id,
            only_without_project=only_without_project,
        )
    page = rows[max(offset, 0) : max(offset, 0) + limit]
    return {
        "total": len(rows),
        "entries": [_json({k: r[k] for k in _COMPACT}) for r in page],
    }


def get_bauportal_entry(entry_id: int, *, ctx: Context) -> dict[str, Any]:
    """One DB-Bauportal entry in full (requires ``progress.edit``): all fields,
    the stored raw API record (``raw_json``) and ``mapped_phase`` — the main
    phase the status feeds into the planning state once the entry is confirmed
    (null for mixed/umbrella entries, which contribute nothing)."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        entry = bauportal_crud.get_entry(db, entry_id)
        if entry is None:
            raise ToolError(f"Bauportal-Eintrag {entry_id} gibt es nicht.")
        return _json(entry)


def assign_bauportal_entry(
    entry_id: int,
    project_id: int | None = None,
    confirmed: bool | None = None,
    clear_project: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Set, clear or confirm the project of a DB-Bauportal entry (requires
    ``progress.edit``), like PATCH /import/bauportal/entries/{id}.
    - project_id: assign this project (stays unconfirmed unless confirmed=true)
    - clear_project=true: remove the assignment (also drops confirmation)
    - confirmed=true: confirm the match (needs a project); only confirmed
      entries feed the planning state — the derived BAUPORTAL observation of
      the affected projects is re-materialised right away. confirmed=false
      withdraws the confirmation.
    Give at least one of project_id, clear_project, confirmed."""
    require(get_principal(ctx), PERMISSION)
    if project_id is not None and clear_project:
        raise ToolError("project_id und clear_project schließen sich aus.")
    payload: dict[str, Any] = {}
    if project_id is not None:
        payload["project_id"] = project_id
    elif clear_project:
        payload["project_id"] = None
    if confirmed is not None:
        payload["confirmed"] = confirmed
    if not payload:
        raise ToolError("Nichts zu tun: project_id, clear_project oder confirmed angeben.")
    with tool_session(ctx) as db:
        try:
            entry = bauportal_crud.update_entry(db, entry_id, payload)
        except bauportal_crud.ProjectNotFoundError as exc:
            raise ToolError(str(exc)) from exc
        if entry is None:
            raise ToolError(f"Bauportal-Eintrag {entry_id} gibt es nicht.")
        out = _json(entry)
        if confirmed and not entry["confirmed"]:
            out["warnings"] = ["Nicht bestätigt: dem Eintrag ist kein Projekt zugeordnet."]
        if entry["project_id"] is not None:
            warnings = archived_warnings(db, [entry["project_id"]])
            if warnings:
                out.setdefault("warnings", []).extend(warnings)
        return out


def register(server: MCPServer) -> None:
    for fn in (list_bauportal_entries, get_bauportal_entry):
        server.add_tool(fn, annotations=READ_ONLY)
    server.add_tool(assign_bauportal_entry, annotations=WRITE)
