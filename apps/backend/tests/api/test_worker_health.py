"""Tests for the worker health check and the hints on /api/v1/tasks/{id}.

The point of both is the case where nothing is wrong with the request and
everything is wrong with the stack: a job is accepted, Celery answers PENDING,
and no worker will ever pick it up. These tests pin the wording down to "the
answer names the problem and the next step", because a hint that merely says
"läuft noch" would be the bug all over again.
"""
from __future__ import annotations

import base64

import dashboard_backend.api.v1.endpoints.tasks as tasks_route
from dashboard_backend.schemas.tasks import WorkerHealthSchema, WorkerSchema
from dashboard_backend.schemas.users import UserRole
from dashboard_backend.services import worker_health as health_service


def _auth(username: str, password: str) -> dict[str, str]:
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def _health(status: str, **overrides) -> WorkerHealthSchema:
    defaults = dict(
        status=status,
        broker_reachable=status != "broker_unreachable",
        broker_url="redis://redis:6379/0",
        workers=[WorkerSchema(name="celery@worker", active_tasks=1, active_task_names=["parse"])]
        if status == "ok"
        else [],
        queued_tasks=0,
        message="Testmeldung",
        detail=None,
        checked_at=1_700_000_000.0,
    )
    defaults.update(overrides)
    return WorkerHealthSchema(**defaults)


class _FakeResult:
    """Stand-in for celery.AsyncResult — only what the endpoint reads."""

    def __init__(self, status: str, result=None, traceback: str | None = None):
        self.status = status
        self.result = result
        self.traceback = traceback


# --- /api/v1/tasks/workers --------------------------------------------------

def test_worker_health_requires_auth(client):
    assert client.get("/api/v1/tasks/workers").status_code == 401


def test_worker_health_requires_settings_permission(client, create_user):
    create_user("editor_wh1", "pass", UserRole.editor)
    resp = client.get("/api/v1/tasks/workers", headers=_auth("editor_wh1", "pass"))
    assert resp.status_code == 403


