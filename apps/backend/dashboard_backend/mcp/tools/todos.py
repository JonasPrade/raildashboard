"""To-do (Aufgaben) tools.

Tags label tasks; ``@LLM`` marks a task that the LLM is to do (fully or in
part) through MCP — filter with ``list_todos(tag="@LLM")``. A task with a part
for Jonas carries ``@Jonas`` too; the LLM part starts once ``@Jonas`` is gone.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError

from dashboard_backend.crud.todos import todos as todos_crud
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.mcp.tools.projects import MAX_LIMIT, READ_ONLY, WRITE
from dashboard_backend.schemas.todos.todo_schema import (
    TodoCreate,
    TodoPriorityLiteral,
    TodoSchema,
    TodoStatusLiteral,
    TodoTagUpdate,
    TodoUpdate,
)


def _todo_dict(todo) -> dict[str, Any]:
    data = TodoSchema.model_validate(todo).model_dump(mode="json")
    data["assignees"] = [a["username"] for a in data["assignees"]]
    data["project"] = data["project"]["name"] if data["project"] else None
    data["tags"] = [t["name"] for t in data["tags"]]
    return data


def list_todos(
    status: TodoStatusLiteral | None = None,
    priority: TodoPriorityLiteral | None = None,
    project_id: int | None = None,
    assignee_id: int | None = None,
    include_done: bool = False,
    tag: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """List tasks (open work first, then by due date). Done tasks are hidden
    unless include_done is true. tag filters by tag name (e.g. "@LLM", see
    list_todo_tags); search matches title and description. Page with
    limit/offset; total counts all matches."""
    get_principal(ctx)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    with tool_session(ctx) as db:
        todos = todos_crud.list_todos(
            db,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            project_id=project_id,
            include_done=include_done,
            tag=tag,
            search=search,
        )
        return {
            "total": len(todos),
            "offset": offset,
            "todos": [_todo_dict(t) for t in todos[offset : offset + limit]],
        }


def list_todo_tags(*, ctx: Context) -> dict[str, Any]:
    """All task tags with their description and number of tasks. "@LLM" marks
    tasks the LLM is to do (fully or in part) through MCP. A task that also
    carries "@Jonas" waits for Jonas' part first: skip it until "@Jonas" is
    removed."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        return {"tags": todos_crud.list_tags(db)}


def update_todo_tag(
    tag: str,
    new_name: str | None = None,
    description: str | None = None,
    clear_description: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Rename a task tag (by its current name) or change its description
    (requires ``todo.edit``). A rename is logged on every task carrying it."""
    principal = get_principal(ctx)
    require(principal, "todo.edit")
    raw: dict[str, Any] = {"name": new_name, "description": description}
    raw = {key: value for key, value in raw.items() if value is not None}
    if clear_description:
        raw["clear_description"] = True
    if not raw:
        raise ToolError("Keine Änderungen übergeben.")
    try:
        payload = TodoTagUpdate(**raw).model_dump(exclude_unset=True)
    except ValidationError as exc:
        raise ToolError(f"Ungültige Werte: {exc}") from exc
    with tool_session(ctx) as db:
        found = todos_crud.get_tag_by_name(db, tag)
        if found is None:
            raise ToolError(f"Tag „{tag}“ nicht gefunden (siehe list_todo_tags).")
        user = load_user(db, principal)
        try:
            todos_crud.update_tag(db, found, payload, user)
        except todos_crud.TagNameTaken as exc:
            raise ToolError(f"Es gibt schon ein Tag „{new_name}“.") from exc
        return todos_crud.tag_dict(db, found)


def create_todo(
    title: str,
    description: str | None = None,
    priority: TodoPriorityLiteral = "MEDIUM",
    due_date: date | None = None,
    project_id: int | None = None,
    assignee_ids: list[int] | None = None,
    tags: list[str] | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Create a task (requires ``todo.create``), optionally linked to a project.
    tags are names; unknown ones are created (e.g. ["@LLM"])."""
    principal = get_principal(ctx)
    require(principal, "todo.create")
    try:
        payload = TodoCreate(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            project_id=project_id,
            assignee_ids=assignee_ids or [],
            tags=tags or [],
        ).model_dump(exclude_unset=True)
    except ValidationError as exc:
        raise ToolError(f"Ungültige Werte: {exc}") from exc
    with tool_session(ctx) as db:
        user = load_user(db, principal)
        return _todo_dict(todos_crud.create_todo(db, payload, user))


def update_todo(
    todo_id: int,
    title: str | None = None,
    description: str | None = None,
    status: TodoStatusLiteral | None = None,
    priority: TodoPriorityLiteral | None = None,
    due_date: date | None = None,
    project_id: int | None = None,
    assignee_ids: list[int] | None = None,
    tags: list[str] | None = None,
    clear_due_date: bool = False,
    clear_project: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Change a task (requires ``todo.edit``). Only passed fields change;
    assignee_ids and tags replace the full set ([] removes all). Use clear_due_date /
    clear_project to remove those values."""
    principal = get_principal(ctx)
    require(principal, "todo.edit")
    fields = {
        "title": title,
        "description": description,
        "status": status,
        "priority": priority,
        "due_date": due_date,
        "project_id": project_id,
        "assignee_ids": assignee_ids,
        "tags": tags,
    }
    raw = {key: value for key, value in fields.items() if value is not None}
    if clear_due_date:
        raw["clear_due_date"] = True
    if clear_project:
        raw["clear_project"] = True
    if not raw:
        raise ToolError("Keine Änderungen übergeben.")
    try:
        payload = TodoUpdate(**raw).model_dump(exclude_unset=True)
    except ValidationError as exc:
        raise ToolError(f"Ungültige Werte: {exc}") from exc
    with tool_session(ctx) as db:
        user = load_user(db, principal)
        updated = todos_crud.update_todo(db, todo_id, payload, user)
        if updated is None:
            raise ToolError(f"Aufgabe {todo_id} nicht gefunden.")
        return _todo_dict(updated)


def register(server: MCPServer) -> None:
    server.add_tool(list_todos, annotations=READ_ONLY)
    server.add_tool(list_todo_tags, annotations=READ_ONLY)
    server.add_tool(create_todo, annotations=WRITE)
    server.add_tool(update_todo, annotations=WRITE)
    server.add_tool(update_todo_tag, annotations=WRITE)
