"""Tests for the /api/v1/todos/ endpoints (Aufgaben).

Tasks are exercised standalone (``project_id=None``): the ``project`` table is
intentionally absent from the test schema, and the FK is unenforced in SQLite.
"""
from __future__ import annotations

from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def _editor(create_user, name="editor"):
    create_user(name, "pass123", UserRole.editor)
    return basic_auth_header(name, "pass123")


def _viewer(create_user, name="viewer"):
    create_user(name, "pass123", UserRole.viewer)
    return basic_auth_header(name, "pass123")


# --- Visibility / auth -------------------------------------------------------


def test_list_requires_auth(client):
    resp = client.get("/api/v1/todos/")
    assert resp.status_code == 401


def test_viewer_can_list_but_not_create(client, create_user):
    headers = _viewer(create_user)
    assert client.get("/api/v1/todos/", headers=headers).status_code == 200
    resp = client.post("/api/v1/todos/", json={"title": "X"}, headers=headers)
    assert resp.status_code == 403


# --- Create ------------------------------------------------------------------


def test_create_minimal_quick_add(client, create_user):
    headers = _editor(create_user)
    resp = client.post("/api/v1/todos/", json={"title": "PFA 3 überarbeiten"}, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "PFA 3 überarbeiten"
    assert body["status"] == "OPEN"
    assert body["priority"] == "MEDIUM"
    assert body["project_id"] is None
    assert body["assignees"] == []
    assert body["created_by_username"] == "editor"
    assert body["completed_at"] is None


def test_create_with_assignees(client, create_user):
    headers = _editor(create_user, "boss")
    alice = create_user("alice", "pass123", UserRole.viewer)
    bob = create_user("bob", "pass123", UserRole.viewer)
    resp = client.post(
        "/api/v1/todos/",
        json={"title": "Review", "priority": "HIGH", "assignee_ids": [alice.id, bob.id]},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["priority"] == "HIGH"
    assert {a["username"] for a in body["assignees"]} == {"alice", "bob"}


def test_create_done_sets_completed_at(client, create_user):
    headers = _editor(create_user)
    resp = client.post(
        "/api/v1/todos/", json={"title": "Already done", "status": "DONE"}, headers=headers
    )
    assert resp.json()["completed_at"] is not None


# --- Update ------------------------------------------------------------------


def test_status_transition_toggles_completed_at(client, create_user):
    headers = _editor(create_user)
    todo_id = client.post("/api/v1/todos/", json={"title": "T"}, headers=headers).json()["id"]

    done = client.patch(f"/api/v1/todos/{todo_id}", json={"status": "DONE"}, headers=headers)
    assert done.json()["completed_at"] is not None

    reopen = client.patch(f"/api/v1/todos/{todo_id}", json={"status": "OPEN"}, headers=headers)
    assert reopen.json()["completed_at"] is None


def test_update_replaces_assignees_and_clears_due_date(client, create_user):
    headers = _editor(create_user, "lead")
    alice = create_user("alice2", "pass123", UserRole.viewer)
    todo_id = client.post(
        "/api/v1/todos/",
        json={"title": "T", "due_date": "2026-07-01", "assignee_ids": [alice.id]},
        headers=headers,
    ).json()["id"]

    resp = client.patch(
        f"/api/v1/todos/{todo_id}",
        json={"assignee_ids": [], "clear_due_date": True},
        headers=headers,
    )
    body = resp.json()
    assert body["assignees"] == []
    assert body["due_date"] is None


def test_update_requires_edit_permission(client, create_user):
    editor = _editor(create_user)
    todo_id = client.post("/api/v1/todos/", json={"title": "T"}, headers=editor).json()["id"]
    viewer = _viewer(create_user)
    resp = client.patch(f"/api/v1/todos/{todo_id}", json={"title": "Hax"}, headers=viewer)
    assert resp.status_code == 403


# --- Filters & delete --------------------------------------------------------


def test_list_filters_by_status_and_include_done(client, create_user):
    headers = _editor(create_user)
    client.post("/api/v1/todos/", json={"title": "open one"}, headers=headers)
    client.post("/api/v1/todos/", json={"title": "done one", "status": "DONE"}, headers=headers)

    only_done = client.get("/api/v1/todos/?status=DONE", headers=headers).json()
    assert [t["title"] for t in only_done] == ["done one"]

    no_done = client.get("/api/v1/todos/?include_done=false", headers=headers).json()
    assert all(t["status"] != "DONE" for t in no_done)
    assert "open one" in [t["title"] for t in no_done]


def test_delete_requires_permission_and_removes(client, create_user):
    headers = _editor(create_user)
    todo_id = client.post("/api/v1/todos/", json={"title": "T"}, headers=headers).json()["id"]

    viewer = _viewer(create_user)
    assert client.delete(f"/api/v1/todos/{todo_id}", headers=viewer).status_code == 403

    assert client.delete(f"/api/v1/todos/{todo_id}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/todos/{todo_id}", headers=headers).status_code == 404


def test_user_options_available_to_any_logged_in_user(client, create_user):
    headers = _viewer(create_user)
    resp = client.get("/api/v1/users/options", headers=headers)
    assert resp.status_code == 200
    assert any(u["username"] == "viewer" for u in resp.json())
