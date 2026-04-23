"""Tests for the /api/v1/projects/ endpoints."""
from __future__ import annotations

import dashboard_backend.api.v1.endpoints.projects as projects_route
from dashboard_backend.schemas.projects import ProjectSchema
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


# ---------------------------------------------------------------------------
# Minimal stub that satisfies ProjectSchema's required fields
# ---------------------------------------------------------------------------

def _make_project(project_id: int = 1, name: str = "Test Project") -> ProjectSchema:
    return ProjectSchema(
        id=project_id,
        name=name,
        length=None,
        number_junction_station=None,
        number_overtaking_station=None,
        new_vmax=None,
        etcs_level=None,
    )


MOCK_PROJECTS = [_make_project(1, "Alpha"), _make_project(2, "Beta")]


# ---------------------------------------------------------------------------
# GET /api/v1/projects/
# ---------------------------------------------------------------------------


def test_list_projects_returns_all(client, monkeypatch):
    monkeypatch.setattr(projects_route, "get_projects", lambda db: MOCK_PROJECTS)

    resp = client.get("/api/v1/projects/")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert {p["id"] for p in body} == {1, 2}


def test_list_projects_empty(client, monkeypatch):
    monkeypatch.setattr(projects_route, "get_projects", lambda db: [])

    resp = client.get("/api/v1/projects/")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/v1/projects/{project_id}
# ---------------------------------------------------------------------------


def test_get_project_found(client, monkeypatch):
    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: _make_project(pid))

    resp = client.get("/api/v1/projects/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == 1


def test_get_project_not_found(client, monkeypatch):
    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: None)

    resp = client.get("/api/v1/projects/999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/projects/
# ---------------------------------------------------------------------------


def test_create_project_success(client, create_user, monkeypatch):
    create_user("editor", "pass123", UserRole.editor)
    created = _make_project(42, "Wizard Project")
    captured = {}

    def fake_create(db, data):
        captured.update(data)
        return created

    monkeypatch.setattr(projects_route, "create_project", fake_create)

    resp = client.post(
        "/api/v1/projects/",
        json={"name": "Wizard Project", "project_number": "1-042"},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 42
    assert body["name"] == "Wizard Project"
    assert captured["name"] == "Wizard Project"
    assert captured["project_number"] == "1-042"


def test_create_project_requires_editor(client, create_user):
    create_user("viewer", "pass123", UserRole.viewer)
    resp = client.post(
        "/api/v1/projects/",
        json={"name": "X"},
        headers=basic_auth_header("viewer", "pass123"),
    )
    assert resp.status_code == 403


def test_create_project_rejects_empty_name(client, create_user):
    create_user("editor", "pass123", UserRole.editor)
    resp = client.post(
        "/api/v1/projects/",
        json={"name": ""},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/v1/projects/{project_id}
# ---------------------------------------------------------------------------


def test_patch_project_requires_auth(client, monkeypatch):
    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: _make_project(pid))

    resp = client.patch("/api/v1/projects/1", json={"name": "Updated"})
    assert resp.status_code == 401


def test_patch_project_requires_editor_role(client, create_user, monkeypatch):
    create_user("viewer", "pass123", UserRole.viewer)
    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: _make_project(pid))

    resp = client.patch(
        "/api/v1/projects/1",
        json={"name": "Updated"},
        headers=basic_auth_header("viewer", "pass123"),
    )
    assert resp.status_code == 403


def test_patch_project_success(client, create_user, monkeypatch):
    create_user("editor", "pass123", UserRole.editor)
    updated = _make_project(1, "Updated Name")

    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: _make_project(pid))
    monkeypatch.setattr(projects_route, "create_changelog_for_patch", lambda *a, **kw: None)
    monkeypatch.setattr(projects_route, "update_project", lambda db, pid, data: updated)

    resp = client.patch(
        "/api/v1/projects/1",
        json={"name": "Updated Name"},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


def test_patch_project_not_found(client, create_user, monkeypatch):
    create_user("editor", "pass123", UserRole.editor)
    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: None)

    resp = client.patch(
        "/api/v1/projects/999",
        json={"name": "X"},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/projects/{project_id}/changelog
# ---------------------------------------------------------------------------


def test_get_changelog_requires_auth(client, monkeypatch):
    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: _make_project(pid))

    resp = client.get("/api/v1/projects/1/changelog")
    assert resp.status_code == 401


def test_get_changelog_returns_list(client, create_user, monkeypatch):
    create_user("viewer", "pass123", UserRole.viewer)
    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: _make_project(pid))
    monkeypatch.setattr(projects_route, "get_project_changelog", lambda db, pid: [])

    resp = client.get(
        "/api/v1/projects/1/changelog",
        headers=basic_auth_header("viewer", "pass123"),
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_changelog_project_not_found(client, create_user, monkeypatch):
    create_user("viewer", "pass123", UserRole.viewer)
    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: None)

    resp = client.get(
        "/api/v1/projects/999/changelog",
        headers=basic_auth_header("viewer", "pass123"),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/projects/{project_id}/changelog/revert
# ---------------------------------------------------------------------------


def test_revert_requires_editor(client, create_user, monkeypatch):
    create_user("viewer", "pass123", UserRole.viewer)
    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: _make_project(pid))

    resp = client.post(
        "/api/v1/projects/1/changelog/revert",
        json={"changelog_entry_id": 1},
        headers=basic_auth_header("viewer", "pass123"),
    )
    assert resp.status_code == 403


def test_revert_entry_not_found(client, create_user, monkeypatch):
    create_user("editor", "pass123", UserRole.editor)
    monkeypatch.setattr(projects_route, "get_project_by_id", lambda db, pid: _make_project(pid))
    monkeypatch.setattr(projects_route, "get_changelog_entry", lambda db, eid, pid: None)

    resp = client.post(
        "/api/v1/projects/1/changelog/revert",
        json={"changelog_entry_id": 999},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 404
