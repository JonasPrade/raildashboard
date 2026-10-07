"""MCP endpoint (/mcp): bearer-key auth, tool catalog and permission gates.

Talks JSON-RPC to the Streamable HTTP transport the way a client does. The
lifespan must run (``with TestClient(app)``) because it starts the SDK's
session manager.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from dashboard_backend.core.security import hash_password
from dashboard_backend.crud import api_keys as api_keys_crud
from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.roles import Role, RolePermission
from dashboard_backend.models.todos.todo import Todo
from dashboard_backend.models.users import User
from dashboard_backend.schemas.users import UserRole
from main import app

PROTOCOL_VERSION = "2025-06-18"
HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
    "MCP-Protocol-Version": PROTOCOL_VERSION,
}


@pytest.fixture()
def mcp_client(db_session):
    with TestClient(app) as test_client:
        yield test_client


def _post(client, token, method, params=None, request_id=1):
    headers = dict(HEADERS)
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    body = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        body["params"] = params
    return client.post("/mcp", headers=headers, json=body)


def _call(client, token, name, arguments=None):
    response = _post(client, token, "tools/call", {"name": name, "arguments": arguments or {}})
    assert response.status_code == 200, response.text
    return response.json()["result"]


def _payload(result):
    assert result["isError"] is False, result
    return json.loads(result["content"][0]["text"])


def _key_for(db, user, scopes=None):
    _, token = api_keys_crud.create_api_key(db, user, "test", scopes)
    return token


def _role_user(db, username, permission_keys):
    role = Role(name=f"role-{username}", description=None, is_system=False)
    role.permissions = [RolePermission(permission_key=key) for key in permission_keys]
    db.add(role)
    db.flush()
    user = User(username=username, hashed_password=hash_password("password123"), role_id=role.id)
    db.add(user)
    db.commit()
    return user


@pytest.fixture()
def admin_token(create_user, db_session):
    admin = create_user("admin", "adminpass", UserRole.admin)
    return _key_for(db_session, admin)


# --- Auth --------------------------------------------------------------------


def test_missing_key_is_401(mcp_client):
    response = _post(mcp_client, None, "tools/list")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_key_is_401(mcp_client):
    assert _post(mcp_client, "rdb_abcdefghijkl_nope", "tools/list").status_code == 401


def test_basic_auth_is_not_accepted(mcp_client, create_user):
    create_user("admin", "adminpass", UserRole.admin)
    response = mcp_client.post(
        "/mcp",
        auth=("admin", "adminpass"),
        headers=HEADERS,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    )
    assert response.status_code == 401


def test_key_without_mcp_access_is_403(mcp_client, db_session):
    user = _role_user(db_session, "editorlike", ["project.edit"])
    token = _key_for(db_session, user)
    assert _post(mcp_client, token, "tools/list").status_code == 403


def test_admin_key_scoped_without_mcp_access_is_403(mcp_client, create_user, db_session):
    admin = create_user("admin", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["project.edit"])
    assert _post(mcp_client, token, "tools/list").status_code == 403


# --- Protocol ----------------------------------------------------------------


def test_initialize_and_list_tools(mcp_client, admin_token):
    init = _post(
        mcp_client,
        admin_token,
        "initialize",
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "1"},
        },
    )
    assert init.status_code == 200
    assert init.json()["result"]["serverInfo"]["name"] == "raildashboard"

    tools = _post(mcp_client, admin_token, "tools/list").json()["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert names == {
        "list_projects",
        "get_project",
        "get_project_progress",
        "list_project_finves",
        "get_project_texts",
        "list_text_types",
        "update_project",
        "add_progress_observation",
        "upsert_project_text",
        "list_todos",
        "create_todo",
        "update_todo",
    }
    by_name = {tool["name"]: tool for tool in tools}
    assert by_name["list_projects"]["annotations"]["readOnlyHint"] is True
    assert by_name["update_project"]["annotations"]["readOnlyHint"] is False
    # The SDK context parameter must not leak into the client-facing schema.
    assert "ctx" not in by_name["list_projects"]["inputSchema"]["properties"]


# --- Read tools --------------------------------------------------------------


def _seed_projects(db):
    group = ProjectGroup(name="Bedarfsplan", short_name="BP", color="#000000")
    alpha = Project(name="ABS Alpha", project_number="1-001", is_draft=False)
    beta = Project(name="NBS Beta", project_number="2-002", is_draft=False)
    draft = Project(name="Alpha Entwurf", is_draft=True)
    alpha.project_groups = [group]
    db.add_all([group, alpha, beta, draft])
    db.flush()
    db.add(ProjectProgress(project_id=beta.id, computed_phase="BAU"))
    db.commit()
    return alpha, beta


def test_list_projects_filters(mcp_client, admin_token, db_session):
    alpha, beta = _seed_projects(db_session)

    everything = _payload(_call(mcp_client, admin_token, "list_projects"))
    assert everything["total"] == 2  # draft excluded
    assert [p["name"] for p in everything["projects"]] == ["ABS Alpha", "NBS Beta"]
    assert "geojson_representation" not in everything["projects"][0]

    by_text = _payload(_call(mcp_client, admin_token, "list_projects", {"search": "alpha"}))
    assert [p["id"] for p in by_text["projects"]] == [alpha.id]

    by_group = _payload(_call(mcp_client, admin_token, "list_projects", {"project_group": "BP"}))
    assert [p["id"] for p in by_group["projects"]] == [alpha.id]
    assert by_group["projects"][0]["project_groups"] == ["BP"]

    by_phase = _payload(_call(mcp_client, admin_token, "list_projects", {"phase": "BAU"}))
    assert [p["id"] for p in by_phase["projects"]] == [beta.id]
    assert by_phase["projects"][0]["phase"] == "BAU"

    page = _payload(_call(mcp_client, admin_token, "list_projects", {"limit": 1, "offset": 1}))
    assert page["total"] == 2
    assert [p["id"] for p in page["projects"]] == [beta.id]


def test_get_project_without_geometry(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)
    data = _payload(_call(mcp_client, admin_token, "get_project", {"project_id": alpha.id}))
    assert data["name"] == "ABS Alpha"
    assert "geojson_representation" not in data
    assert "centroid" not in data
    assert data["subprojects"] == []


def test_unknown_project_is_tool_error(mcp_client, admin_token):
    result = _call(mcp_client, admin_token, "get_project", {"project_id": 999999})
    assert result["isError"] is True
    assert "nicht gefunden" in result["content"][0]["text"]


# --- Write tools -------------------------------------------------------------


def test_create_todo_end_to_end(mcp_client, admin_token, db_session):
    created = _payload(
        _call(mcp_client, admin_token, "create_todo", {"title": "Via MCP", "priority": "HIGH"})
    )
    assert created["title"] == "Via MCP"
    assert created["created_by_username"] == "admin"

    todo = db_session.query(Todo).filter(Todo.id == created["id"]).one()
    assert todo.priority == "HIGH"

    updated = _payload(
        _call(mcp_client, admin_token, "update_todo", {"todo_id": todo.id, "status": "DONE"})
    )
    assert updated["status"] == "DONE"
    listed = _payload(_call(mcp_client, admin_token, "list_todos", {"include_done": True}))
    assert [t["id"] for t in listed["todos"]] == [todo.id]


def test_write_tool_needs_capability(mcp_client, db_session):
    user = _role_user(db_session, "reader", ["mcp.access"])
    token = _key_for(db_session, user)
    result = _call(mcp_client, token, "create_todo", {"title": "Nope"})
    assert result["isError"] is True
    assert "todo.create" in result["content"][0]["text"]
    assert db_session.query(Todo).count() == 0


def test_read_only_key_cannot_write(mcp_client, create_user, db_session):
    admin = create_user("admin", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["mcp.access"])
    alpha, _ = _seed_projects(db_session)

    result = _call(
        mcp_client, token, "update_project", {"project_id": alpha.id, "changes": {"name": "X"}}
    )
    assert result["isError"] is True
    assert "project.edit" in result["content"][0]["text"]
    # Reading still works with the same key.
    assert _call(mcp_client, token, "get_project", {"project_id": alpha.id})["isError"] is False


def test_update_project_rejects_geometry(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)
    result = _call(
        mcp_client,
        admin_token,
        "update_project",
        {"project_id": alpha.id, "changes": {"geojson_representation": "{}"}},
    )
    assert result["isError"] is True


def test_update_project_writes_changelog(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)
    data = _payload(
        _call(
            mcp_client,
            admin_token,
            "update_project",
            {"project_id": alpha.id, "changes": {"description": "Neu", "nbs": True}},
        )
    )
    assert data["description"] == "Neu"
    assert data["nbs"] is True

    changelog = db_session.query(ChangeLog).filter(ChangeLog.project_id == alpha.id).one()
    assert changelog.username_snapshot == "admin"
    assert {e.field_name for e in changelog.entries} == {"description", "nbs"}


def test_update_project_rejects_unknown_field(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)
    result = _call(
        mcp_client, admin_token, "update_project", {"project_id": alpha.id, "changes": {"foo": 1}}
    )
    assert result["isError"] is True
    assert "foo" in result["content"][0]["text"]
