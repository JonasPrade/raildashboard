"""MCP constituency / member-of-parliament tools (read-only)."""

from __future__ import annotations

from dashboard_backend.models.projects.project import Project
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    _role_user,
    admin_token,
    mcp_client,
)
from tests.api.test_parliament import PROJECT_ID, parliament_data  # noqa: F401 - fixture


def _project(db):
    project = db.get(Project, PROJECT_ID)
    project.geojson_representation = '{"type": "FeatureCollection", "features": []}'
    db.commit()
    return project


def test_list_politicians_committee_first_with_status(mcp_client, admin_token, parliament_data):
    result = _payload(_call(mcp_client, admin_token, "list_politicians"))
    assert result["total"] == 3
    first = result["politicians"][0]
    assert first["name"] == "Tarek Al-Wazir"
    assert first["committees"][0]["key"] == "verkehr"
    assert first["project_count"] == 1
    assert result["data_status"]["is_stale"] is False
    assert result["data_status"]["period"] == "Bundestag 2025 - 2029"

    transport = _payload(
        _call(mcp_client, admin_token, "list_politicians", {"committee": "verkehr"})
    )
    assert [p["name"] for p in transport["politicians"]] == ["Tarek Al-Wazir"]
    by_name = _payload(_call(mcp_client, admin_token, "list_politicians", {"search": "anne"}))
    assert [p["name"] for p in by_name["politicians"]] == ["Änne Beispiel"]
    paged = _payload(_call(mcp_client, admin_token, "list_politicians", {"limit": 1, "offset": 1}))
    assert paged["total"] == 3 and len(paged["politicians"]) == 1


def test_get_politician_lists_constituency_projects(mcp_client, admin_token, parliament_data):
    mandate_id = parliament_data["chair_mandate"].id
    detail = _payload(_call(mcp_client, admin_token, "get_politician", {"mandate_id": mandate_id}))
    assert detail["constituency"]["number"] == 182
    assert [p["project_id"] for p in detail["projects"]] == [PROJECT_ID]
    assert detail["projects"][0]["length_km"] == 51.0
    missing = _call(mcp_client, admin_token, "get_politician", {"mandate_id": 999999})
    assert missing["isError"] is True


def test_constituencies_list_and_detail(mcp_client, admin_token, parliament_data):
    listed = _payload(_call(mcp_client, admin_token, "list_constituencies"))
    assert [c["number"] for c in listed["constituencies"]] == [1, 42, 182]
    hessen = _payload(
        _call(
            mcp_client,
            admin_token,
            "list_constituencies",
            {"state": "hessen", "only_with_projects": True},
        )
    )
    assert [c["name"] for c in hessen["constituencies"]] == ["Offenbach"]
    by_number = _payload(_call(mcp_client, admin_token, "list_constituencies", {"search": "182"}))
    assert by_number["total"] == 1

    detail = _payload(
        _call(
            mcp_client,
            admin_token,
            "get_constituency",
            {"constituency_id": parliament_data["offenbach"].id},
        )
    )
    assert [m["name"] for m in detail["direct_mandates"]] == ["Tarek Al-Wazir"]
    assert [m["name"] for m in detail["list_mandates"]] == ["Änne Beispiel"]
    assert [p["project_id"] for p in detail["projects"]] == [PROJECT_ID]


def test_project_constituencies_heaviest_first(mcp_client, admin_token, parliament_data, db_session):
    _project(db_session)
    result = _payload(
        _call(mcp_client, admin_token, "get_project_constituencies", {"project_id": PROJECT_ID})
    )
    assert result["has_geometry"] is True
    assert [c["number"] for c in result["constituencies"]] == [182, 1]
    assert result["constituencies"][0]["has_direct_mandate"] is True
    assert result["project_name"] == "ABS Test"
    assert result["data_status"]["last_import"] is not None


def test_readable_with_any_mcp_key(mcp_client, db_session, parliament_data):
    token = _key_for(db_session, _role_user(db_session, "nurlesen", ["mcp.access"]))
    assert _payload(_call(mcp_client, token, "list_politicians"))["total"] == 3
