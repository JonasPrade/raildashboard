"""MCP geometry tools: operational-point search, geometry summary, routing and
manual editing. The routing service is the conftest stub (no GraphHopper)."""

from __future__ import annotations

import json

from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.railway_infrastructure.operational_point import OperationalPoint
from dashboard_backend.models.routes import Route
from dashboard_backend.schemas.users import UserRole
from dashboard_backend.services.exceptions import RoutingNoPathError, RoutingUpstreamError
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    admin_token,
    mcp_client,
)

EXISTING_LINE = json.dumps(
    {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[8.0, 50.0], [8.0, 50.5]]},
                "properties": {},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [8.0, 50.0]},
                "properties": {"name": "Alt", "op_id": "XALT", "feature_type": "operational_point"},
            },
        ],
    }
)


def _seed(db):
    project = Project(name="ABS Test", is_draft=False, geojson_representation=EXISTING_LINE)
    koeln = OperationalPoint(op_id="KK", name="Köln Hbf", type="station", latitude=50.94, longitude=6.96)
    koeln_west = OperationalPoint(
        op_id="KKW", name="Köln West", type="station", latitude=50.94, longitude=6.93
    )
    dortmund = OperationalPoint(
        op_id="EDO", name="Dortmund Hbf", type="station", latitude=51.52, longitude=7.46
    )
    no_coords = OperationalPoint(op_id="XNC", name="Ohne Koordinaten", type="station")
    db.add_all([project, koeln, koeln_west, dortmund, no_coords])
    db.commit()
    return project, koeln, dortmund


def _features(project: Project) -> list[dict]:
    return json.loads(project.geojson_representation)["features"]


def test_search_operational_points(mcp_client, admin_token, db_session):
    _seed(db_session)
    found = _payload(
        _call(mcp_client, admin_token, "search_operational_points", {"query": "köln"})
    )["operational_points"]
    assert {op["op_id"] for op in found} == {"KK", "KKW"}
    exact = _payload(
        _call(mcp_client, admin_token, "search_operational_points", {"query": "edo"})
    )["operational_points"]
    assert exact[0]["name"] == "Dortmund Hbf"
    assert exact[0]["lat"] == 51.52
    assert _call(mcp_client, admin_token, "search_operational_points", {"query": "k"})["isError"]


def test_get_project_geometry(mcp_client, admin_token, db_session):
    project, _, _ = _seed(db_session)
    result = _payload(
        _call(mcp_client, admin_token, "get_project_geometry", {"project_id": project.id})
    )
    assert result["editable"] is True
    assert result["feature_count"] == 2
    assert result["line_count"] == 1 and result["point_count"] == 1
    assert 55 < result["length_km"] < 56
    assert result["bbox"] == [8.0, 50.0, 8.0, 50.5]
    line, point = result["features"]
    assert line["index"] == 0 and line["start"] == [8.0, 50.0] and line["end"] == [8.0, 50.5]
    assert point["op_id"] == "XALT" and point["coordinates"] == [8.0, 50.0]
    assert "geojson" not in result

    full = _payload(
        _call(
            mcp_client,
            admin_token,
            "get_project_geometry",
            {"project_id": project.id, "include_geojson": True},
        )
    )
    assert full["geojson"]["features"][0]["geometry"]["type"] == "LineString"


def test_route_preview_does_not_write(mcp_client, admin_token, db_session, routing_stub):
    project, koeln, dortmund = _seed(db_session)
    result = _payload(
        _call(
            mcp_client,
            admin_token,
            "route_project_geometry",
            {"project_id": project.id, "waypoints": ["Köln Hbf", dortmund.id]},
        )
    )
    assert routing_stub.calls == 1
    assert result["applied"] is False
    assert result["route"]["distance_km"] == 1.2
    assert result["route"]["duration_min"] == 8
    assert [w["op_id"] for w in result["route"]["waypoints"]] == ["KK", "EDO"]
    # Existing line + point and the route; waypoints are not added as points by default.
    assert result["geometry"]["feature_count"] == 3
    db_session.refresh(project)
    assert project.geojson_representation == EXISTING_LINE
    assert db_session.query(Route).filter_by(project_id=project.id).count() == 0
    assert db_session.query(ChangeLog).filter_by(project_id=project.id).count() == 0


