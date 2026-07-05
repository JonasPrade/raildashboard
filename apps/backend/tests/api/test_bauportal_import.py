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
        "confirmed": False,
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


# --- update / confirm --------------------------------------------------------


def test_update_assign_and_confirm(client, create_user, monkeypatch):
    create_user("editor-bp4", "pass123", UserRole.editor)
    captured = {}

    def _update(db, entry_id, payload):
        captured["entry_id"] = entry_id
        captured["payload"] = payload
        return _entry(entry_id, project_id=5, project_name="Röblingen", confirmed=True)

    monkeypatch.setattr(bauportal_route.bauportal_crud, "update_entry", _update)
    resp = client.patch(
        "/api/v1/import/bauportal/entries/1",
        json={"project_id": 5, "confirmed": True},
        headers=basic_auth_header("editor-bp4", "pass123"),
    )
    assert resp.status_code == 200
    assert captured["entry_id"] == 1
    assert captured["payload"] == {"project_id": 5, "confirmed": True}
    assert resp.json()["project_id"] == 5
    assert resp.json()["confirmed"] is True


def test_update_unknown_project_404(client, create_user, monkeypatch):
    create_user("editor-bp5", "pass123", UserRole.editor)

    def _update(db, entry_id, payload):
        raise ProjectNotFoundError("Project 999 not found")

    monkeypatch.setattr(bauportal_route.bauportal_crud, "update_entry", _update)
    resp = client.patch(
        "/api/v1/import/bauportal/entries/1",
        json={"project_id": 999},
        headers=basic_auth_header("editor-bp5", "pass123"),
    )
    assert resp.status_code == 404


def test_update_missing_entry_404(client, create_user, monkeypatch):
    create_user("editor-bp6", "pass123", UserRole.editor)
    monkeypatch.setattr(
        bauportal_route.bauportal_crud, "update_entry", lambda db, e, p: None
    )
    resp = client.patch(
        "/api/v1/import/bauportal/entries/999",
        json={"project_id": None},
        headers=basic_auth_header("editor-bp6", "pass123"),
    )
    assert resp.status_code == 404


def test_confirm_all(client, create_user, monkeypatch):
    create_user("editor-bp7", "pass123", UserRole.editor)
    monkeypatch.setattr(bauportal_route.bauportal_crud, "confirm_all", lambda db: 14)
    resp = client.post(
        "/api/v1/import/bauportal/confirm-all",
        headers=basic_auth_header("editor-bp7", "pass123"),
    )
    assert resp.status_code == 200
    assert resp.json() == {"confirmed": 14}
