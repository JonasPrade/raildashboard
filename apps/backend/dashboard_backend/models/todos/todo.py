"""To-do (Aufgabe) records.

A task either belongs to one project (``project_id``) or is a free standalone
note (``project_id is None``). Assignment to users is many-to-many through
``todo_assignee``. See ``docs/features/feature-tasks.md``.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base
from dashboard_backend.models.todos.todo_enums import TodoPriority, TodoStatus


class TodoAssignee(Base):
    """Association of a user to a to-do (many-to-many)."""

    __tablename__ = "todo_assignee"

    todo_id: Mapped[int] = mapped_column(
        ForeignKey("todo.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )


class Todo(Base):
    __tablename__ = "todo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=TodoStatus.OPEN.value, server_default=TodoStatus.OPEN.value,
    )
    priority: Mapped[str] = mapped_column(
        String(10), nullable=False,
        default=TodoPriority.MEDIUM.value, server_default=TodoPriority.MEDIUM.value,
    )
    due_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)

    # Optional project link — NULL means a free standalone note. SET NULL on
    # project delete so the task survives.
    project_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("project.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Author snapshot (username survives a later user deletion).
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_username: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    assignees: Mapped[list["User"]] = relationship(  # noqa: F821
        "User",
        secondary="todo_assignee",
        lazy="selectin",
    )
    # Lazy "select" (not "joined"): a many-to-one whose FK is NULL resolves to
    # None without emitting SQL, so standalone tasks never touch the project
    # table (keeps the test schema, which omits ``project``, working).
    project: Mapped["Project | None"] = relationship(  # noqa: F821
        "Project", lazy="select", viewonly=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Todo(id={self.id}, status={self.status}, title={self.title!r})>"
