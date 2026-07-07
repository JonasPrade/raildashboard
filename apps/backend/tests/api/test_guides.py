"""Tests for the /api/v1/guides override endpoints."""

from __future__ import annotations

from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


# --- auth --------------------------------------------------------------------


def test_list_overrides_is_public(client):
    resp = client.get("/api/v1/guides/fulda/overrides")
    assert resp.status_code == 200
    assert resp.json() == []


def test_put_requires_auth(client):
    resp = client.put(
        "/api/v1/guides/fulda/overrides/intro",
        json={"body_markdown": "Neu"},
    )
    assert resp.status_code == 401


def test_put_forbidden_without_permission(client, create_user):
    # editor lacks guides.edit by default (grantable via the roles admin UI)
    create_user("editor-g", "pass123", UserRole.editor)
    resp = client.put(
        "/api/v1/guides/fulda/overrides/intro",
        json={"body_markdown": "Neu"},
        headers=basic_auth_header("editor-g", "pass123"),
    )
    assert resp.status_code == 403


def test_delete_forbidden_without_permission(client, create_user):
    create_user("viewer-g", "pass123", UserRole.viewer)
    resp = client.delete(
        "/api/v1/guides/fulda/overrides/intro",
        headers=basic_auth_header("viewer-g", "pass123"),
    )
    assert resp.status_code == 403


# --- upsert / list / reset ---------------------------------------------------


def test_admin_can_upsert_list_and_reset(client, create_user):
    create_user("admin-g", "pass123", UserRole.admin)
    auth = basic_auth_header("admin-g", "pass123")

    # create
    resp = client.put(
        "/api/v1/guides/fulda/overrides/intro",
        json={"body_markdown": "Angepasster Einleitungstext."},
        headers=auth,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["guide_slug"] == "fulda"
    assert body["section_key"] == "intro"
    assert body["body_markdown"] == "Angepasster Einleitungstext."
    assert body["username_snapshot"] == "admin-g"

    # replace (upsert on the same key must not create a second row)
    resp = client.put(
        "/api/v1/guides/fulda/overrides/intro",
        json={"body_markdown": "Version 2"},
        headers=auth,
    )
    assert resp.status_code == 200
    assert resp.json()["body_markdown"] == "Version 2"

    # list is scoped by slug
    assert client.get("/api/v1/guides/fulda/overrides").json() == [
        {
            **{k: resp.json()[k] for k in ("guide_slug", "section_key", "body_markdown")},
            "updated_at": resp.json()["updated_at"],
            "username_snapshot": "admin-g",
        }
    ]
    assert client.get("/api/v1/guides/bauportal/overrides").json() == []

    # reset → fall back to default
    resp = client.delete("/api/v1/guides/fulda/overrides/intro", headers=auth)
    assert resp.status_code == 204
    assert client.get("/api/v1/guides/fulda/overrides").json() == []

    # reset is idempotent
    resp = client.delete("/api/v1/guides/fulda/overrides/intro", headers=auth)
    assert resp.status_code == 204


def test_empty_body_rejected(client, create_user):
    create_user("admin-g2", "pass123", UserRole.admin)
    resp = client.put(
        "/api/v1/guides/fulda/overrides/intro",
        json={"body_markdown": ""},
        headers=basic_auth_header("admin-g2", "pass123"),
    )
    assert resp.status_code == 422
