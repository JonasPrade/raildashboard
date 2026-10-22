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


# --- Tags --------------------------------------------------------------------


def test_create_with_tags_reuses_existing_case_insensitively(client, create_user):
    headers = _editor(create_user)
    first = client.post(
        "/api/v1/todos/", json={"title": "A", "tags": ["@LLM", " Recherche ", "@llm"]}, headers=headers
    ).json()
    assert [t["name"] for t in first["tags"]] == ["@LLM", "Recherche"]

    second = client.post("/api/v1/todos/", json={"title": "B", "tags": ["@llm"]}, headers=headers).json()
    assert [t["name"] for t in second["tags"]] == ["@LLM"]
    assert second["tags"][0]["id"] == first["tags"][0]["id"]

    tags = client.get("/api/v1/todos/tags", headers=headers).json()
    assert [(t["name"], t["todo_count"]) for t in tags] == [("@LLM", 2), ("Recherche", 1)]


def test_update_replaces_and_clears_tags(client, create_user):
    headers = _editor(create_user)
    todo_id = client.post(
        "/api/v1/todos/", json={"title": "T", "tags": ["a", "b"]}, headers=headers
    ).json()["id"]

    resp = client.patch(f"/api/v1/todos/{todo_id}", json={"tags": ["b", "c"]}, headers=headers)
    assert [t["name"] for t in resp.json()["tags"]] == ["b", "c"]

    # Omitting tags leaves them as they are.
    resp = client.patch(f"/api/v1/todos/{todo_id}", json={"title": "T2"}, headers=headers)
    assert [t["name"] for t in resp.json()["tags"]] == ["b", "c"]

    resp = client.patch(f"/api/v1/todos/{todo_id}", json={"tags": []}, headers=headers)
    assert resp.json()["tags"] == []


def test_tag_too_long_is_rejected(client, create_user):
    headers = _editor(create_user)
    resp = client.post("/api/v1/todos/", json={"title": "T", "tags": ["x" * 51]}, headers=headers)
    assert resp.status_code == 422


def test_list_filters_by_tag_and_text(client, create_user):
    headers = _editor(create_user)
    client.post("/api/v1/todos/", json={"title": "Infraplan lesen", "tags": ["@LLM"]}, headers=headers)
    client.post(
        "/api/v1/todos/",
        json={"title": "Anrufen", "description": "wegen Infraplan"},
        headers=headers,
    )
    client.post("/api/v1/todos/", json={"title": "Sonstiges"}, headers=headers)

    by_tag = client.get("/api/v1/todos/?tag=@llm", headers=headers).json()
    assert [t["title"] for t in by_tag] == ["Infraplan lesen"]

    by_text = client.get("/api/v1/todos/?q=infraplan", headers=headers).json()
    assert {t["title"] for t in by_text} == {"Infraplan lesen", "Anrufen"}

    both = client.get("/api/v1/todos/?q=infraplan&tag=@LLM", headers=headers).json()
    assert [t["title"] for t in both] == ["Infraplan lesen"]


def test_tags_require_auth(client):
    assert client.get("/api/v1/todos/tags").status_code == 401


# --- History -----------------------------------------------------------------


def test_history_records_create_and_tag_changes(client, create_user):
    headers = _editor(create_user)
    todo_id = client.post(
        "/api/v1/todos/", json={"title": "T", "tags": ["@LLM"]}, headers=headers
    ).json()["id"]
    client.patch(f"/api/v1/todos/{todo_id}", json={"tags": ["@LLM", "Doku"]}, headers=headers)
    # A no-op update writes no history row.
    client.patch(f"/api/v1/todos/{todo_id}", json={"title": "T"}, headers=headers)

    history = client.get(f"/api/v1/todos/{todo_id}/history", headers=headers).json()
    assert [h["action"] for h in history] == ["PATCH", "CREATE"]
    patch = history[0]
    assert patch["username_snapshot"] == "editor"
    assert patch["entries"] == [{"field_name": "tags", "old_value": "@LLM", "new_value": "@LLM, Doku"}]
    created = {e["field_name"]: e["new_value"] for e in history[1]["entries"]}
    assert created["title"] == "T"
    assert created["tags"] == "@LLM"


def test_history_unknown_task_is_404(client, create_user):
    headers = _editor(create_user)
    assert client.get("/api/v1/todos/999/history", headers=headers).status_code == 404


# --- Tag management ----------------------------------------------------------


def _tag_id(client, headers, name):
    return next(t["id"] for t in client.get("/api/v1/todos/tags", headers=headers).json() if t["name"] == name)


def test_rename_tag_is_logged_on_tasks(client, create_user):
    headers = _editor(create_user)
    todo_id = client.post(
        "/api/v1/todos/", json={"title": "T", "tags": ["Recherche"]}, headers=headers
    ).json()["id"]
    tag_id = _tag_id(client, headers, "Recherche")

    resp = client.patch(
        f"/api/v1/todos/tags/{tag_id}",
        json={"name": " Quellen ", "description": "Quellen suchen"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {"id": tag_id, "name": "Quellen", "description": "Quellen suchen", "todo_count": 1}

    todo = client.get(f"/api/v1/todos/{todo_id}", headers=headers).json()
    assert [t["name"] for t in todo["tags"]] == ["Quellen"]
    history = client.get(f"/api/v1/todos/{todo_id}/history", headers=headers).json()
    assert history[0]["entries"] == [
        {"field_name": "tags", "old_value": "Recherche", "new_value": "Quellen"}
    ]

    resp = client.patch(f"/api/v1/todos/tags/{tag_id}", json={"clear_description": True}, headers=headers)
    assert resp.json()["description"] is None


def test_rename_tag_to_existing_name_conflicts(client, create_user):
    headers = _editor(create_user)
    client.post("/api/v1/todos/", json={"title": "T", "tags": ["a", "b"]}, headers=headers)
    tag_id = _tag_id(client, headers, "a")
    resp = client.patch(f"/api/v1/todos/tags/{tag_id}", json={"name": "B"}, headers=headers)
    assert resp.status_code == 409
    # Changing only the case of its own name is fine.
    resp = client.patch(f"/api/v1/todos/tags/{tag_id}", json={"name": "A"}, headers=headers)
    assert resp.json()["name"] == "A"


def test_delete_tag_removes_it_from_tasks(client, create_user):
    headers = _editor(create_user)
    todo_id = client.post(
        "/api/v1/todos/", json={"title": "T", "tags": ["alt", "bleibt"]}, headers=headers
    ).json()["id"]
    tag_id = _tag_id(client, headers, "alt")

    viewer = _viewer(create_user)
    assert client.delete(f"/api/v1/todos/tags/{tag_id}", headers=viewer).status_code == 403

    assert client.delete(f"/api/v1/todos/tags/{tag_id}", headers=headers).status_code == 204
    assert [t["name"] for t in client.get("/api/v1/todos/tags", headers=headers).json()] == ["bleibt"]
    todo = client.get(f"/api/v1/todos/{todo_id}", headers=headers).json()
    assert [t["name"] for t in todo["tags"]] == ["bleibt"]
    history = client.get(f"/api/v1/todos/{todo_id}/history", headers=headers).json()
    assert history[0]["entries"] == [
        {"field_name": "tags", "old_value": "alt, bleibt", "new_value": "bleibt"}
    ]


def test_unknown_tag_is_404(client, create_user):
    headers = _editor(create_user)
    assert client.patch("/api/v1/todos/tags/99", json={"name": "x"}, headers=headers).status_code == 404
    assert client.delete("/api/v1/todos/tags/99", headers=headers).status_code == 404
