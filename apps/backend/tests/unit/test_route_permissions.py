"""Every write route under /api/v1 must name the capability it needs.

The ``AuthRouter`` fallback only demands a login (and rejects API keys), so a
write route without ``require_permission`` is open to every signed-in viewer.
This test fails for any such route that is not a deliberate exception below.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials

from dashboard_backend.routing.auth_router import AuthRouter
from main import app

# Write routes that deliberately carry no capability (method, path).
ALLOWED_WITHOUT_PERMISSION = {
    ("POST", "/api/v1/auth/session"),  # login
    ("DELETE", "/api/v1/auth/session"),  # logout
    ("DELETE", "/api/v1/api-keys/{key_id}"),  # own keys stay revocable
    ("POST", "/api/v1/tasks/debug"),
}


def _has_permission_dependency(dependant) -> bool:
    for sub in dependant.dependencies:
        if getattr(sub.call, "__is_role_dependency__", False) or _has_permission_dependency(sub):
            return True
    return False


def test_every_write_route_requires_a_permission():
    missing = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/v1"):
            continue
        for method in sorted(route.methods - {"GET", "HEAD", "OPTIONS"}):
            if (method, route.path) in ALLOWED_WITHOUT_PERMISSION:
                continue
            if not _has_permission_dependency(route.dependant):
                missing.append(f"{method} {route.path}")
    assert missing == [], f"write routes without require_permission: {missing}"


def test_exceptions_still_exist():
    # A stale exception would silently widen the allow-list for a future route.
    existing = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }
    assert ALLOWED_WITHOUT_PERMISSION <= existing


def test_api_layer_never_calls_user_has_permission():
    # ``User.has_permission`` ignores API-key scopes and lets admin keys bypass
    # them; endpoints check ``has_effective_permission(current_user, key)``.
    api_dir = Path(__file__).resolve().parents[2] / "dashboard_backend" / "api"
    offenders = [
        str(path.relative_to(api_dir))
        for path in sorted(api_dir.rglob("*.py"))
        if ".has_permission(" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_auth_router_fallback_rejects_api_keys():
    router = AuthRouter()

    @router.post("/write")
    def write():  # pragma: no cover - never called
        return None

    route = next(r for r in router.routes if isinstance(r, APIRoute))
    fallback = route.dependencies[-1].dependency
    bearer = HTTPAuthorizationCredentials(scheme="Bearer", credentials="rdb_x")
    with pytest.raises(HTTPException) as exc:
        fallback(session=None, credentials=None, bearer=bearer, db=None)
    assert exc.value.status_code == 403
