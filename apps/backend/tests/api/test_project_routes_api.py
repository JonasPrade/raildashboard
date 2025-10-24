from __future__ import annotations

from uuid import uuid4

import pytest

from dashboard_backend.schemas.users import UserRole
from dashboard_backend.services.exceptions import RoutingUpstreamError
from tests.api.conftest import basic_auth_header


@pytest.fixture()
def project_id() -> str:
    return str(uuid4())


@pytest.fixture()
def route_payload(project_id: str):
    return {
        "waypoints": [
            {"lat": 51.0, "lon": 7.0},
            {"lat": 51.5, "lon": 7.5},
        ],
        "profile": "rail_default",
        "options": {},
    }


def test_create_route_requires_auth(client, project_id, route_payload, routing_stub):
    response = client.post(f"/api/v1/projects/{project_id}/routes", json=route_payload)
    assert response.status_code == 401
    assert routing_stub.calls == 0


def test_create_route_success(client, create_user, project_id, route_payload, routing_stub):
    create_user("planner", "secret123", UserRole.viewer)
    headers = basic_auth_header("planner", "secret123")

    response = client.post(f"/api/v1/projects/{project_id}/routes", json=route_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == project_id
    assert data["distance_m"] == pytest.approx(1200.5)
    assert data["duration_ms"] == 480000
    assert data["geom_geojson"]["type"] == "LineString"
    assert routing_stub.calls == 1

    response_repeat = client.post(
        f"/api/v1/projects/{project_id}/routes", json=route_payload, headers=headers
    )
    assert response_repeat.status_code == 201
    assert routing_stub.calls == 1


def test_list_routes_returns_routes(client, create_user, project_id, route_payload, routing_stub):
    create_user("planner", "secret123", UserRole.viewer)
    headers = basic_auth_header("planner", "secret123")

    post_response = client.post(
        f"/api/v1/projects/{project_id}/routes", json=route_payload, headers=headers
    )
    assert post_response.status_code == 201

    list_response = client.get(f"/api/v1/projects/{project_id}/routes")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["project_id"] == project_id



def test_get_route_detail(client, create_user, project_id, route_payload, routing_stub):
    create_user("planner", "secret123", UserRole.viewer)
    headers = basic_auth_header("planner", "secret123")
    post_response = client.post(
        f"/api/v1/projects/{project_id}/routes", json=route_payload, headers=headers
    )
    route_id = post_response.json()["route_id"]

    detail_response = client.get(f"/api/v1/routes/{route_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["route_id"] == route_id



def test_create_route_returns_422_when_no_path(
    client,
    create_user,
    project_id,
    route_payload,
    routing_stub,
):
    create_user("planner", "secret123", UserRole.viewer)
    headers = basic_auth_header("planner", "secret123")
    routing_stub.next_response = {"paths": []}

    response = client.post(
        f"/api/v1/projects/{project_id}/routes", json=route_payload, headers=headers
    )
    assert response.status_code == 422
    assert "routing service returned no paths" in response.json()["detail"]



def test_create_route_returns_502_on_upstream_error(
    client,
    create_user,
    project_id,
    route_payload,
    routing_stub,
):
    create_user("planner", "secret123", UserRole.viewer)
    headers = basic_auth_header("planner", "secret123")
    routing_stub.next_exception = RoutingUpstreamError("upstream boom")

    response = client.post(
        f"/api/v1/projects/{project_id}/routes", json=route_payload, headers=headers
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "upstream boom"


def test_get_route_returns_404_for_unknown_route(client):
    response = client.get(f"/api/v1/routes/{uuid4()}")
    assert response.status_code == 404