def test_worker_health_reports_online_workers(client, monkeypatch, create_user):
    create_user("admin_wh1", "pass", UserRole.admin)
    monkeypatch.setattr(tasks_route, "cached_worker_health", lambda: _health("ok"))

    resp = client.get("/api/v1/tasks/workers", headers=_auth("admin_wh1", "pass"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["workers"][0]["name"] == "celery@worker"


def test_worker_health_refresh_bypasses_the_cache(client, monkeypatch, create_user):
    create_user("admin_wh2", "pass", UserRole.admin)
    calls: list[str] = []
    monkeypatch.setattr(
        tasks_route, "cached_worker_health", lambda: calls.append("cached") or _health("ok")
    )
    monkeypatch.setattr(
        tasks_route, "worker_health", lambda: calls.append("fresh") or _health("no_workers")
    )
    monkeypatch.setattr(tasks_route, "reset_cache", lambda: calls.append("reset"))

    resp = client.get("/api/v1/tasks/workers?refresh=true", headers=_auth("admin_wh2", "pass"))
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_workers"
    assert calls == ["reset", "fresh"]


# --- /api/v1/tasks/{task_id} ------------------------------------------------

def test_pending_task_without_worker_explains_itself(client, monkeypatch, create_user):
    create_user("editor_wh2", "pass", UserRole.editor)
    monkeypatch.setattr(
        tasks_route.celery_app, "AsyncResult", lambda task_id: _FakeResult("PENDING")
    )
    monkeypatch.setattr(
        tasks_route,
        "cached_worker_health",
        lambda: _health("no_workers", message="Kein Worker online. …"),
    )

    resp = client.get("/api/v1/tasks/abc", headers=_auth("editor_wh2", "pass"))
    assert resp.status_code == 200
    assert resp.json()["hint"] == "Kein Worker online. …"


def test_pending_task_with_healthy_workers_has_no_hint(client, monkeypatch, create_user):
    create_user("editor_wh3", "pass", UserRole.editor)
    monkeypatch.setattr(
        tasks_route.celery_app, "AsyncResult", lambda task_id: _FakeResult("PENDING")
    )
    monkeypatch.setattr(tasks_route, "cached_worker_health", lambda: _health("ok"))

    resp = client.get("/api/v1/tasks/abc", headers=_auth("editor_wh3", "pass"))
    assert resp.json()["hint"] is None


def test_failed_task_names_exception_and_location(client, monkeypatch, create_user):
    create_user("editor_wh4", "pass", UserRole.editor)
    traceback = (
        'Traceback (most recent call last):\n'
        '  File "/app/dashboard_backend/tasks/haushalt.py", line 912, in _extract_pages\n'
        '    raise ValueError("kaputt")\n'
        'ValueError: kaputt\n'
    )
    monkeypatch.setattr(
        tasks_route.celery_app,
        "AsyncResult",
        lambda task_id: _FakeResult("FAILURE", ValueError("kaputt"), traceback),
    )

    body = client.get("/api/v1/tasks/abc", headers=_auth("editor_wh4", "pass")).json()
    assert body["error"] == "ValueError: kaputt"
    assert "haushalt.py:912" in body["hint"]
    assert "_extract_pages" in body["hint"]
    assert "worker" in body["hint"]


def test_failure_reports_the_real_class_not_celery_s_placeholder(client, monkeypatch, create_user):
    # With the JSON result serializer Celery cannot rebuild the original class:
    # `result.result` is a plain Exception carrying the repr of the real one.
    # The traceback still names it, and that is what the user needs to search for.
    create_user("editor_wh6", "pass", UserRole.editor)
    traceback = (
        'Traceback (most recent call last):\n'
        '  File "/app/dashboard_backend/tasks/haushalt.py", line 1642, in parse_haushalt_pdf\n'
        '    db.query(Project).all()\n'
        '  File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute\n'
        '    cursor.execute(statement, parameters)\n'
        'sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such function: AsEWKB\n'
    )
    placeholder = Exception("<class 'sqlalchemy.exc.OperationalError'>(['no such function'])")
    monkeypatch.setattr(
        tasks_route.celery_app,
        "AsyncResult",
        lambda task_id: _FakeResult("FAILURE", placeholder, traceback),
    )

    body = client.get("/api/v1/tasks/abc", headers=_auth("editor_wh6", "pass")).json()
    assert body["error"] == "OperationalError: (sqlite3.OperationalError) no such function: AsEWKB"
    # The deepest frame is inside SQLAlchemy; the lead is our own last frame.
    assert "haushalt.py:1642" in body["hint"]
    assert "default.py" not in body["hint"]


def test_failure_without_traceback_still_names_the_log(client, monkeypatch, create_user):
    create_user("editor_wh5", "pass", UserRole.editor)
    monkeypatch.setattr(
        tasks_route.celery_app,
        "AsyncResult",
        lambda task_id: _FakeResult("FAILURE", KeyError("finve_nr"), None),
    )

    body = client.get("/api/v1/tasks/abc", headers=_auth("editor_wh5", "pass")).json()
    assert body["error"].startswith("KeyError:")
    assert "docker compose logs" in body["hint"]


# --- the probe itself -------------------------------------------------------

def test_broker_unreachable_is_a_value_not_an_exception(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise OSError("Connection refused")

    monkeypatch.setattr(health_service.celery_app, "connection", _boom)
    health = health_service.worker_health(timeout=0.01)

    assert health.status == "broker_unreachable"
    assert health.broker_reachable is False
    assert "Connection refused" in (health.detail or "")
    assert "redis" in health.message.lower()


def test_broker_url_is_handed_out_without_credentials():
    assert (
        health_service.sanitize_broker_url("redis://:sup3rsecret@redis.internal:6379/0")
        == "redis://redis.internal:6379/0"
    )
    assert health_service.sanitize_broker_url(None) == ""


def test_cached_health_probes_at_most_once_per_ttl(monkeypatch):
    calls: list[int] = []

    def _probe(timeout: float = 1.0) -> WorkerHealthSchema:
        calls.append(1)
        return _health("ok")

    health_service.reset_cache()
    monkeypatch.setattr(health_service, "worker_health", _probe)
    health_service.cached_worker_health()
    health_service.cached_worker_health()
    assert len(calls) == 1

    health_service.reset_cache()
    health_service.cached_worker_health()
    assert len(calls) == 2
    health_service.reset_cache()
