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


# ---------------------------------------------------------------------------
# Legal pages (Impressum, Datenschutz)
# ---------------------------------------------------------------------------

LEGAL_FIELDS = ("impressum_url", "impressum_markdown", "datenschutz_url", "datenschutz_markdown")


def test_get_settings_returns_legal_fields_empty(client):
    body = client.get("/api/v1/settings/").json()
    for field in LEGAL_FIELDS:
        assert field in body
        assert body[field] is None


def test_patch_legal_fields_sets_and_is_public(client, create_user):
    create_user("admin4", "adminpass", UserRole.admin)

    resp = client.patch(
        "/api/v1/settings/",
        json={
            "impressum_url": "https://example.org/impressum",
            "datenschutz_markdown": "# Datenschutz\n\nText.",
        },
        headers=basic_auth_header("admin4", "adminpass"),
    )
    assert resp.status_code == 200

    # Readable without auth; map_group_mode untouched by the partial update.
    body = client.get("/api/v1/settings/").json()
    assert body["impressum_url"] == "https://example.org/impressum"
    assert body["impressum_markdown"] is None
    assert body["datenschutz_url"] is None
    assert body["datenschutz_markdown"] == "# Datenschutz\n\nText."
    assert body["map_group_mode"] == "preconfigured"


def test_patch_legal_fields_clears_with_empty_string_and_null(client, create_user):
    create_user("admin5", "adminpass", UserRole.admin)
    headers = basic_auth_header("admin5", "adminpass")
    client.patch(
        "/api/v1/settings/",
        json={"impressum_url": "https://example.org/i", "impressum_markdown": "Text"},
        headers=headers,
    )

    resp = client.patch(
        "/api/v1/settings/",
        json={"impressum_url": "", "impressum_markdown": None},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["impressum_url"] is None
    assert body["impressum_markdown"] is None


def test_patch_legal_url_rejects_non_http_scheme(client, create_user):
    create_user("admin6", "adminpass", UserRole.admin)
    headers = basic_auth_header("admin6", "adminpass")
    for bad in ("javascript:alert(1)", "ftp://example.org", "example.org/impressum"):
        resp = client.patch("/api/v1/settings/", json={"datenschutz_url": bad}, headers=headers)
        assert resp.status_code == 422, bad


def test_patch_legal_fields_requires_settings_manage(client, create_user):
    create_user("editor2", "pass123", UserRole.editor)
    resp = client.patch(
        "/api/v1/settings/",
        json={"impressum_markdown": "Text"},
        headers=basic_auth_header("editor2", "pass123"),
    )
    assert resp.status_code == 403
