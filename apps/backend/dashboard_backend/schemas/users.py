from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRole(str, Enum):
    viewer = "viewer"
    editor = "editor"
    admin = "admin"


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    # Role name (system role or a custom role).
    role: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    id: int
    username: str
    role: str
    permissions: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("role", mode="before")
    @classmethod
    def _role_to_name(cls, value: object) -> object:
        # Accept either the related Role object or a plain role-name string.
        return getattr(value, "name", value)


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    role: str | None = Field(default=None, min_length=1, max_length=50)


class UserPasswordUpdate(BaseModel):
    password: str = Field(min_length=8, max_length=128)
