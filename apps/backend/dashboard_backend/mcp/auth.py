"""Bearer-key authentication in front of the MCP transport.

Only ``Authorization: Bearer rdb_…`` is accepted here — no session cookie and no
HTTP Basic, so a browser can never be tricked into driving the MCP endpoint
(which is also why the SDK's DNS-rebinding check can stay off). The key must
carry ``mcp.access``; without a valid key → 401 with ``WWW-Authenticate:
Bearer`` (where an OAuth ``resource_metadata`` hint goes later), without the
capability → 403.
"""

from __future__ import annotations

import anyio
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from dashboard_backend.core.api_keys import MCP_PERMISSION
from dashboard_backend.crud import api_keys as api_keys_crud
from dashboard_backend.mcp.context import (
    PRINCIPAL_STATE_KEY,
    SESSION_PROVIDER_STATE_KEY,
    McpPrincipal,
    SessionProvider,
)


def _bearer_token(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            scheme, _, token = value.decode("latin-1").partition(" ")
            if scheme.lower() == "bearer" and token.strip():
                return token.strip()
            return None
    return None


def _error(status_code: int, detail: str) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse({"detail": detail}, status_code=status_code, headers=headers)


class McpAuthMiddleware:
    def __init__(self, app: ASGIApp, session_provider: SessionProvider) -> None:
        self.app = app
        self.session_provider = session_provider

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token = _bearer_token(scope)
        if token is None:
            await _error(401, "API key required (Authorization: Bearer rdb_…)")(scope, receive, send)
            return

        # Blocking DB lookup → worker thread, like FastAPI does for sync dependencies.
        principal = await anyio.to_thread.run_sync(self._resolve, token)
        if principal is None:
            await _error(401, "Invalid or expired API key")(scope, receive, send)
            return
        if MCP_PERMISSION not in principal.permissions:
            await _error(403, f"API key lacks the '{MCP_PERMISSION}' permission")(scope, receive, send)
            return

        state = scope.setdefault("state", {})
        state[PRINCIPAL_STATE_KEY] = principal
        state[SESSION_PROVIDER_STATE_KEY] = self.session_provider
        await self.app(scope, receive, send)

    def _resolve(self, token: str) -> McpPrincipal | None:
        with self.session_provider() as db:
            api_key = api_keys_crud.authenticate_token(db, token)
            if api_key is None:
                return None
            return McpPrincipal(
                user_id=api_key.user_id,
                username=api_key.user.username,
                api_key_id=api_key.id,
                permissions=frozenset(api_keys_crud.effective_key_permissions(api_key)),
            )