def test_route_apply_replace_writes_changelog_and_route(
    mcp_client, admin_token, db_session, routing_stub
):
    project, koeln, _ = _seed(db_session)
    result = _payload(
        _call(
            mcp_client,
            admin_token,
            "route_project_geometry",
            {
                "project_id": project.id,
                "waypoints": ["kk", {"lat": 51.5, "lon": 7.5}],
                "mode": "replace",
                "add_stations": True,
                "apply": True,
            },
        )
    )
    assert result["applied"] is True
    db_session.refresh(project)
    features = _features(project)
    assert [f["geometry"]["type"] for f in features] == ["LineString", "Point"]
    assert features[0]["geometry"]["coordinates"] == [[7.0, 51.0], [7.5, 51.5]]
    assert features[1]["properties"]["op_id"] == "KK"
    [entry] = db_session.query(ChangeLog).filter_by(project_id=project.id).one().entries
    assert entry.field_name == "geojson_representation"
    assert json.loads(entry.old_value) == EXISTING_LINE
    assert db_session.query(Route).filter_by(project_id=project.id).count() == 1


def test_route_append_skips_present_station(mcp_client, admin_token, db_session):
    project, koeln, dortmund = _seed(db_session)
    project.geojson_representation = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [6.96, 50.94]},
                    "properties": {"op_id": "KK"},
                }
            ],
        }
    )
    db_session.commit()
    _payload(
        _call(
            mcp_client,
            admin_token,
            "route_project_geometry",
            {
                "project_id": project.id,
                "waypoints": [koeln.id, dortmund.id],
                "add_stations": True,
                "apply": True,
            },
        )
    )
    db_session.refresh(project)
    op_ids = [f["properties"].get("op_id") for f in _features(project)]
    assert op_ids == ["KK", None, "EDO"]


def test_route_errors(mcp_client, admin_token, db_session, routing_stub):
    project, koeln, dortmund = _seed(db_session)
    args = {"project_id": project.id, "waypoints": [koeln.id, dortmund.id]}

    routing_stub.next_exception = RoutingNoPathError("none")
    result = _call(mcp_client, admin_token, "route_project_geometry", args)
    assert result["isError"] and "Kein Pfad" in result["content"][0]["text"]

    routing_stub.next_exception = RoutingUpstreamError("down")
    result = _call(mcp_client, admin_token, "route_project_geometry", args)
    assert result["isError"] and "nicht erreichbar" in result["content"][0]["text"]

    ambiguous = _call(
        mcp_client,
        admin_token,
        "route_project_geometry",
        {"project_id": project.id, "waypoints": ["Köln", dortmund.id]},
    )
    assert ambiguous["isError"] and "mehrdeutig" in ambiguous["content"][0]["text"]

    no_coords = _call(
        mcp_client,
        admin_token,
        "route_project_geometry",
        {"project_id": project.id, "waypoints": ["XNC", dortmund.id]},
    )
    assert no_coords["isError"] and "keine Koordinaten" in no_coords["content"][0]["text"]

    single = _call(
        mcp_client,
        admin_token,
        "route_project_geometry",
        {"project_id": project.id, "waypoints": [koeln.id]},
    )
    assert single["isError"]


