from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # None = every capability of the owner; a list narrows the key to those keys
    # (e.g. ``["mcp.access"]`` = read-only MCP key). Unknown keys are rejected.
    scopes: list[str] | None = None


class ApiKeyRead(BaseModel):
    """Key metadata — never contains the token or its hash."""

    id: int
    name: str
    prefix: str
    scopes: list[str] | None
    user_id: int
    username: str
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_key(cls, api_key) -> "ApiKeyRead":
        return cls(
            id=api_key.id,
            name=api_key.name,
            prefix=api_key.prefix,
            scopes=api_key.scopes,
            user_id=api_key.user_id,
            username=api_key.user.username,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            expires_at=api_key.expires_at,
            revoked_at=api_key.revoked_at,
        )


class ApiKeyCreated(ApiKeyRead):
    """Creation response: the only place the clear-text token ever appears."""

    token: str
