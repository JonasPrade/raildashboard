"""Tests for the routing-service check on the system status page."""
from __future__ import annotations

import base64

import httpx

import dashboard_backend.api.v1.endpoints.system as system_route
from dashboard_backend.schemas.users import UserRole
from dashboard_backend.services import routing_health as service


def _auth(username: str, password: str) -> dict[str, str]:
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def test_routing_health_requires_auth(client):
    assert client.get("/api/v1/system/routing").status_code == 401


def test_routing_health_requires_settings_permission(client, create_user):
    create_user("editor_rh1", "pass", UserRole.editor)
    resp = client.get("/api/v1/system/routing", headers=_auth("editor_rh1", "pass"))
    assert resp.status_code == 403


def test_routing_health_endpoint_returns_probe(client, monkeypatch, create_user):
    create_user("admin_rh1", "pass", UserRole.admin)
    monkeypatch.setattr(
        system_route,
        "routing_health",
        lambda: service.RoutingHealthSchema(
            status="ok", base_url="http://graphhopper:8989", message="ok", checked_at=1.0
        ),
    )
    resp = client.get("/api/v1/system/routing", headers=_auth("admin_rh1", "pass"))
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_probe_ok(monkeypatch):
    monkeypatch.setattr(service.httpx, "get", lambda url, timeout: httpx.Response(200))
    health = service.routing_health()
    assert health.status == "ok"
    assert health.http_status == 200


def test_probe_bad_status(monkeypatch):
    monkeypatch.setattr(service.httpx, "get", lambda url, timeout: httpx.Response(500))
    health = service.routing_health()
    assert health.status == "error"
    assert health.http_status == 500


def test_probe_unreachable_names_next_step(monkeypatch):
    def refuse(url, timeout):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(service.httpx, "get", refuse)
    health = service.routing_health()
    assert health.status == "unreachable"
    assert "docker compose" in health.message
    assert "ConnectError" in (health.detail or "")
