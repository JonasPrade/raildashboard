"""Tests for the project texts endpoints."""
from __future__ import annotations

import dashboard_backend.api.v1.endpoints.project_texts as texts_route
from dashboard_backend.schemas.projects.project_text_schema import (
    ProjectTextSchema,
    ProjectTextTypeSchema,
)
from dashboard_backend.schemas.projects import ProjectSchema
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

MOCK_TEXT_TYPE = ProjectTextTypeSchema(id=1, name="Pressemitteilung")

MOCK_TEXT = ProjectTextSchema(
    id=1,
    header="Test Header",
    text="Test content",
    type=1,
    created_at=0,
    updated_at=0,
    text_type=MOCK_TEXT_TYPE,
    attachments=[],
)


def _make_project(pid: int = 1) -> ProjectSchema:
    return ProjectSchema(
        id=pid,
        name="Test Project",
        length=None,
        number_junction_station=None,
        number_overtaking_station=None,
        new_vmax=None,
        etcs_level=None,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/projects/{id}/texts
# ---------------------------------------------------------------------------


def test_list_project_texts_returns_list(client, monkeypatch):
    monkeypatch.setattr(texts_route, "get_project_by_id", lambda db, pid: _make_project(pid))
    monkeypatch.setattr(texts_route, "get_texts_for_project", lambda db, pid: [MOCK_TEXT])

    resp = client.get("/api/v1/projects/1/texts")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["id"] == 1
    assert body[0]["header"] == "Test Header"


def test_list_project_texts_project_not_found(client, monkeypatch):
    monkeypatch.setattr(texts_route, "get_project_by_id", lambda db, pid: None)

    resp = client.get("/api/v1/projects/999/texts")
    assert resp.status_code == 404


def test_list_project_texts_empty(client, monkeypatch):
    monkeypatch.setattr(texts_route, "get_project_by_id", lambda db, pid: _make_project(pid))
    monkeypatch.setattr(texts_route, "get_texts_for_project", lambda db, pid: [])

    resp = client.get("/api/v1/projects/1/texts")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/v1/text_types
# ---------------------------------------------------------------------------


def test_list_text_types(client, monkeypatch):
    monkeypatch.setattr(texts_route, "get_text_types", lambda db: [MOCK_TEXT_TYPE])

    resp = client.get("/api/v1/text_types")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Pressemitteilung"


# ---------------------------------------------------------------------------
# POST /api/v1/projects/{id}/texts
# ---------------------------------------------------------------------------


def test_create_text_requires_editor(client, create_user, monkeypatch):
    create_user("viewer", "pass123", UserRole.viewer)
    monkeypatch.setattr(texts_route, "get_project_by_id", lambda db, pid: _make_project(pid))

    resp = client.post(
        "/api/v1/projects/1/texts",
        json={"header": "H", "type": 1},
        headers=basic_auth_header("viewer", "pass123"),
    )
    assert resp.status_code == 403


def test_create_text_requires_auth(client, monkeypatch):
    monkeypatch.setattr(texts_route, "get_project_by_id", lambda db, pid: _make_project(pid))

    resp = client.post("/api/v1/projects/1/texts", json={"header": "H", "type": 1})
    assert resp.status_code == 401


def test_create_text_success(client, create_user, monkeypatch):
    create_user("editor", "pass123", UserRole.editor)
    monkeypatch.setattr(texts_route, "get_project_by_id", lambda db, pid: _make_project(pid))
    monkeypatch.setattr(texts_route, "create_text_for_project", lambda db, pid, data: MOCK_TEXT)
    monkeypatch.setattr(texts_route, "create_text_changelog_for_create", lambda *a, **kw: None)

    resp = client.post(
        "/api/v1/projects/1/texts",
        json={"header": "Test Header", "type": 1},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 201
    assert resp.json()["header"] == "Test Header"


def test_create_text_project_not_found(client, create_user, monkeypatch):
    create_user("editor", "pass123", UserRole.editor)
    monkeypatch.setattr(texts_route, "get_project_by_id", lambda db, pid: None)

    resp = client.post(
        "/api/v1/projects/999/texts",
        json={"header": "H", "type": 1},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/projects/texts/{text_id}
# ---------------------------------------------------------------------------


def test_delete_text_requires_editor(client, create_user, monkeypatch):
    create_user("viewer", "pass123", UserRole.viewer)

    resp = client.delete(
        "/api/v1/projects/texts/1",
        headers=basic_auth_header("viewer", "pass123"),
    )
    assert resp.status_code == 403


def test_delete_text_not_found(client, create_user, monkeypatch):
    create_user("editor", "pass123", UserRole.editor)

    # Patch DB query via the endpoint's db.query call by patching delete_project_text guard
    # Simpler: let the real DB return None for the query (no text inserted)
    resp = client.delete(
        "/api/v1/projects/texts/999",
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 404
