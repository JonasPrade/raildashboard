"""Constituencies and members of parliament (feature-abgeordnete.md), read-only.

Two working directions: before an appointment the person is fixed and the
projects are wanted (list_politicians → get_politician); before a campaign the
project is fixed and the contacts are wanted (get_project_constituencies).
Same right as the REST reads: any signed-in user — here, any MCP key. Imports
stay in the admin area (they call external services and overwrite rows).
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.orm import Session

from dashboard_backend.crud import parliament as parliament_crud
from dashboard_backend.mcp.context import get_principal, tool_session
from dashboard_backend.mcp.tools.projects import MAX_LIMIT, READ_ONLY, _project_or_error
from dashboard_backend.models.parliament import IMPORT_KIND_POLITICIANS

CommitteeLiteral = Literal["verkehr", "haushalt"]


def _data_status(db: Session) -> dict[str, Any]:
    """When the members of parliament were last fetched, and whether that is stale."""
    run = parliament_crud.last_successful_run(db, IMPORT_KIND_POLITICIANS)
    period = parliament_crud.current_period(db)
    return {
        "period": period.label if period is not None else None,
        "last_import": run.finished_at.isoformat() if run is not None and run.finished_at else None,
        "is_stale": parliament_crud.is_stale(run),
        "stale_after_days": parliament_crud.STALE_AFTER_DAYS,
    }


def _page(items: list, limit: int, offset: int) -> tuple[list, int]:
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    return items[offset : offset + limit], offset


def list_politicians(
    search: str | None = None,
    committee: CommitteeLiteral | None = None,
    fraction: str | None = None,
    limit: int = 50,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Members of the Bundestag (current period): name, fraction, party, direct
    or list mandate, constituency, committee roles (Verkehr, Haushalt) and the
    number of projects in their constituency. Committee members come first.
    - search: part of the name (umlauts and case ignored)
    - committee: "verkehr" or "haushalt" — members of that committee only
    - fraction: exact fraction label as returned here (e.g. "SPD")
    Paged with limit/offset; ``total`` counts all matches. ``data_status`` says
    when the data was last fetched. Details and the project list of one member:
    get_politician(mandate_id)."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        items = parliament_crud.politician_list(
            db, query=search, committee=committee, fraction=fraction
        )
        page, offset = _page(items, limit, offset)
        return {
            "total": len(items),
            "offset": offset,
            "politicians": [item.model_dump(mode="json") for item in page],
            "data_status": _data_status(db),
        }


def get_politician(mandate_id: int, *, ctx: Context) -> dict[str, Any]:
    """One member of parliament (by mandate_id from list_politicians): mandate,
    constituency, committee roles and the projects in their constituency,
    heaviest first (kilometres in the constituency, share of the project).
    A list mandate without a constituency of its own has no projects here."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        detail = parliament_crud.politician_detail(db, mandate_id)
        if detail is None:
            raise ToolError(f"Mandat {mandate_id} nicht gefunden (siehe list_politicians).")
        data = detail.model_dump(mode="json")
        data["data_status"] = _data_status(db)
        return data


def list_constituencies(
    search: str | None = None,
    state: str | None = None,
    only_with_projects: bool = False,
    limit: int = 50,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Bundestag constituencies (current period) with number, name, state,
    number of projects and mandates and whether a direct mandate exists.
    - search: part of the name or the number ("Ulm", "291")
    - state: Land name as returned here (e.g. "Baden-Württemberg")
    - only_with_projects: only constituencies touched by at least one project
    Paged with limit/offset. Projects and members of one constituency:
    get_constituency."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        items = parliament_crud.constituency_list(db)
        if search and search.strip():
            needle = parliament_crud.normalize_search(search.strip())
            items = [
                item
                for item in items
                if needle in parliament_crud.normalize_search(item.name)
                or search.strip() == str(item.number)
            ]
        if state and state.strip():
            wanted = state.strip().lower()
            items = [item for item in items if (item.state or "").lower() == wanted]
        if only_with_projects:
            items = [item for item in items if item.project_count]
        page, offset = _page(items, limit, offset)
        return {
            "total": len(items),
            "offset": offset,
            "constituencies": [item.model_dump(mode="json") for item in page],
            "data_status": _data_status(db),
        }


def get_constituency(constituency_id: int, *, ctx: Context) -> dict[str, Any]:
    """One constituency (by id from list_constituencies): the projects in it,
    heaviest first, and its members of parliament — direct mandate and the
    members who ran here and entered over the state list."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        detail = parliament_crud.constituency_detail(db, constituency_id)
        if detail is None:
            raise ToolError(f"Wahlkreis {constituency_id} nicht gefunden (siehe list_constituencies).")
        data = detail.model_dump(mode="json")
        data["data_status"] = _data_status(db)
        return data


def get_project_constituencies(project_id: int, *, ctx: Context) -> dict[str, Any]:
    """Constituencies a project touches, heaviest first (``length_km`` in the
    constituency, ``share`` of the project's line; a point project has no
    kilometres), each with its members of parliament and their committee roles.
    The answer to "whom do I talk to about this project?". A project without
    geometry has no constituencies (``has_geometry`` false) — route or draw it
    first (route_project_geometry, edit_project_geometry); the links are rebuilt
    with the geometry."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        data = parliament_crud.project_constituencies(db, project).model_dump(mode="json")
        data["project_name"] = project.name
        data["data_status"] = _data_status(db)
        return data


def register(server: MCPServer) -> None:
    for fn in (
        list_politicians,
        get_politician,
        list_constituencies,
        get_constituency,
        get_project_constituencies,
    ):
        server.add_tool(fn, annotations=READ_ONLY)
