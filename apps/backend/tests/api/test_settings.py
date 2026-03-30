"""Tests for the /api/v1/settings/ endpoint."""
from __future__ import annotations

from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


# ---------------------------------------------------------------------------
# GET /api/v1/settings/  (public — no auth needed)
# ---------------------------------------------------------------------------


def test_get_settings_returns_defaults(client):
    resp = client.get("/api/v1/settings/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["map_group_mode"] == "preconfigured"


# ---------------------------------------------------------------------------
# PATCH /api/v1/settings/  (admin only)
# ---------------------------------------------------------------------------


def test_patch_settings_requires_admin(client, create_user):
    create_user("editor", "pass123", UserRole.editor)

    resp = client.patch(
        "/api/v1/settings/",
        json={"map_group_mode": "all"},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 403


def test_patch_settings_requires_auth(client):
    resp = client.patch("/api/v1/settings/", json={"map_group_mode": "all"})
    assert resp.status_code == 401


def test_patch_settings_success(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)

    resp = client.patch(
        "/api/v1/settings/",
        json={"map_group_mode": "all"},
        headers=basic_auth_header("admin", "adminpass"),
    )
    assert resp.status_code == 200
    assert resp.json()["map_group_mode"] == "all"


def test_patch_settings_invalid_value(client, create_user):
    create_user("admin2", "adminpass", UserRole.admin)

    resp = client.patch(
        "/api/v1/settings/",
        json={"map_group_mode": "invalid_value"},
        headers=basic_auth_header("admin2", "adminpass"),
    )
    assert resp.status_code == 422


def test_settings_roundtrip(client, create_user):
    """GET → PATCH → GET confirms the value was persisted."""
    create_user("admin3", "adminpass", UserRole.admin)

    # Initially defaults to "preconfigured"
    resp = client.get("/api/v1/settings/")
    assert resp.json()["map_group_mode"] == "preconfigured"

    # Patch to "all"
    client.patch(
        "/api/v1/settings/",
        json={"map_group_mode": "all"},
        headers=basic_auth_header("admin3", "adminpass"),
    )

    # Verify change persisted
    resp = client.get("/api/v1/settings/")
    assert resp.json()["map_group_mode"] == "all"
