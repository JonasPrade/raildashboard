"""Tests for the /api/v1/health endpoint (docker healthcheck target)."""
from __future__ import annotations


def test_health_returns_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_requires_no_auth(client):
    # Healthcheck must work without any credentials — docker invokes it from inside the container.
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "WWW-Authenticate" not in resp.headers
