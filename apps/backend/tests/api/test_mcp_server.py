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
from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.crud import api_keys as api_keys_crud
from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.projects.progress_observation import ProgressObservation
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
        "list_project_groups",
        "list_projects",
        "get_project",
        "get_project_progress",
        "list_project_finves",
        "list_finves",
        "get_finve",
        "get_project_texts",
        "list_text_types",
        "create_project",
        "compute_project_length",
        "update_project",
        "set_project_groups",
        "add_progress_observation",
        "delete_progress_observation",
        "set_phase_override",
        "upsert_project_text",
        "merge_projects",
        "list_todos",
        "create_todo",
        "update_todo",
        "search_operational_points",
        "get_project_geometry",
        "route_project_geometry",
        "edit_project_geometry",
        "list_data_gaps",
        "check_geometry",
        "list_fulda_categories",
        "list_fulda_documents",
        "create_fulda_document",
        "update_fulda_document",
        "add_fulda_entries",
        "list_fulda_entries",
        "assign_fulda_entry",
        "update_fulda_entry",
        "delete_fulda_entry",
        "confirm_fulda_document",
        "list_vib_reports",
        "create_vib_report",
        "update_vib_report",
        "list_vib_entries",
        "get_vib_entry",
        "add_vib_entries",
        "update_vib_entry",
        "set_vib_pfa_entries",
        "assign_vib_entry",
        "assign_vib_pfa",
        "delete_vib_entry",
        "confirm_vib_report",
        "list_gvfg_programs",
        "list_gvfg_entries",
        "get_gvfg_entry",
        "list_project_gvfg",
        "assign_gvfg_entry",
        "list_skills",
        "get_skill",
    }
    by_name = {tool["name"]: tool for tool in tools}
    assert by_name["list_projects"]["annotations"]["readOnlyHint"] is True
    assert by_name["update_project"]["annotations"]["readOnlyHint"] is False
    assert by_name["delete_progress_observation"]["annotations"]["destructiveHint"] is True
    assert by_name["merge_projects"]["annotations"]["destructiveHint"] is True
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


def test_list_projects_by_group_name_and_several_groups(mcp_client, admin_token, db_session):
    alpha, beta = _seed_projects(db_session)
    dt = ProjectGroup(name="Deutschlandtakt", short_name="DT", color="#000000")
    alpha.project_groups.append(dt)
    beta.project_groups = [dt]
    db_session.add(dt)
    db_session.commit()

    by_name = _payload(
        _call(mcp_client, admin_token, "list_projects", {"project_group": "bedarfsplan"})
    )
    assert [p["id"] for p in by_name["projects"]] == [alpha.id]

    by_id = _payload(_call(mcp_client, admin_token, "list_projects", {"project_group": str(dt.id)}))
    assert [p["id"] for p in by_id["projects"]] == [alpha.id, beta.id]

    both = _payload(
        _call(mcp_client, admin_token, "list_projects", {"project_group": ["bp", "DT"]})
    )
    assert [p["id"] for p in both["projects"]] == [alpha.id]


def test_list_project_groups(mcp_client, admin_token, db_session):
    _seed_projects(db_session)
    db_session.add(ProjectGroup(name="Leer", short_name="L", color="#000000"))
    db_session.commit()

    groups = _payload(_call(mcp_client, admin_token, "list_project_groups"))["groups"]
    by_short = {g["short_name"]: g for g in groups}
    assert by_short["BP"]["name"] == "Bedarfsplan"
    assert by_short["BP"]["project_count"] == 1  # draft not counted
    assert by_short["L"]["project_count"] == 0

    found = _payload(_call(mcp_client, admin_token, "list_project_groups", {"search": "bedarf"}))
    assert [g["short_name"] for g in found["groups"]] == ["BP"]


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



# The SQLite test schema has no observation tables, so the progress view and the
# observation delete are stubbed (same convention as test_project_progress.py).


def _stub_view(db, project_id, today=None):
    progress = db.query(ProjectProgress).filter_by(project_id=project_id).first()
    override = progress.manual_phase_override if progress else None
    return {
        "project_id": project_id,
        "effective_phase": override or "NICHT_GESTARTET",
        "computed_phase": "NICHT_GESTARTET",
        "computed_confidence": 0.12,
        "is_overridden": override is not None,
        "manual_override_note": progress.manual_override_note if progress else None,
        "computed_at": None,
        "has_planfeststellung": False,
        "parl_befassung_relevant": False,
        "parl_befassung_relevant_override": None,
        "lifecycle_status": "AKTIV",
        "pf_state": "OFFEN",
        "parl_state": "OFFEN",
        "observations": [],
        "contributions": [],
        "pf_documents": [],
        "parl_documents": [],
        "is_superior": False,
        "span_min_phase": None,
        "span_max_phase": None,
        "children": [],
    }


