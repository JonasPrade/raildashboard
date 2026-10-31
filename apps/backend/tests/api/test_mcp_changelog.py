"""MCP change-history tools: project, text and task history, and revert."""

from __future__ import annotations

from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.projects.project_text_type import ProjectTextType
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    _role_user,
    _seed_projects,
    admin_token,
    mcp_client,
)


def _edit(client, token, project_id, changes):
    return _payload(
        _call(client, token, "update_project", {"project_id": project_id, "changes": changes})
    )


def test_changelog_lists_newest_first_and_filters(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)
    _edit(mcp_client, admin_token, alpha.id, {"description": "Erste Fassung"})
    _edit(mcp_client, admin_token, alpha.id, {"nbs": True})
    _edit(mcp_client, admin_token, alpha.id, {"description": "x" * 900})

    log = _payload(_call(mcp_client, admin_token, "get_project_changelog", {"project_id": alpha.id}))
    assert log["total"] == 3
    newest = log["events"][0]["changes"][0]
    assert newest["field"] == "description"
    assert newest["truncated"] is True and len(newest["new"]) == 500
    assert log["events"][0]["user"] == "admin"

    only_desc = _payload(
        _call(
            mcp_client,
            admin_token,
            "get_project_changelog",
            {"project_id": alpha.id, "field": "description", "limit": 1},
        )
    )
    assert only_desc["total"] == 2 and len(only_desc["events"]) == 1
    future = _payload(
        _call(
            mcp_client,
            admin_token,
            "get_project_changelog",
            {"project_id": alpha.id, "since": "2999-01-01"},
        )
    )
    assert future["total"] == 0


def test_revert_sets_old_value_and_logs_revert(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)
    _edit(mcp_client, admin_token, alpha.id, {"description": "Alt"})
    _edit(mcp_client, admin_token, alpha.id, {"description": "Falsch"})
    log = _payload(_call(mcp_client, admin_token, "get_project_changelog", {"project_id": alpha.id}))
    entry_id = log["events"][0]["changes"][0]["entry_id"]

    result = _payload(
        _call(
            mcp_client,
            admin_token,
            "revert_project_change",
            {"project_id": alpha.id, "changelog_entry_id": entry_id},
        )
    )
    assert result["project"]["description"] == "Alt"
    assert result["revert_event"]["action"] == "REVERT"
    actions = [c.action for c in db_session.query(ChangeLog).filter_by(project_id=alpha.id)]
    assert actions.count("REVERT") == 1


def test_revert_errors(mcp_client, admin_token, db_session):
    alpha, beta = _seed_projects(db_session)
    _edit(mcp_client, admin_token, beta.id, {"description": "Beta"})
    log = _payload(_call(mcp_client, admin_token, "get_project_changelog", {"project_id": beta.id}))
    foreign_entry = log["events"][0]["changes"][0]["entry_id"]
    wrong_project = _call(
        mcp_client,
        admin_token,
        "revert_project_change",
        {"project_id": alpha.id, "changelog_entry_id": foreign_entry},
    )
    assert wrong_project["isError"] is True
    assert "gehört nicht" in wrong_project["content"][0]["text"]

    reader = _key_for(db_session, _role_user(db_session, "leser", ["mcp.access"]))
    denied = _call(
        mcp_client,
        reader,
        "revert_project_change",
        {"project_id": beta.id, "changelog_entry_id": foreign_entry},
    )
    assert denied["isError"] is True and "project.edit" in denied["content"][0]["text"]
    # Reading needs no extra right.
    assert _payload(_call(mcp_client, reader, "get_project_changelog", {"project_id": beta.id}))["total"] == 1


def test_text_changelog_and_todo_history(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)
    text_type = ProjectTextType(name="Info")
    db_session.add(text_type)
    db_session.commit()
    created = _payload(
        _call(
            mcp_client,
            admin_token,
            "upsert_project_text",
            {"project_id": alpha.id, "header": "Stand", "text": "A", "text_type_id": text_type.id},
        )
    )
    _payload(
        _call(
            mcp_client,
            admin_token,
            "upsert_project_text",
            {"project_id": alpha.id, "text_id": created["id"], "text": "B"},
        )
    )
    texts = _payload(
        _call(mcp_client, admin_token, "get_project_text_changelog", {"project_id": alpha.id})
    )
    assert texts["total"] == 2
    assert {e["action"] for e in texts["events"]} == {"CREATE", "PATCH"}
    assert texts["events"][0]["text_header"] == "Stand"

    todo = _payload(_call(mcp_client, admin_token, "create_todo", {"title": "Prüfen"}))
    _payload(_call(mcp_client, admin_token, "update_todo", {"todo_id": todo["id"], "status": "DONE"}))
    plain = _payload(_call(mcp_client, admin_token, "get_todo", {"todo_id": todo["id"]}))
    assert "history" not in plain and plain["title"] == "Prüfen"
    with_history = _payload(
        _call(mcp_client, admin_token, "get_todo", {"todo_id": todo["id"], "history": True})
    )
    assert with_history["history"][0]["entries"][0]["field_name"] == "status"
    assert _call(mcp_client, admin_token, "get_todo", {"todo_id": 999})["isError"] is True
