"""Per-request principal and database access for MCP tools.

The ASGI auth middleware (``mcp/auth.py``) resolves the bearer key and stores a
:class:`McpPrincipal` plus the session provider in the request scope; tools read
both back through the SDK ``Context``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass

from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.orm import Session

from dashboard_backend.crud import users as users_crud
from dashboard_backend.models.users import User

SessionProvider = Callable[[], AbstractContextManager[Session]]

PRINCIPAL_STATE_KEY = "mcp_principal"
SESSION_PROVIDER_STATE_KEY = "mcp_session_provider"


@dataclass(frozen=True)
class McpPrincipal:
    user_id: int
    username: str
    api_key_id: int
    # Effective capabilities of the key: owner's set ∩ key scopes (no admin bypass).
    permissions: frozenset[str]


def _scope_state(ctx: Context) -> dict:
    request = ctx.request_context.request
    if request is None:
        raise ToolError("Kein HTTP-Kontext für diesen Aufruf.")
    return request.scope.get("state", {})


def get_principal(ctx: Context) -> McpPrincipal:
    principal = _scope_state(ctx).get(PRINCIPAL_STATE_KEY)
    if not isinstance(principal, McpPrincipal):
        raise ToolError("Nicht authentifiziert.")
    return principal


def require(principal: McpPrincipal, permission: str) -> None:
    if permission not in principal.permissions:
        raise ToolError(
            f"Dieser API-Key hat nicht das Recht '{permission}'. "
            "Der Nutzer braucht die Berechtigung, und der Key darf nicht auf "
            "Nur-Lesen eingeschränkt sein."
        )


@contextmanager
def tool_session(ctx: Context) -> Iterator[Session]:
    provider: SessionProvider | None = _scope_state(ctx).get(SESSION_PROVIDER_STATE_KEY)
    if provider is None:
        raise ToolError("Keine Datenbankverbindung verfügbar.")
    with provider() as db:
        yield db


def load_user(db: Session, principal: McpPrincipal) -> User:
    user = users_crud.get_user_by_id(db, principal.user_id)
    if user is None:
        raise ToolError("Der Nutzer dieses API-Keys existiert nicht mehr.")
    return user
