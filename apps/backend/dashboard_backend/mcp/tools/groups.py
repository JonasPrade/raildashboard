"""Project-group maintenance and the group timeline.

Creating a group and changing memberships live in ``projects.py``
(create_project_group, set_project_groups); here a group's own settings change
and its timeline is read. Deleting a group stays in the UI.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from dashboard_backend.crud.projects.progress_timeline import get_group_timeline
from dashboard_backend.crud.projects.project_groups import update_project_group as update_group_crud
from dashboard_backend.mcp.context import get_principal, require, tool_session
from dashboard_backend.mcp.tools.projects import READ_ONLY, WRITE, _group_filter
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.schemas.projects.progress_schema import (
    ProjectGroupTimelineSchema,
    SkippablePhaseLiteral,
)
from dashboard_backend.schemas.projects.project_group_schema import ProjectGroupUpdate


def _group_or_error(db: Session, group: str) -> ProjectGroup:
    found = db.query(ProjectGroup).filter(_group_filter(str(group))).all()
    if not found:
        raise ToolError(f"Projektgruppe „{group}“ nicht gefunden (siehe list_project_groups).")
    if len(found) > 1:
        raise ToolError(
            f"„{group}“ passt auf mehrere Gruppen ({', '.join(str(g.id) for g in found)}) — "
            "bitte die id angeben."
        )
    return found[0]


def _group_dict(group: ProjectGroup) -> dict[str, Any]:
    return {
        "id": group.id,
        "short_name": group.short_name,
        "name": group.name,
        "description": group.description,
        "color": group.color,
        "public": group.public,
        "plot_only_superior_projects": group.plot_only_superior_projects,
        "is_visible": group.is_visible,
        "is_default_selected": group.is_default_selected,
        "skipped_phases": list(group.skipped_phases or []),
        "assumed_build_months": group.assumed_build_months,
    }


def update_project_group(
    group: str,
    name: str | None = None,
    short_name: str | None = None,
    description: str | None = None,
    color: str | None = None,
    public: bool | None = None,
    plot_only_superior_projects: bool | None = None,
    is_visible: bool | None = None,
    is_default_selected: bool | None = None,
    skipped_phases: list[SkippablePhaseLiteral] | None = None,
    assumed_build_months: int | None = None,
    clear_assumed_build_months: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Change a project group's settings (requires ``projectgroup.edit``).
    group: id, short name or name (see list_project_groups). Only passed fields
    change.
    - short_name: max. 20 characters, unique; name: max. 100
    - public: shown to visitors; is_visible / is_default_selected: map layer
    - skipped_phases: planning phases this group's projects usually skip
      (hidden in the progress view and forecast when all groups of a project
      skip them); [] clears
    - assumed_build_months: assumed construction period (1–120) for the
      forecast; clear_assumed_build_months=true removes it
    Group changes are not in a project changelog. Returns the group."""
    principal = get_principal(ctx)
    require(principal, "projectgroup.edit")
    raw: dict[str, Any] = {
        key: value
        for key, value in {
            "name": name.strip() if name is not None else None,
            "short_name": short_name.strip() if short_name is not None else None,
            "description": description,
            "color": color.strip() if color is not None else None,
            "public": public,
            "plot_only_superior_projects": plot_only_superior_projects,
            "is_visible": is_visible,
            "is_default_selected": is_default_selected,
            "skipped_phases": skipped_phases,
            "assumed_build_months": assumed_build_months,
        }.items()
        if value is not None
    }
    if clear_assumed_build_months:
        if assumed_build_months is not None:
            raise ToolError("assumed_build_months und clear_assumed_build_months schließen sich aus.")
        raw["assumed_build_months"] = None
    if not raw:
        raise ToolError("Keine Änderungen übergeben.")
    if raw.get("name") == "" or raw.get("short_name") == "":
        raise ToolError("name und short_name dürfen nicht leer sein.")
    if len(raw.get("name") or "") > 100 or len(raw.get("short_name") or "") > 20 or len(raw.get("color") or "") > 10:
        raise ToolError("Zu lang: name max. 100, short_name max. 20, color max. 10 Zeichen.")
    try:
        updates = ProjectGroupUpdate(**raw).model_dump(exclude_unset=True)
    except ValidationError as exc:
        raise ToolError(f"Ungültige Werte: {exc}") from exc

    with tool_session(ctx) as db:
        target = _group_or_error(db, group)
        new_short = updates.get("short_name")
        if new_short is not None:
            clash = (
                db.query(ProjectGroup)
                .filter(_group_filter(new_short), ProjectGroup.id != target.id)
                .first()
            )
            if clash is not None:
                raise ToolError(f"Kurzname oder Name „{new_short}“ ist schon vergeben (Gruppe {clash.id}).")
        updated = update_group_crud(db, target.id, updates)
        return _group_dict(updated)


def get_project_group_timeline(
    group: str, only_superior: bool = True, *, ctx: Context
) -> dict[str, Any]:
    """Timeline of a project group: the dated milestones (VIB-PFA, Fulda-Runde,
    manual expected entries, Planfeststellung, parliamentary dates) of its
    projects, as on the group's timeline page. Only projects with at least one
    concrete date are listed; ``without_dates_count`` counts the rest. BVWP
    estimates are never used. only_superior=true (default) skips subprojects —
    a parent already pools its subtree's dates. group: id, short name or name."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        target = _group_or_error(db, group)
        payload = get_group_timeline(db, target.id, only_superior=only_superior)
        data = ProjectGroupTimelineSchema.model_validate(payload).model_dump(mode="json")
        data["group"] = {"id": target.id, "short_name": target.short_name, "name": target.name}
        return data


def register(server: MCPServer) -> None:
    server.add_tool(update_project_group, annotations=WRITE)
    server.add_tool(get_project_group_timeline, annotations=READ_ONLY)
