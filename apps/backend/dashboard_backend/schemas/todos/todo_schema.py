"""Pydantic schemas for the to-do (Aufgaben) feature.

Status/priority use ``Literal[...]`` (not the Python enum) so the generated
TypeScript client gets clean string-union types. The nullable ``due_date`` and
``project_id`` use ``clear_*`` sentinels on update to disambiguate "set to null"
from "not provided" (mirrors the project-progress update schema).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TodoStatusLiteral = Literal["OPEN", "IN_PROGRESS", "DONE"]
TodoPriorityLiteral = Literal["LOW", "MEDIUM", "HIGH"]


class TodoUserRef(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class TodoProjectRef(BaseModel):
    id: int
    name: str
    project_number: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TodoSchema(BaseModel):
    id: int
    title: str
    description: str | None
    status: TodoStatusLiteral
    priority: TodoPriorityLiteral
    due_date: date | None
    project_id: int | None
    project: TodoProjectRef | None
    assignees: list[TodoUserRef]
    created_by_id: int | None
    created_by_username: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10000)
    status: TodoStatusLiteral = "OPEN"
    priority: TodoPriorityLiteral = "MEDIUM"
    due_date: date | None = None
    project_id: int | None = None
    assignee_ids: list[int] = Field(default_factory=list)


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10000)
    status: TodoStatusLiteral | None = None
    priority: TodoPriorityLiteral | None = None
    due_date: date | None = None
    project_id: int | None = None
    # When provided, replaces the full assignee set.
    assignee_ids: list[int] | None = None
    # Explicit clears (None is otherwise ambiguous with "not provided").
    # ``Optional[bool] = None`` (not ``bool = False``) keeps the generated TS
    # field optional, matching the project's update-schema convention.
    clear_due_date: bool | None = None
    clear_project: bool | None = None
