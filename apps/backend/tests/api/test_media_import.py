"""Tests for the /api/v1/import/media endpoints (CRUD monkeypatched)."""

from __future__ import annotations

import httpx

import dashboard_backend.api.v1.endpoints.media_import as media_route
from dashboard_backend.crud._importer_common import ProjectNotFoundError
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def _entry(entry_id: int = 1, **overrides) -> dict:
    entry = {
        "id": entry_id,
        "url": "https://example.org/a",
        "publication": "FAZ",
        "published_date": None,
        "raw_text": "…",
        "quote": "Bauarbeiten haben begonnen",
        "asserted_phase": "BAU",
        "observed_date": None,
        "suggested_project_id": 5,
        "suggested_project_name": "Hanau–Würzburg",
        "project_id": None,
        "project_name": None,
        "confirmed": False,
        "created_at": None,
        "username_snapshot": "editor1",
    }
    entry.update(overrides)
    return entry


# --- auth --------------------------------------------------------------------


def test_extract_requires_auth(client):
    assert client.post("/api/v1/import/media/extract", json={"text": "x"}).status_code == 401


def test_extract_forbidden_for_viewer(client, create_user):
    create_user("viewer-m", "pass123", UserRole.viewer)
    resp = client.post(
        "/api/v1/import/media/extract",
        json={"text": "x"},
        headers=basic_auth_header("viewer-m", "pass123"),
    )
    assert resp.status_code == 403


# --- extract -----------------------------------------------------------------


def test_extract_creates_draft(client, create_user, monkeypatch):
    create_user("editor-m", "pass123", UserRole.editor)
    captured = {}

    def _create(db, *, url, text, user):
        captured["url"] = url
        captured["text"] = text
        return _entry(1)

    monkeypatch.setattr(media_route.media_crud, "create_from_input", _create)
    resp = client.post(
        "/api/v1/import/media/extract",
        json={"url": "https://example.org/a"},
        headers=basic_auth_header("editor-m", "pass123"),
    )
    assert resp.status_code == 200
    assert captured["url"] == "https://example.org/a"
    assert resp.json()["asserted_phase"] == "BAU"


def test_extract_empty_input_400(client, create_user, monkeypatch):
    create_user("editor-m2", "pass123", UserRole.editor)

    def _create(db, *, url, text, user):
        raise ValueError("Either a URL or article text is required.")

    monkeypatch.setattr(media_route.media_crud, "create_from_input", _create)
    resp = client.post(
        "/api/v1/import/media/extract",
        json={},
        headers=basic_auth_header("editor-m2", "pass123"),
    )
    assert resp.status_code == 400


def test_extract_url_fetch_error_502(client, create_user, monkeypatch):
    create_user("editor-m3", "pass123", UserRole.editor)

    def _create(db, *, url, text, user):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(media_route.media_crud, "create_from_input", _create)
    resp = client.post(
        "/api/v1/import/media/extract",
        json={"url": "https://bad.example"},
        headers=basic_auth_header("editor-m3", "pass123"),
    )
    assert resp.status_code == 502


# --- list / update / delete --------------------------------------------------


def test_list_entries(client, create_user, monkeypatch):
    create_user("editor-m4", "pass123", UserRole.editor)
    monkeypatch.setattr(
        media_route.media_crud,
        "list_entries",
        lambda db, only_unconfirmed=False: [_entry(1), _entry(2, confirmed=True, project_id=9)],
    )
    resp = client.get(
        "/api/v1/import/media/entries",
        headers=basic_auth_header("editor-m4", "pass123"),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_confirm(client, create_user, monkeypatch):
    create_user("editor-m5", "pass123", UserRole.editor)
    captured = {}

    def _update(db, entry_id, payload):
        captured["entry_id"] = entry_id
        captured["payload"] = payload
        return _entry(entry_id, project_id=5, confirmed=True, project_name="Hanau–Würzburg")

    monkeypatch.setattr(media_route.media_crud, "update_entry", _update)
    resp = client.patch(
        "/api/v1/import/media/entries/1",
        json={"project_id": 5, "confirmed": True},
        headers=basic_auth_header("editor-m5", "pass123"),
    )
    assert resp.status_code == 200
    assert captured["payload"] == {"project_id": 5, "confirmed": True}
    assert resp.json()["confirmed"] is True


def test_update_unknown_project_404(client, create_user, monkeypatch):
    create_user("editor-m6", "pass123", UserRole.editor)

    def _update(db, entry_id, payload):
        raise ProjectNotFoundError("Project 999 not found")

    monkeypatch.setattr(media_route.media_crud, "update_entry", _update)
    resp = client.patch(
        "/api/v1/import/media/entries/1",
        json={"project_id": 999},
        headers=basic_auth_header("editor-m6", "pass123"),
    )
    assert resp.status_code == 404


def test_delete_entry(client, create_user, monkeypatch):
    create_user("editor-m7", "pass123", UserRole.editor)
    monkeypatch.setattr(media_route.media_crud, "delete_entry", lambda db, e: True)
    resp = client.delete(
        "/api/v1/import/media/entries/1",
        headers=basic_auth_header("editor-m7", "pass123"),
    )
    assert resp.status_code == 204


def test_delete_missing_404(client, create_user, monkeypatch):
    create_user("editor-m8", "pass123", UserRole.editor)
    monkeypatch.setattr(media_route.media_crud, "delete_entry", lambda db, e: False)
    resp = client.delete(
        "/api/v1/import/media/entries/999",
        headers=basic_auth_header("editor-m8", "pass123"),
    )
    assert resp.status_code == 404
