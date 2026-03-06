from unittest.mock import patch

import pytest

from dashboard_backend.celery_app import celery_app
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


@pytest.fixture(autouse=True)
def celery_eager(monkeypatch):
    """Run Celery tasks synchronously in-process; no broker needed."""
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)


@pytest.fixture(autouse=True)
def no_sleep():
    """Skip the artificial delay in the debug task during tests."""
    with patch("dashboard_backend.tasks.debug.time.sleep"):
        yield


# ---------------------------------------------------------------------------
# POST /api/v1/tasks/debug
# ---------------------------------------------------------------------------


def test_debug_task_requires_auth(client):
    response = client.post("/api/v1/tasks/debug", json={"x": 2, "y": 3})
    assert response.status_code == 401


def test_debug_task_starts_successfully(client, create_user):
    create_user("editor", "pass123", UserRole.editor)

    response = client.post(
        "/api/v1/tasks/debug",
        json={"x": 2, "y": 3},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert response.status_code == 200
    assert "task_id" in response.json()


# ---------------------------------------------------------------------------
# GET /api/v1/tasks/{task_id}
# ---------------------------------------------------------------------------


def test_task_status_requires_auth(client):
    response = client.get("/api/v1/tasks/some-task-id")
    assert response.status_code == 401


def test_task_roundtrip(client, create_user):
    """Start a debug task, then poll its status and verify SUCCESS + result."""
    create_user("editor", "pass123", UserRole.editor)
    headers = basic_auth_header("editor", "pass123")

    # Start task
    start_resp = client.post(
        "/api/v1/tasks/debug",
        json={"x": 4, "y": 6},
        headers=headers,
    )
    assert start_resp.status_code == 200
    task_id = start_resp.json()["task_id"]

    # Poll status — with task_always_eager the task has already completed
    status_resp = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["status"] == "SUCCESS"
    assert data["result"] == 10
    assert data["error"] is None
