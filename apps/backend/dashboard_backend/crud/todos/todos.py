"""DB access for the to-do (Aufgaben) feature."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from dashboard_backend.models.todos.todo import (
    Todo,
    TodoAssignee,
    TodoChangeLog,
    TodoChangeLogEntry,
    TodoTag,
    TodoTagLink,
)
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


def _resolve_tags(db: Session, names: list[str]) -> list[TodoTag]:
    """Return the tags for ``names`` (case-insensitive), creating missing ones.

    ``names`` is expected normalized (see ``schemas.todos.normalize_tag_names``).
    """

    tags: list[TodoTag] = []
    for name in names:
        tag = db.query(TodoTag).filter(func.lower(TodoTag.name) == name.lower()).first()
        if tag is None:
            tag = TodoTag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


# --- History -----------------------------------------------------------------

_TRACKED_FIELDS = ("title", "description", "status", "priority", "due_date", "project_id")


def _snapshot(todo: Todo) -> dict[str, str | None]:
    """String view of every tracked field, as stored in the change log."""

    snap: dict[str, str | None] = {}
    for field in _TRACKED_FIELDS:
        value = getattr(todo, field)
        snap[field] = None if value is None else str(value)
    snap["assignees"] = ", ".join(sorted(u.username for u in todo.assignees)) or None
    snap["tags"] = ", ".join(sorted((t.name for t in todo.tags), key=str.lower)) or None
    return snap


def _log_change(
    db: Session,
    todo: Todo,
    user: User | None,
    action: str,
    before: dict[str, str | None],
    after: dict[str, str | None],
) -> None:
    """Add a change-log row with one entry per changed field (no row if nothing changed)."""

    changed = [field for field in after if before.get(field) != after[field]]
    if not changed and action == "PATCH":
        return
    log = TodoChangeLog(
        todo_id=todo.id,
        todo_title_snapshot=todo.title,
        user_id=user.id if user else None,
        username_snapshot=user.username if user else None,
        action=action,
    )
    for field in changed:
        log.entries.append(
            TodoChangeLogEntry(field_name=field, old_value=before.get(field), new_value=after[field])
        )
    db.add(log)


def list_todo_history(db: Session, todo_id: int) -> list[TodoChangeLog]:
    return (
        db.query(TodoChangeLog)
        .filter(TodoChangeLog.todo_id == todo_id)
        .order_by(TodoChangeLog.timestamp.desc(), TodoChangeLog.id.desc())
        .all()
    )


# --- Tags --------------------------------------------------------------------


def list_tags(db: Session) -> list[dict]:
    """All tags with the number of tasks carrying them, alphabetically."""

    rows = (
        db.query(TodoTag, func.count(TodoTagLink.todo_id))
        .outerjoin(TodoTagLink, TodoTagLink.tag_id == TodoTag.id)
        .group_by(TodoTag.id)
        .order_by(func.lower(TodoTag.name))
        .all()
    )
    return [
        {"id": tag.id, "name": tag.name, "description": tag.description, "todo_count": count}
        for tag, count in rows
    ]


# --- Tasks -------------------------------------------------------------------


def list_todos(
    db: Session,
    *,
    status: str | None = None,
    priority: str | None = None,
    assignee_id: int | None = None,
    project_id: int | None = None,
    created_by_id: int | None = None,
    include_done: bool = True,
    tag: str | None = None,
    search: str | None = None,
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
    if tag:
        query = (
            query.join(TodoTagLink, TodoTagLink.todo_id == Todo.id)
            .join(TodoTag, TodoTag.id == TodoTagLink.tag_id)
            .filter(func.lower(TodoTag.name) == tag.strip().lower())
        )
    if search and search.strip():
        pattern = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Todo.title).like(pattern),
                func.lower(func.coalesce(Todo.description, "")).like(pattern),
            )
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
    todo.tags = _resolve_tags(db, data.get("tags") or [])
    db.flush()
    db.refresh(todo)  # reload assignees for the snapshot
    _log_change(db, todo, user, "CREATE", {}, _snapshot(todo))
    db.commit()
    db.refresh(todo)
    return todo


def update_todo(
    db: Session, todo_id: int, payload: dict, user: User | None = None
) -> Todo | None:
    todo = get_todo(db, todo_id)
    if todo is None:
        return None
    before = _snapshot(todo)

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
    if payload.get("tags") is not None:
        todo.tags = _resolve_tags(db, payload["tags"])

    db.flush()
    db.refresh(todo)  # reload assignees for the snapshot
    _log_change(db, todo, user, "PATCH", before, _snapshot(todo))
    db.commit()
    db.refresh(todo)
    return todo


def delete_todo(db: Session, todo_id: int, user: User | None = None) -> bool:
    todo = get_todo(db, todo_id)
    if todo is None:
        return False
    _log_change(db, todo, user, "DELETE", _snapshot(todo), {})
    db.flush()
    db.delete(todo)
    db.commit()
    return True
