"""Pydantic schemas for the to-do (Aufgaben) feature.

Status/priority use ``Literal[...]`` (not the Python enum) so the generated
TypeScript client gets clean string-union types. The nullable ``due_date`` and
``project_id`` use ``clear_*`` sentinels on update to disambiguate "set to null"
from "not provided" (mirrors the project-progress update schema).

Tags travel as plain names on write (unknown names are created on the fly) and
as ``{id, name, description}`` on read.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TodoStatusLiteral = Literal["OPEN", "IN_PROGRESS", "DONE"]
TodoPriorityLiteral = Literal["LOW", "MEDIUM", "HIGH"]

TAG_NAME_MAX = 50


def normalize_tag_names(names: list[str] | None) -> list[str] | None:
    """Strip names, drop blanks and case-insensitive duplicates (first spelling wins)."""

    if names is None:
        return None
    seen: set[str] = set()
    result: list[str] = []
    for raw in names:
        name = " ".join(raw.split())
        if not name or name.lower() in seen:
            continue
        if len(name) > TAG_NAME_MAX:
            raise ValueError(f"Tag „{name}“ ist länger als {TAG_NAME_MAX} Zeichen.")
        seen.add(name.lower())
        result.append(name)
    return result


class TodoUserRef(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class TodoProjectRef(BaseModel):
    id: int
    name: str
    project_number: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TodoTagRef(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TodoTagSchema(TodoTagRef):
    todo_count: int = 0


class TodoTagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=TAG_NAME_MAX)
    description: str | None = Field(default=None, max_length=1000)
    # Explicit clear (None is otherwise ambiguous with "not provided").
    clear_description: bool | None = None

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = " ".join(value.split())
        if not name:
            raise ValueError("Der Tag-Name darf nicht leer sein.")
        return name


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
    tags: list[TodoTagRef] = Field(default_factory=list)
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
    tags: list[str] = Field(default_factory=list)

    _normalize_tags = field_validator("tags")(normalize_tag_names)


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10000)
    status: TodoStatusLiteral | None = None
    priority: TodoPriorityLiteral | None = None
    due_date: date | None = None
    project_id: int | None = None
    # When provided, replaces the full assignee set.
    assignee_ids: list[int] | None = None
    # When provided, replaces the full tag set (names; unknown ones are created).
    tags: list[str] | None = None

    _normalize_tags = field_validator("tags")(normalize_tag_names)
    # Explicit clears (None is otherwise ambiguous with "not provided").
    # ``Optional[bool] = None`` (not ``bool = False``) keeps the generated TS
    # field optional, matching the project's update-schema convention.
    clear_due_date: bool | None = None
    clear_project: bool | None = None


class TodoChangeLogEntrySchema(BaseModel):
    field_name: str
    old_value: str | None
    new_value: str | None

    model_config = ConfigDict(from_attributes=True)


class TodoChangeLogSchema(BaseModel):
    id: int
    todo_id: int | None
    username_snapshot: str | None
    timestamp: datetime
    action: str
    entries: list[TodoChangeLogEntrySchema]

    model_config = ConfigDict(from_attributes=True)
