"""MCP DB-Bauportal tools: list/get, assignment with re-materialisation, and the
entry reference on the derived observation in get_project_progress."""

from __future__ import annotations

from datetime import datetime

from dashboard_backend.models.projects.bauportal_status import BauportalStatus
from dashboard_backend.models.projects.project import Project
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    _role_user,
    admin_token,
    mcp_client,
)


def _seed(db):
    alpha = Project(name="ABS Oldenburg – Wilhelmshaven")
    beta = Project(name="Wilhelmshaven Ölweiche")
    db.add_all([alpha, beta])
    db.flush()
    build = BauportalStatus(
        bauportal_id=1, shorttitle="ABS Oldenburg-Wilhelmshaven", status_raw="Projekt in der Bauphase",
        projecttime_raw="in Baustufen", url="https://bau.example/1", raw_json='{"id": 1}',
        fetched_at=datetime(2026, 7, 15), suggested_project_id=alpha.id,
    )
    plan = BauportalStatus(
        bauportal_id=2, shorttitle="Ölweiche Nord", status_raw="Projekt in der Planungsphase",
        projecttime_raw="2025 – 2026", fetched_at=datetime(2026, 7, 15),
    )
    db.add_all([build, plan])
    db.commit()
    return alpha, beta, build, plan


def test_list_and_filters(mcp_client, admin_token, db_session):
    alpha, _, build, plan = _seed(db_session)
    res = _payload(_call(mcp_client, admin_token, "list_bauportal_entries", {}))
    assert res["total"] == 2
    assert "raw_json" not in res["entries"][0]
    assert _payload(_call(mcp_client, admin_token, "list_bauportal_entries", {"search": "weiche"}))["total"] == 1
    assert _payload(_call(mcp_client, admin_token, "list_bauportal_entries", {"only_without_project": True}))["total"] == 2
    _call(mcp_client, admin_token, "assign_bauportal_entry", {"entry_id": build.id, "project_id": alpha.id})
    by_project = _payload(_call(mcp_client, admin_token, "list_bauportal_entries", {"project_id": alpha.id}))
    assert [e["id"] for e in by_project["entries"]] == [build.id]
    assert by_project["entries"][0]["project_name"] == alpha.name
    open_ = _payload(_call(mcp_client, admin_token, "list_bauportal_entries", {"only_unconfirmed": True}))
    assert open_["total"] == 2


def test_get_entry(mcp_client, admin_token, db_session):
    _, _, build, _ = _seed(db_session)
    entry = _payload(_call(mcp_client, admin_token, "get_bauportal_entry", {"entry_id": build.id}))
    assert entry["raw_json"] == {"id": 1}
    assert entry["mapped_phase"] == "BAU"
    missing = _call(mcp_client, admin_token, "get_bauportal_entry", {"entry_id": 999})
    assert missing["isError"] is True


def test_assign_confirm_materialises_and_progress_names_entry(mcp_client, admin_token, db_session):
    alpha, _, build, _ = _seed(db_session)
    set_ = _payload(_call(mcp_client, admin_token, "assign_bauportal_entry",
                          {"entry_id": build.id, "project_id": alpha.id}))
    assert set_["confirmed"] is False
    done = _payload(_call(mcp_client, admin_token, "assign_bauportal_entry",
                          {"entry_id": build.id, "confirmed": True}))
    assert done["confirmed"] is True

    progress = _payload(_call(mcp_client, admin_token, "get_project_progress", {"project_id": alpha.id}))
    derived = [o for o in progress["observations"] if o["source_type"] == "BAUPORTAL"]
    assert len(derived) == 1
    assert derived[0]["bauportal_status_id"] == build.id
    assert derived[0]["bauportal"] == {
        "id": build.id, "shorttitle": build.shorttitle, "url": "https://bau.example/1"
    }

    cleared = _payload(_call(mcp_client, admin_token, "assign_bauportal_entry",
                             {"entry_id": build.id, "clear_project": True}))
    assert cleared["project_id"] is None and cleared["confirmed"] is False
    progress = _payload(_call(mcp_client, admin_token, "get_project_progress", {"project_id": alpha.id}))
    assert not [o for o in progress["observations"] if o["source_type"] == "BAUPORTAL"]


def test_assign_errors(mcp_client, admin_token, db_session):
    _, _, build, plan = _seed(db_session)
    for args in (
        {"entry_id": build.id},
        {"entry_id": build.id, "project_id": 99999},
        {"entry_id": 999, "confirmed": True},
        {"entry_id": build.id, "project_id": 1, "clear_project": True},
    ):
        assert _call(mcp_client, admin_token, "assign_bauportal_entry", args)["isError"] is True
    unconfirmed = _payload(_call(mcp_client, admin_token, "assign_bauportal_entry",
                                 {"entry_id": plan.id, "confirmed": True}))
    assert unconfirmed["confirmed"] is False and unconfirmed["warnings"]


def test_requires_progress_edit(mcp_client, db_session):
    _, _, build, _ = _seed(db_session)
    token = _key_for(db_session, _role_user(db_session, "reader", ["mcp.access"]))
    for name, args in (
        ("list_bauportal_entries", {}),
        ("get_bauportal_entry", {"entry_id": build.id}),
        ("assign_bauportal_entry", {"entry_id": build.id, "confirmed": True}),
    ):
        res = _call(mcp_client, token, name, args)
        assert res["isError"] is True
        assert "progress.edit" in res["content"][0]["text"]