def test_set_and_clear_phase_override(mcp_client, admin_token, db_session, monkeypatch):
    monkeypatch.setattr(progress_crud, "get_progress_view", _stub_view)
    alpha, _ = _seed_projects(db_session)

    missing_note = _call(
        mcp_client, admin_token, "set_phase_override", {"project_id": alpha.id, "phase": "IN_BETRIEB"}
    )
    assert missing_note["isError"] is True
    assert "note" in missing_note["content"][0]["text"]

    view = _payload(
        _call(
            mcp_client,
            admin_token,
            "set_phase_override",
            {"project_id": alpha.id, "phase": "IN_BETRIEB", "note": "Medien, 15.12.2024"},
        )
    )
    assert view["effective_phase"] == "IN_BETRIEB"
    assert view["is_overridden"] is True
    progress = db_session.query(ProjectProgress).filter_by(project_id=alpha.id).one()
    assert progress.manual_phase_override == "IN_BETRIEB"
    assert progress.manual_override_note == "Medien, 15.12.2024"
    set_log = db_session.query(ChangeLog).filter(ChangeLog.project_id == alpha.id).one()
    assert set_log.username_snapshot == "admin"
    assert {e.field_name: e.new_value for e in set_log.entries} == {
        "progress.manual_phase_override": '"IN_BETRIEB"',
        "progress.manual_override_note": '"Medien, 15.12.2024"',
    }

    cleared = _payload(
        _call(mcp_client, admin_token, "set_phase_override", {"project_id": alpha.id})
    )
    assert cleared["is_overridden"] is False
    db_session.refresh(progress)
    assert progress.manual_phase_override is None
    assert progress.manual_override_note is None
    logs = (
        db_session.query(ChangeLog)
        .filter(ChangeLog.project_id == alpha.id)
        .order_by(ChangeLog.id)
        .all()
    )
    assert len(logs) == 2
    assert {e.field_name: e.new_value for e in logs[1].entries} == {
        "progress.manual_phase_override": None,
        "progress.manual_override_note": None,
    }


def test_phase_override_needs_capability(mcp_client, db_session):
    alpha, _ = _seed_projects(db_session)
    user = _role_user(db_session, "reader", ["mcp.access"])
    token = _key_for(db_session, user)
    result = _call(
        mcp_client,
        token,
        "set_phase_override",
        {"project_id": alpha.id, "phase": "BAU", "note": "x"},
    )
    assert result["isError"] is True
    assert "progress.edit" in result["content"][0]["text"]
    assert db_session.query(ProjectProgress).filter_by(project_id=alpha.id).count() == 0


def test_add_and_delete_observation_write_changelog(
    mcp_client, admin_token, db_session, monkeypatch
):
    monkeypatch.setattr(progress_crud, "get_progress_view", _stub_view)
    alpha, beta = _seed_projects(db_session)

    _payload(
        _call(
            mcp_client,
            admin_token,
            "add_progress_observation",
            {
                "project_id": alpha.id,
                "track": "MAIN",
                "asserted_state": "IN_BETRIEB",
                "observed_date": "2024-12-15",
                "source_type": "MEDIEN",
                "note": "Wiederinbetriebnahme",
            },
        )
    )
    observation = db_session.query(ProgressObservation).filter_by(project_id=alpha.id).one()
    created = db_session.query(ChangeLog).filter_by(project_id=alpha.id, action="CREATE").one()
    assert created.username_snapshot == "admin"
    [entry] = created.entries
    assert entry.field_name == "progress.observation"
    assert entry.old_value is None
    assert entry.new_value == (
        f'"#{observation.id} Hauptpfad: IN_BETRIEB · 15.12.2024 · MEDIEN · Wiederinbetriebnahme"'
    )

    wrong_project = _call(
        mcp_client,
        admin_token,
        "delete_progress_observation",
        {"project_id": beta.id, "observation_id": observation.id},
    )
    assert wrong_project["isError"] is True

    _payload(
        _call(
            mcp_client,
            admin_token,
            "delete_progress_observation",
            {"project_id": alpha.id, "observation_id": observation.id},
        )
    )
    assert db_session.query(ProgressObservation).filter_by(project_id=alpha.id).count() == 0
    deleted = db_session.query(ChangeLog).filter_by(project_id=alpha.id, action="DELETE").one()
    [entry] = deleted.entries
    assert entry.field_name == "progress.observation"
    assert entry.new_value is None
    assert f"#{observation.id} Hauptpfad: IN_BETRIEB" in entry.old_value


