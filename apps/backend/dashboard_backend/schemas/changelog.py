from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ChangeLogEntryRead(BaseModel):
    id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChangeLogRead(BaseModel):
    id: int
    project_id: int
    user_id: Optional[int] = None
    username_snapshot: Optional[str] = None
    timestamp: datetime
    action: str
    entries: list[ChangeLogEntryRead] = []

    model_config = ConfigDict(from_attributes=True)


class RevertFieldRequest(BaseModel):
    changelog_entry_id: int


class TextChangeLogEntryRead(BaseModel):
    id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TextChangeLogRead(BaseModel):
    id: int
    text_id: Optional[int] = None
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    username_snapshot: Optional[str] = None
    text_header_snapshot: Optional[str] = None
    timestamp: datetime
    action: str
    entries: list[TextChangeLogEntryRead] = []

    model_config = ConfigDict(from_attributes=True)
