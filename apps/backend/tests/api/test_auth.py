"""Tests for the /api/v1/auth/session endpoint."""
from __future__ import annotations

from dashboard_backend.core.security import _SESSION_COOKIE, create_session_token
from dashboard_backend.schemas.users import UserRole


# ---------------------------------------------------------------------------
# POST /api/v1/auth/session — login
# ---------------------------------------------------------------------------


def test_login_success_sets_cookie(client, create_user):
    create_user("alice", "correct123", UserRole.viewer)

    resp = client.post(
        "/api/v1/auth/session",
        json={"username": "alice", "password": "correct123"},
    )
    assert resp.status_code == 204
    assert _SESSION_COOKIE in resp.cookies


def test_login_wrong_password(client, create_user):
    create_user("alice", "correct123", UserRole.viewer)

    resp = client.post(
        "/api/v1/auth/session",
        json={"username": "alice", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post(
        "/api/v1/auth/session",
        json={"username": "nobody", "password": "anything"},
    )
    assert resp.status_code == 401


def test_login_missing_fields(client):
    resp = client.post("/api/v1/auth/session", json={"username": "alice"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/auth/session — logout
# ---------------------------------------------------------------------------


def test_logout_without_session_returns_401(client):
    resp = client.delete("/api/v1/auth/session")
    assert resp.status_code == 401


def test_logout_with_valid_session(client, create_user):
    user = create_user("alice", "pass123", UserRole.viewer)
    token = create_session_token(user.id)

    resp = client.delete(
        "/api/v1/auth/session",
        cookies={_SESSION_COOKIE: token},
    )
    assert resp.status_code == 204
