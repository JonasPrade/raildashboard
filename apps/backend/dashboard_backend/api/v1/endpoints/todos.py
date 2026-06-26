"""To-do (Aufgaben) endpoints.

Mounted under ``/todos``. Tasks are visible to logged-in users only (no public
GET — every read requires a valid session); mutations require the matching
``todo.*`` capability. The ``tasks`` route namespace is reserved for Celery job
status, so this feature uses ``todo`` throughout the code/URL layer.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_auth, require_permission
from dashboard_backend.crud.todos import todos as todos_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.todos.todo_schema import (
    TodoCreate,
    TodoSchema,
    TodoUpdate,
)

router = AuthRouter()


@router.get("/", response_model=list[TodoSchema])
def list_todos(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    assignee_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    created_by_id: int | None = Query(default=None),
    include_done: bool = Query(default=True),
    current_user: User = Depends(require_auth()),
    db: Session = Depends(get_db),
):
    """List tasks (logged-in users only), with optional filters."""
    return todos_crud.list_todos(
        db,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        project_id=project_id,
        created_by_id=created_by_id,
        include_done=include_done,
    )


@router.get("/{todo_id}", response_model=TodoSchema)
def get_todo(
    todo_id: int,
    current_user: User = Depends(require_auth()),
    db: Session = Depends(get_db),
):
    todo = todos_crud.get_todo(db, todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return todo


@router.post("/", response_model=TodoSchema, status_code=201)
def create_todo(
    body: TodoCreate,
    current_user: User = Depends(require_permission("todo.create")),
    db: Session = Depends(get_db),
):
    return todos_crud.create_todo(db, body.model_dump(exclude_unset=True), current_user)


@router.patch("/{todo_id}", response_model=TodoSchema)
def update_todo(
    todo_id: int,
    body: TodoUpdate,
    current_user: User = Depends(require_permission("todo.edit")),
    db: Session = Depends(get_db),
):
    updated = todos_crud.update_todo(db, todo_id, body.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@router.delete("/{todo_id}", status_code=204)
def delete_todo(
    todo_id: int,
    current_user: User = Depends(require_permission("todo.delete")),
    db: Session = Depends(get_db),
):
    if not todos_crud.delete_todo(db, todo_id):
        raise HTTPException(status_code=404, detail="Task not found")