def test_aggregated_parent_is_not_editable(mcp_client, admin_token, db_session, routing_stub):
    project, koeln, dortmund = _seed(db_session)
    db_session.add(Project(name="Etappe", is_draft=False, superior_project_id=project.id))
    project.geojson_from_subprojects = True
    db_session.commit()

    geometry = _payload(
        _call(mcp_client, admin_token, "get_project_geometry", {"project_id": project.id})
    )
    assert geometry["aggregated_from_subprojects"] is True and geometry["editable"] is False

    routed = _call(
        mcp_client,
        admin_token,
        "route_project_geometry",
        {"project_id": project.id, "waypoints": [koeln.id, dortmund.id]},
    )
    assert routed["isError"] and "geojson_from_subprojects" in routed["content"][0]["text"]
    assert routing_stub.calls == 0
    edited = _call(
        mcp_client,
        admin_token,
        "edit_project_geometry",
        {"project_id": project.id, "replace": True},
    )
    assert edited["isError"]


def test_edit_geometry_draw_remove_and_points(mcp_client, admin_token, db_session):
    project, koeln, _ = _seed(db_session)
    result = _payload(
        _call(
            mcp_client,
            admin_token,
            "edit_project_geometry",
            {
                "project_id": project.id,
                "remove_feature_indices": [0],
                "add_features": [
                    {"type": "LineString", "coordinates": [[9.0, 52.0], [9.1, 52.1]]},
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [52.0, 9.0]},
                        "properties": {"name": "Swapped"},
                    },
                ],
                "add_operational_points": ["Köln Hbf"],
            },
        )
    )
    assert result["applied"] is True
    assert len(result["warnings"]) == 1 and "vertauscht" in result["warnings"][0]
    db_session.refresh(project)
    features = _features(project)
    assert [f["geometry"]["type"] for f in features] == ["Point", "LineString", "Point", "Point"]
    assert features[0]["properties"]["op_id"] == "XALT"
    assert features[2]["properties"] == {"name": "Swapped"}
    assert features[3]["properties"]["op_id"] == "KK"
    assert db_session.query(ChangeLog).filter_by(project_id=project.id).count() == 1


def test_edit_geometry_replace_alone_clears(mcp_client, admin_token, db_session):
    project, _, _ = _seed(db_session)
    result = _payload(
        _call(
            mcp_client, admin_token, "edit_project_geometry", {"project_id": project.id, "replace": True}
        )
    )
    assert result["geometry"]["feature_count"] == 0
    db_session.refresh(project)
    assert project.geojson_representation is None


def test_edit_geometry_rejections(mcp_client, admin_token, db_session):
    project, _, _ = _seed(db_session)

    def error(arguments):
        result = _call(
            mcp_client, admin_token, "edit_project_geometry", {"project_id": project.id, **arguments}
        )
        assert result["isError"], result
        return result["content"][0]["text"]

    assert "Keine Änderung" in error({})
    assert "existiert nicht" in error({"remove_feature_indices": [5]})
    assert "schließen sich aus" in error({"replace": True, "remove_feature_indices": [0]})
    assert "zwei Koordinaten" in error(
        {"add_features": [{"type": "LineString", "coordinates": [[8.0, 50.0]]}]}
    )
    assert "nicht unterstützt" in error(
        {"add_features": [{"type": "Polygon", "coordinates": [[[8, 50], [9, 50], [8, 51], [8, 50]]]}]}
    )
    assert "außerhalb" in error({"add_features": [{"type": "Point", "coordinates": [200, 50]}]})
    db_session.refresh(project)
    assert project.geojson_representation == EXISTING_LINE


def test_geometry_writes_need_capability(mcp_client, create_user, db_session, routing_stub):
    admin = create_user("admin", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["mcp.access"])
    project, koeln, dortmund = _seed(db_session)

    assert not _call(mcp_client, token, "get_project_geometry", {"project_id": project.id})[
        "isError"
    ]
    routed = _call(
        mcp_client,
        token,
        "route_project_geometry",
        {"project_id": project.id, "waypoints": [koeln.id, dortmund.id]},
    )
    assert routed["isError"] and "project.edit" in routed["content"][0]["text"]
    assert routing_stub.calls == 0
    edited = _call(mcp_client, token, "edit_project_geometry", {"project_id": project.id, "replace": True})
    assert edited["isError"] and "project.edit" in edited["content"][0]["text"]