def test_derived_observation_cannot_be_deleted(mcp_client, admin_token, db_session, monkeypatch):
    monkeypatch.setattr(progress_crud, "get_progress_view", _stub_view)
    alpha, _ = _seed_projects(db_session)
    derived = ProgressObservation(
        project_id=alpha.id, source_type="VIB", track="MAIN", asserted_state="BAU", is_derived=True
    )
    db_session.add(derived)
    db_session.commit()
    result = _call(
        mcp_client,
        admin_token,
        "delete_progress_observation",
        {"project_id": alpha.id, "observation_id": derived.id},
    )
    assert result["isError"] is True
    assert "Abgeleitete" in result["content"][0]["text"]
    assert db_session.query(ProgressObservation).filter_by(id=derived.id).count() == 1
    assert db_session.query(ChangeLog).filter_by(project_id=alpha.id).count() == 0


def test_delete_observation_needs_capability(mcp_client, db_session, monkeypatch):
    called = []
    monkeypatch.setattr(progress_crud, "delete_observation", lambda *a: called.append(a))
    alpha, _ = _seed_projects(db_session)
    user = _role_user(db_session, "reader", ["mcp.access"])
    token = _key_for(db_session, user)
    result = _call(
        mcp_client,
        token,
        "delete_progress_observation",
        {"project_id": alpha.id, "observation_id": 1},
    )
    assert result["isError"] is True
    assert "progress.edit" in result["content"][0]["text"]
    assert called == []


