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


# --- /healthz: the deploy gate ------------------------------------------------

import pytest
from sqlalchemy import text

from dashboard_backend.core.config import settings


@pytest.fixture
def writable_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "import_staging_dir", str(tmp_path / "staging"))
    return tmp_path


def test_healthz_ok_when_ready(client, writable_dirs):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_healthz_requires_no_auth(client, writable_dirs):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert "WWW-Authenticate" not in resp.headers


def test_healthz_is_not_part_of_the_api_schema(client):
    assert "/healthz" not in client.get("/openapi.json").json()["paths"]


def test_healthz_fails_when_a_mapped_column_is_missing(client, writable_dirs, tmp_path):
    # The rollback case: an older image whose model still maps a column that a
    # newer migration dropped. SELECT 1 stays green; /healthz must not.
    # A separate database, because SQLite DDL is not rolled back with the
    # per-test transaction.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from dashboard_backend.database import get_db
    from main import app

    engine = create_engine(f"sqlite:///{tmp_path / 'old-schema.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE project (id INTEGER PRIMARY KEY)"))
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db] = lambda: session
    try:
        resp = client.get("/healthz")
    finally:
        session.close()
        engine.dispose()
    assert resp.status_code == 503
    assert resp.json()["problems"] == ["schema"]


@pytest.mark.parametrize("value", ["", "change-me-generate-a-random-32-byte-hex-string"])
def test_healthz_fails_on_placeholder_session_secret(client, writable_dirs, monkeypatch, value):
    monkeypatch.setattr(settings, "session_secret_key", value)
    resp = client.get("/healthz")
    assert resp.status_code == 503
    assert resp.json()["problems"] == ["session_secret_key"]


def test_healthz_fails_when_upload_dir_is_not_writable(client, writable_dirs, monkeypatch):
    blocker = writable_dirs / "a-file"
    blocker.write_text("")
    monkeypatch.setattr(settings, "upload_dir", str(blocker / "uploads"))
    resp = client.get("/healthz")
    assert resp.status_code == 503
    assert resp.json()["problems"] == ["upload_dir"]
