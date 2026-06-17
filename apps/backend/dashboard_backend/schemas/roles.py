from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PermissionSchema(BaseModel):
    """A single capability in the catalog (for the admin UI)."""

    key: str
    label: str
    group: str


class RoleRead(BaseModel):
    id: int
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("permissions", mode="before")
    @classmethod
    def _permission_keys(cls, value: object) -> object:
        # Accept the Role.permissions relationship (RolePermission rows) or keys.
        if isinstance(value, (list, tuple, set)):
            return sorted(getattr(item, "permission_key", item) for item in value)
        return value


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] | None = None
