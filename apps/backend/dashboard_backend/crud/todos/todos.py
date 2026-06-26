"""DB access for the to-do (Aufgaben) feature."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from dashboard_backend.models.todos.todo import Todo, TodoAssignee
from dashboard_backend.models.todos.todo_enums import TodoStatus
from dashboard_backend.models.users import User


def _resolve_assignees(db: Session, user_ids: list[int]) -> list[User]:
    """Return the existing users for ``user_ids`` (unknown ids are ignored)."""

    unique_ids = list(dict.fromkeys(user_ids))  # dedupe, keep order
    if not unique_ids:
        return []
    return db.query(User).filter(User.id.in_(unique_ids)).all()


def _sync_assignees(db: Session, todo: Todo, user_ids: list[int]) -> None:
    """Replace the task's assignee set with the given user ids."""

    db.query(TodoAssignee).filter(TodoAssignee.todo_id == todo.id).delete(
        synchronize_session=False
    )
    for user in _resolve_assignees(db, user_ids):
        db.add(TodoAssignee(todo_id=todo.id, user_id=user.id))


def list_todos(
    db: Session,
    *,
    status: str | None = None,
    priority: str | None = None,
    assignee_id: int | None = None,
    project_id: int | None = None,
    created_by_id: int | None = None,
    include_done: bool = True,
) -> list[Todo]:
    query = db.query(Todo)
    if status is not None:
        query = query.filter(Todo.status == status)
    if priority is not None:
        query = query.filter(Todo.priority == priority)
    if project_id is not None:
        query = query.filter(Todo.project_id == project_id)
    if created_by_id is not None:
        query = query.filter(Todo.created_by_id == created_by_id)
    if assignee_id is not None:
        query = query.join(TodoAssignee, TodoAssignee.todo_id == Todo.id).filter(
            TodoAssignee.user_id == assignee_id
        )
    if not include_done:
        query = query.filter(Todo.status != TodoStatus.DONE.value)
    # Open work first, newest first within a status group.
    return (
        query.order_by(
            Todo.completed_at.isnot(None),  # not-done before done
            Todo.due_date.is_(None),  # dated before undated
            Todo.due_date.asc(),
            Todo.created_at.desc(),
        )
        .all()
    )


def get_todo(db: Session, todo_id: int) -> Todo | None:
    return db.query(Todo).filter(Todo.id == todo_id).first()


def create_todo(db: Session, data: dict, user: User | None) -> Todo:
    status = data.get("status", TodoStatus.OPEN.value)
    todo = Todo(
        title=data["title"],
        description=data.get("description"),
        status=status,
        priority=data.get("priority", "MEDIUM"),
        due_date=data.get("due_date"),
        project_id=data.get("project_id"),
        created_by_id=user.id if user else None,
        created_by_username=user.username if user else None,
        completed_at=datetime.utcnow() if status == TodoStatus.DONE.value else None,
    )
    db.add(todo)
    db.flush()  # assign todo.id before linking assignees
    _sync_assignees(db, todo, data.get("assignee_ids") or [])
    db.commit()
    db.refresh(todo)
    return todo


def update_todo(db: Session, todo_id: int, payload: dict) -> Todo | None:
    todo = get_todo(db, todo_id)
    if todo is None:
        return None

    scalar_fields = {"title", "description", "status", "priority", "due_date", "project_id"}
    for key, value in payload.items():
        if key in scalar_fields:
            setattr(todo, key, value)

    # Explicit clears for the nullable fields.
    if payload.get("clear_due_date"):
        todo.due_date = None
    if payload.get("clear_project"):
        todo.project_id = None

    # Keep completed_at in sync with the status transition.
    if "status" in payload:
        if payload["status"] == TodoStatus.DONE.value:
            if todo.completed_at is None:
                todo.completed_at = datetime.utcnow()
        else:
            todo.completed_at = None

    if payload.get("assignee_ids") is not None:
        _sync_assignees(db, todo, payload["assignee_ids"])

    db.commit()
    db.refresh(todo)
    return todo


def delete_todo(db: Session, todo_id: int) -> bool:
    todo = get_todo(db, todo_id)
    if todo is None:
        return False
    db.delete(todo)
    db.commit()
    return True
