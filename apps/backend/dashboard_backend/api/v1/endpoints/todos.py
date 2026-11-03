"""To-do (Aufgaben) endpoints.

Mounted under ``/todos``. Tasks are visible to logged-in users only (no public
GET — every read requires a valid session); mutations require the matching
``todo.*`` capability. The ``tasks`` route namespace is reserved for Celery job
status, so this feature uses ``todo`` throughout the code/URL layer.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from dashboard_backend.core.security import (
    has_effective_permission,
    require_auth,
    require_permission,
)
from dashboard_backend.crud.todos import todos as todos_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.todos.todo_schema import (
    TodoChangeLogSchema,
    TodoCommentCreate,
    TodoCommentSchema,
    TodoCommentUpdate,
    TodoCreate,
    TodoSchema,
    TodoTagSchema,
    TodoTagUpdate,
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
    tag: str | None = Query(default=None, description="Tag name (case-insensitive)"),
    q: str | None = Query(default=None, description="Text search in title and description"),
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
        tag=tag,
        search=q,
    )


@router.get("/tags", response_model=list[TodoTagSchema])
def list_todo_tags(
    current_user: User = Depends(require_auth()),
    db: Session = Depends(get_db),
):
    """All tags with their task count (logged-in users only)."""
    return todos_crud.list_tags(db)


@router.patch("/tags/{tag_id}", response_model=TodoTagSchema)
def update_todo_tag(
    tag_id: int,
    body: TodoTagUpdate,
    current_user: User = Depends(require_permission("todo.edit")),
    db: Session = Depends(get_db),
):
    """Rename a tag or change its description (rename is logged on every task)."""
    tag = todos_crud.get_tag(db, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    try:
        todos_crud.update_tag(db, tag, body.model_dump(exclude_unset=True), current_user)
    except todos_crud.TagNameTaken:
        raise HTTPException(status_code=409, detail="Tag name already exists") from None
    return todos_crud.tag_dict(db, tag)


@router.delete("/tags/{tag_id}", status_code=204)
def delete_todo_tag(
    tag_id: int,
    current_user: User = Depends(require_permission("todo.delete")),
    db: Session = Depends(get_db),
):
    """Remove a tag from all tasks and delete it."""
    tag = todos_crud.get_tag(db, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    todos_crud.delete_tag(db, tag, current_user)


@router.get("/{todo_id}/history", response_model=list[TodoChangeLogSchema])
def get_todo_history(
    todo_id: int,
    current_user: User = Depends(require_auth()),
    db: Session = Depends(get_db),
):
    """Change history of one task, newest first."""
    if todos_crud.get_todo(db, todo_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return todos_crud.list_todo_history(db, todo_id)


@router.get("/{todo_id}/comments", response_model=list[TodoCommentSchema])
def list_todo_comments(
    todo_id: int,
    current_user: User = Depends(require_auth()),
    db: Session = Depends(get_db),
):
    """Comments of one task, oldest first (logged-in users only)."""
    if todos_crud.get_todo(db, todo_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return todos_crud.list_comments(db, todo_id)


@router.post("/{todo_id}/comments", response_model=TodoCommentSchema, status_code=201)
def create_todo_comment(
    todo_id: int,
    body: TodoCommentCreate,
    current_user: User = Depends(require_permission("todo.edit")),
    db: Session = Depends(get_db),
):
    """Add a comment (e.g. the current state of the work). Requires ``todo.edit``."""
    todo = todos_crud.get_todo(db, todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return todos_crud.create_comment(db, todo, body.body, current_user)


@router.patch("/{todo_id}/comments/{comment_id}", response_model=TodoCommentSchema)
def update_todo_comment(
    todo_id: int,
    comment_id: int,
    body: TodoCommentUpdate,
    current_user: User = Depends(require_permission("todo.edit")),
    db: Session = Depends(get_db),
):
    """Edit the text of a comment — only its author may."""
    comment = todos_crud.get_comment(db, todo_id, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the author can edit a comment")
    return todos_crud.update_comment(db, comment, body.body)


@router.delete("/{todo_id}/comments/{comment_id}", status_code=204)
def delete_todo_comment(
    todo_id: int,
    comment_id: int,
    current_user: User = Depends(require_permission("todo.edit")),
    db: Session = Depends(get_db),
):
    """Delete a comment — its author, or anyone holding ``todo.delete``."""
    comment = todos_crud.get_comment(db, todo_id, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and not has_effective_permission(
        current_user, "todo.delete"
    ):
        raise HTTPException(status_code=403, detail="Only the author can delete a comment")
    todos_crud.delete_comment(db, comment)


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
    updated = todos_crud.update_todo(
        db, todo_id, body.model_dump(exclude_unset=True), current_user
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@router.delete("/{todo_id}", status_code=204)
def delete_todo(
    todo_id: int,
    current_user: User = Depends(require_permission("todo.delete")),
    db: Session = Depends(get_db),
):
    if not todos_crud.delete_todo(db, todo_id, current_user):
        raise HTTPException(status_code=404, detail="Task not found")
