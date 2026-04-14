from __future__ import annotations

from uuid import uuid4

import pytest

from dashboard_backend.schemas.users import UserRole
from dashboard_backend.services.exceptions import RoutingUpstreamError
from tests.api.conftest import basic_auth_header


PROJECT_ID = 999  # arbitrary integer; project row does not need to exist for route storage

def _make_feature(cache_key: str = "testhash001", distance_m: float = 1200.5) -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[7.0, 51.0], [7.5, 51.5]],
        },
        "properties": {
            "distance_m": distance_m,
            "duration_ms": 480000,
            "profile": "rail_default",
            "graph_version": "test-graph",
            "bbox": [7.0, 51.0, 7.5, 51.5],
            "details": {},
            "cache_key": cache_key,
        },
    }


VALID_FEATURE = _make_feature()

CALCULATE_PAYLOAD = {
    "waypoints": [
        {"lat": 51.0, "lon": 7.0},
        {"lat": 51.5, "lon": 7.5},
    ],
    "profile": "rail_default",
    "options": {},
}


# ---------------------------------------------------------------------------
# Confirm route  POST /projects/{id}/routes
# ---------------------------------------------------------------------------

def test_create_route_requires_auth(client, routing_stub):
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/routes",
        json={"feature": VALID_FEATURE},
    )
    assert response.status_code == 401
    assert routing_stub.calls == 0


def test_create_route_success(client, create_user, routing_stub):
    create_user("planner", "secret123", UserRole.editor)
    headers = basic_auth_header("planner", "secret123")

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/routes",
        json={"feature": VALID_FEATURE},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == PROJECT_ID
    assert data["distance_m"] == pytest.approx(1200.5)
    assert data["duration_ms"] == 480000
    assert data["geom_geojson"]["type"] == "LineString"
    # Confirm does NOT call the routing service
    assert routing_stub.calls == 0

    # Second call with a different feature → second route stored for same project
    response2 = client.post(
        f"/api/v1/projects/{PROJECT_ID}/routes",
        json={"feature": _make_feature(cache_key="testhash002", distance_m=2500.0)},
        headers=headers,
    )
    assert response2.status_code == 201
    assert response2.json()["project_id"] == PROJECT_ID
    assert routing_stub.calls == 0


def test_list_routes_returns_routes(client, create_user, routing_stub):
    create_user("planner", "secret123", UserRole.editor)
    headers = basic_auth_header("planner", "secret123")

    post_response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/routes",
        json={"feature": VALID_FEATURE},
        headers=headers,
    )
    assert post_response.status_code == 201

    list_response = client.get(f"/api/v1/projects/{PROJECT_ID}/routes")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["project_id"] == PROJECT_ID


def test_get_route_detail(client, create_user, routing_stub):
    create_user("planner", "secret123", UserRole.editor)
    headers = basic_auth_header("planner", "secret123")

    post_response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/routes",
        json={"feature": VALID_FEATURE},
        headers=headers,
    )
    assert post_response.status_code == 201
    route_id = post_response.json()["route_id"]

    detail_response = client.get(f"/api/v1/routes/{route_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["route_id"] == route_id


def test_get_route_returns_404_for_unknown_route(client):
    response = client.get(f"/api/v1/routes/{uuid4()}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Calculate route  POST /routes/calculate
# ---------------------------------------------------------------------------

def test_calculate_route_returns_422_when_no_path(client, create_user, routing_stub):
    create_user("planner", "secret123", UserRole.editor)
    headers = basic_auth_header("planner", "secret123")
    routing_stub.next_response = {"paths": []}

    response = client.post(
        "/api/v1/routes/calculate",
        json=CALCULATE_PAYLOAD,
        headers=headers,
    )
    assert response.status_code == 422
    assert "routing service returned no paths" in response.json()["detail"]


def test_calculate_route_returns_502_on_upstream_error(client, create_user, routing_stub):
    create_user("planner", "secret123", UserRole.editor)
    headers = basic_auth_header("planner", "secret123")
    routing_stub.next_exception = RoutingUpstreamError("upstream boom")

    response = client.post(
        "/api/v1/routes/calculate",
        json=CALCULATE_PAYLOAD,
        headers=headers,
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "upstream boom"