def test_set_project_groups_logs_and_reverts(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)  # alpha is in BP
    dt = ProjectGroup(name="Deutschlandtakt", short_name="DT", color="#000000")
    db_session.add(dt)
    db_session.commit()
    bp_id = alpha.project_groups[0].id

    result = _payload(
        _call(
            mcp_client,
            admin_token,
            "set_project_groups",
            {"project_id": alpha.id, "add": ["deutschlandtakt"], "remove": ["BP"]},
        )
    )
    assert [g["short_name"] for g in result["project_groups"]] == ["DT"]
    db_session.refresh(alpha)
    assert [g.id for g in alpha.project_groups] == [dt.id]

    changelog = db_session.query(ChangeLog).filter(ChangeLog.project_id == alpha.id).one()
    assert changelog.username_snapshot == "admin"
    [entry] = changelog.entries
    assert entry.field_name == "project_group_ids"
    assert json.loads(entry.old_value) == [bp_id]
    assert json.loads(entry.new_value) == [dt.id]

    # The entry is revertible like any project field.
    reverted = mcp_client.post(
        f"/api/v1/projects/{alpha.id}/changelog/revert",
        json={"changelog_entry_id": entry.id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reverted.status_code == 200, reverted.text
    db_session.refresh(alpha)
    assert [g.id for g in alpha.project_groups] == [bp_id]
    assert db_session.query(ChangeLog).filter_by(project_id=alpha.id, action="REVERT").count() == 1


def test_set_project_groups_errors(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)
    unknown = _call(
        mcp_client, admin_token, "set_project_groups", {"project_id": alpha.id, "add": ["XYZ"]}
    )
    assert unknown["isError"] is True
    assert "XYZ" in unknown["content"][0]["text"]

    via_update = _call(
        mcp_client,
        admin_token,
        "update_project",
        {"project_id": alpha.id, "changes": {"project_group_ids": []}},
    )
    assert via_update["isError"] is True
    assert "set_project_groups" in via_update["content"][0]["text"]

    # Already a member: nothing changes, nothing is logged.
    same = _payload(
        _call(mcp_client, admin_token, "set_project_groups", {"project_id": alpha.id, "add": ["BP"]})
    )
    assert [g["short_name"] for g in same["project_groups"]] == ["BP"]
    assert db_session.query(ChangeLog).filter_by(project_id=alpha.id).count() == 0


def test_set_project_groups_needs_capability(mcp_client, create_user, db_session):
    admin = create_user("admin", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["mcp.access"])
    alpha, _ = _seed_projects(db_session)
    result = _call(
        mcp_client, token, "set_project_groups", {"project_id": alpha.id, "remove": ["BP"]}
    )
    assert result["isError"] is True
    assert "project.edit" in result["content"][0]["text"]


LINE_1_DEGREE = json.dumps({"type": "LineString", "coordinates": [[0, 0], [1, 0]]})


def test_create_subproject_writes_changelog(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)
    created = _payload(
        _call(
            mcp_client,
            admin_token,
            "create_project",
            {
                "name": "ABS Alpha – Etappe 1",
                "superior_project_id": alpha.id,
                "project_groups": ["bp"],
                "fields": {"length": 12.5},
            },
        )
    )
    assert created["superior_project_id"] == alpha.id
    assert created["is_draft"] is False
    assert created["length"] == 12.5
    assert "geojson_representation" not in created

    project = db_session.query(Project).filter_by(id=created["id"]).one()
    assert [g.short_name for g in project.project_groups] == ["BP"]
    listed = _payload(
        _call(mcp_client, admin_token, "list_projects", {"superior_project_id": alpha.id})
    )
    assert [p["id"] for p in listed["projects"]] == [project.id]

    changelog = db_session.query(ChangeLog).filter_by(project_id=project.id).one()
    assert changelog.action == "CREATE"
    assert changelog.username_snapshot == "admin"
    entries = {e.field_name: (e.old_value, e.new_value) for e in changelog.entries}
    assert entries["name"] == (None, '"ABS Alpha \\u2013 Etappe 1"')
    assert entries["superior_project_id"] == (None, str(alpha.id))
    assert entries["length"] == (None, "12.5")
    assert entries["project_group_ids"] == (None, json.dumps([project.project_groups[0].id]))
    assert "is_draft" not in entries


def test_create_project_rejections(mcp_client, admin_token, db_session):
    _seed_projects(db_session)
    for arguments, needle in (
        ({"name": "X", "superior_project_id": 999999}, ""),
        ({"name": "X", "fields": {"geojson_representation": "{}"}}, "geojson_representation"),
        ({"name": "X", "fields": {"foo": 1}}, "foo"),
        ({"name": "X", "project_groups": ["XYZ"]}, "XYZ"),
    ):
        result = _call(mcp_client, admin_token, "create_project", arguments)
        assert result["isError"] is True, arguments
        assert needle in result["content"][0]["text"]
    assert db_session.query(Project).filter_by(name="X").count() == 0


def test_create_project_needs_capability(mcp_client, create_user, db_session):
    admin = create_user("admin", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["mcp.access"])
    result = _call(mcp_client, token, "create_project", {"name": "Nope"})
    assert result["isError"] is True
    assert "project.create" in result["content"][0]["text"]


def test_compute_project_length(mcp_client, admin_token, db_session):
    alpha, beta = _seed_projects(db_session)
    alpha.geojson_representation = LINE_1_DEGREE
    alpha.length = 70.0
    db_session.commit()

    preview = _payload(
        _call(mcp_client, admin_token, "compute_project_length", {"project_id": alpha.id})
    )
    assert preview["has_geometry"] is True
    assert 110 < preview["computed_length_km"] < 112
    assert preview["stored_length_km"] == 70.0
    assert preview["applied"] is False
    assert db_session.query(ChangeLog).filter_by(project_id=alpha.id).count() == 0

    applied = _payload(
        _call(
            mcp_client, admin_token, "compute_project_length", {"project_id": alpha.id, "apply": True}
        )
    )
    assert applied["applied"] is True
    assert applied["stored_length_km"] == preview["computed_length_km"]
    [entry] = db_session.query(ChangeLog).filter_by(project_id=alpha.id).one().entries
    assert entry.field_name == "length"
    assert entry.old_value == "70.0"

    no_geometry = _call(
        mcp_client, admin_token, "compute_project_length", {"project_id": beta.id, "apply": True}
    )
    assert no_geometry["isError"] is True


def test_compute_length_apply_needs_capability(mcp_client, create_user, db_session):
    admin = create_user("admin", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["mcp.access"])
    alpha, _ = _seed_projects(db_session)
    alpha.geojson_representation = LINE_1_DEGREE
    db_session.commit()
    assert _call(mcp_client, token, "compute_project_length", {"project_id": alpha.id})[
        "isError"
    ] is False
    result = _call(
        mcp_client, token, "compute_project_length", {"project_id": alpha.id, "apply": True}
    )
    assert result["isError"] is True
    assert "project.edit" in result["content"][0]["text"]
