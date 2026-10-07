"""To-do (Aufgaben) tools."""

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
    TodoUpdate,
)


def _todo_dict(todo) -> dict[str, Any]:
    data = TodoSchema.model_validate(todo).model_dump(mode="json")
    data["assignees"] = [a["username"] for a in data["assignees"]]
    data["project"] = data["project"]["name"] if data["project"] else None
    return data


def list_todos(
    status: TodoStatusLiteral | None = None,
    priority: TodoPriorityLiteral | None = None,
    project_id: int | None = None,
    assignee_id: int | None = None,
    include_done: bool = False,
    limit: int = 50,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """List tasks (open work first, then by due date). Done tasks are hidden
    unless include_done is true."""
    get_principal(ctx)
    limit = max(1, min(limit, MAX_LIMIT))
    with tool_session(ctx) as db:
        todos = todos_crud.list_todos(
            db,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            project_id=project_id,
            include_done=include_done,
        )
        return {"total": len(todos), "todos": [_todo_dict(t) for t in todos[:limit]]}


def create_todo(
    title: str,
    description: str | None = None,
    priority: TodoPriorityLiteral = "MEDIUM",
    due_date: date | None = None,
    project_id: int | None = None,
    assignee_ids: list[int] | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Create a task (requires ``todo.create``), optionally linked to a project."""
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
    clear_due_date: bool = False,
    clear_project: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Change a task (requires ``todo.edit``). Only passed fields change;
    assignee_ids replaces the full assignee set. Use clear_due_date /
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
        updated = todos_crud.update_todo(db, todo_id, payload)
        if updated is None:
            raise ToolError(f"Aufgabe {todo_id} nicht gefunden.")
        return _todo_dict(updated)


def register(server: MCPServer) -> None:
    server.add_tool(list_todos, annotations=READ_ONLY)
    server.add_tool(create_todo, annotations=WRITE)
    server.add_tool(update_todo, annotations=WRITE)
