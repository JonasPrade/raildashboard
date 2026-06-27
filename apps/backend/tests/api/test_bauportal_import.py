"""Tests for the /api/v1/import/bauportal endpoints.

Per project convention the CRUD layer is monkeypatched so these tests need no
Bauportal tables in the SQLite schema and never touch the live network.
"""

from __future__ import annotations

import httpx

import dashboard_backend.api.v1.endpoints.bauportal_import as bauportal_route
from dashboard_backend.crud.bauportal import ProjectNotFoundError
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def _entry(entry_id: int = 1, **overrides) -> dict:
    entry = {
        "id": entry_id,
        "bauportal_id": 12082,
        "parent_bauportal_id": None,
        "shorttitle": "740 Meter-Netz – Röblingen am See Bahnhof",
        "status_raw": "Projekt in der Bauphase",
        "mapped_phase": "BAU",
        "projecttime_raw": "2024 – 2026",
        "url": "https://example.org/x",
        "lat": 51.4,
        "lng": 11.6,
        "fetched_at": None,
        "suggested_project_id": 5,
        "suggested_project_name": "Röblingen",
        "project_id": None,
        "project_name": None,
    }
    entry.update(overrides)
    return entry


# --- auth --------------------------------------------------------------------


def test_entries_requires_auth(client):
    assert client.get("/api/v1/import/bauportal/entries").status_code == 401


def test_fetch_forbidden_for_viewer(client, create_user):
    create_user("viewer-bp", "pass123", UserRole.viewer)
    resp = client.post(
        "/api/v1/import/bauportal/fetch",
        headers=basic_auth_header("viewer-bp", "pass123"),
    )
    assert resp.status_code == 403


# --- fetch -------------------------------------------------------------------


def test_fetch_returns_summary(client, create_user, monkeypatch):
    create_user("editor-bp", "pass123", UserRole.editor)
    monkeypatch.setattr(
        bauportal_route.bauportal_crud,
        "run_import",
        lambda db: {"fetched": 295, "created": 295, "updated": 0, "skipped": 0},
    )
    resp = client.post(
        "/api/v1/import/bauportal/fetch",
        headers=basic_auth_header("editor-bp", "pass123"),
    )
    assert resp.status_code == 200
    assert resp.json()["fetched"] == 295


def test_fetch_reports_network_error_as_502(client, create_user, monkeypatch):
    create_user("editor-bp2", "pass123", UserRole.editor)

    def _boom(db):
        raise httpx.ConnectError("no route to host")

    monkeypatch.setattr(bauportal_route.bauportal_crud, "run_import", _boom)
    resp = client.post(
        "/api/v1/import/bauportal/fetch",
        headers=basic_auth_header("editor-bp2", "pass123"),
    )
    assert resp.status_code == 502


# --- list --------------------------------------------------------------------


def test_list_entries(client, create_user, monkeypatch):
    create_user("editor-bp3", "pass123", UserRole.editor)
    monkeypatch.setattr(
        bauportal_route.bauportal_crud,
        "list_entries",
        lambda db, only_unconfirmed=False: [_entry(1), _entry(2, project_id=9, project_name="X")],
    )
    resp = client.get(
        "/api/v1/import/bauportal/entries",
        headers=basic_auth_header("editor-bp3", "pass123"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["mapped_phase"] == "BAU"


# --- confirm match -----------------------------------------------------------


def test_confirm_match(client, create_user, monkeypatch):
    create_user("editor-bp4", "pass123", UserRole.editor)
    captured = {}

    def _confirm(db, entry_id, project_id):
        captured["entry_id"] = entry_id
        captured["project_id"] = project_id
        return _entry(entry_id, project_id=project_id, project_name="Röblingen")

    monkeypatch.setattr(bauportal_route.bauportal_crud, "confirm_match", _confirm)
    resp = client.patch(
        "/api/v1/import/bauportal/entries/1",
        json={"project_id": 5},
        headers=basic_auth_header("editor-bp4", "pass123"),
    )
    assert resp.status_code == 200
    assert captured == {"entry_id": 1, "project_id": 5}
    assert resp.json()["project_id"] == 5


def test_confirm_unknown_project_404(client, create_user, monkeypatch):
    create_user("editor-bp5", "pass123", UserRole.editor)

    def _confirm(db, entry_id, project_id):
        raise ProjectNotFoundError("Project 999 not found")

    monkeypatch.setattr(bauportal_route.bauportal_crud, "confirm_match", _confirm)
    resp = client.patch(
        "/api/v1/import/bauportal/entries/1",
        json={"project_id": 999},
        headers=basic_auth_header("editor-bp5", "pass123"),
    )
    assert resp.status_code == 404


def test_confirm_missing_entry_404(client, create_user, monkeypatch):
    create_user("editor-bp6", "pass123", UserRole.editor)
    monkeypatch.setattr(
        bauportal_route.bauportal_crud, "confirm_match", lambda db, e, p: None
    )
    resp = client.patch(
        "/api/v1/import/bauportal/entries/999",
        json={"project_id": None},
        headers=basic_auth_header("editor-bp6", "pass123"),
    )
    assert resp.status_code == 404
