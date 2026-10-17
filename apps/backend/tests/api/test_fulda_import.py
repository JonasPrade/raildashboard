"""Tests for the /api/v1/import/fulda endpoints (CRUD monkeypatched)."""

from __future__ import annotations

import dashboard_backend.api.v1.endpoints.fulda_import as fulda_route
from dashboard_backend.crud._importer_common import ProjectNotFoundError
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def _entry(entry_id: int = 1, **overrides) -> dict:
    entry = {
        "id": entry_id,
        "announcement_year": 2026,
        "document_id": 1,
        "drucksache": "21/5855",
        "document_date": None,
        "raw_name": "Ausbau Hanau–Würzburg",
        "abschnitt": "Gesamtstrecke",
        "category": "IN_LPH_3_4",
        "statement_kind": "IST",
        "phase": "GENEHMIGUNGSPLANUNG",
        "expected_date": None,
        "project_ids": [],
        "project_names": [],
        "confirmed": False,
        "created_at": None,
        "username_snapshot": "editor1",
    }
    entry.update(overrides)
    return entry



# --- auth --------------------------------------------------------------------


def test_entries_requires_auth(client):
    assert client.get("/api/v1/import/fulda/entries").status_code == 401


def test_viewer_is_forbidden(client, create_user):
    create_user("viewer-f1", "pass123", UserRole.viewer)
    resp = client.get(
        "/api/v1/import/fulda/entries",
        headers=basic_auth_header("viewer-f1", "pass123"),
    )
    assert resp.status_code == 403


def test_parse_route_is_gone(client, create_user):
    create_user("editor-f0", "pass123", UserRole.editor)
    resp = client.post(
        "/api/v1/import/fulda/parse",
        headers=basic_auth_header("editor-f0", "pass123"),
    )
    assert resp.status_code in (404, 405)


def test_categories(client, create_user):
    create_user("editor-fc", "pass123", UserRole.editor)
    resp = client.get(
        "/api/v1/import/fulda/categories",
        headers=basic_auth_header("editor-fc", "pass123"),
    )
    assert resp.status_code == 200
    by_key = {c["key"]: c for c in resp.json()}
    assert by_key["COMPLETES_LPH_3_4"] == {
        "key": "COMPLETES_LPH_3_4",
        "label": "Lph 3/4 wird abgeschlossen",
        "statement_kind": "PROGNOSE",
        "phase": "BAU",
    }
    assert by_key["COMPLETES_LPH_1"]["phase"] is None


# --- list / update / delete --------------------------------------------------


def test_list_entries(client, create_user, monkeypatch):
    create_user("editor-f3", "pass123", UserRole.editor)
    monkeypatch.setattr(
        fulda_route.fulda_crud,
        "list_entries",
        lambda db, only_unconfirmed=False, year=None, document_id=None: [_entry(1), _entry(2)],
    )
    resp = client.get(
        "/api/v1/import/fulda/entries",
        headers=basic_auth_header("editor-f3", "pass123"),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_years(client, create_user, monkeypatch):
    create_user("editor-fy", "pass123", UserRole.editor)
    monkeypatch.setattr(fulda_route.fulda_crud, "list_years", lambda db: [2026, 2025])
    resp = client.get(
        "/api/v1/import/fulda/years",
        headers=basic_auth_header("editor-fy", "pass123"),
    )
    assert resp.status_code == 200
    assert resp.json() == [2026, 2025]


def test_list_year_summaries(client, create_user, monkeypatch):
    create_user("editor-fys", "pass123", UserRole.editor)
    monkeypatch.setattr(
        fulda_route.fulda_crud,
        "list_year_summaries",
        lambda db: [
            {
                "announcement_year": 2026,
                "total": 40,
                "confirmed": 12,
                "documents": [],
            }
        ],
    )
    resp = client.get(
        "/api/v1/import/fulda/year-summaries",
        headers=basic_auth_header("editor-fys", "pass123"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["announcement_year"] == 2026
    assert body[0]["total"] == 40
    assert body[0]["confirmed"] == 12


def test_update_confirm(client, create_user, monkeypatch):
    create_user("editor-f4", "pass123", UserRole.editor)
    captured = {}

    def _update(db, entry_id, payload):
        captured["payload"] = payload
        return _entry(
            entry_id,
            project_ids=[5, 7],
            confirmed=True,
            project_names=["Hanau–Würzburg", "Würzburg–Nürnberg"],
        )

    monkeypatch.setattr(fulda_route.fulda_crud, "update_entry", _update)
    resp = client.patch(
        "/api/v1/import/fulda/entries/1",
        json={"project_ids": [5, 7], "confirmed": True},
        headers=basic_auth_header("editor-f4", "pass123"),
    )
    assert resp.status_code == 200
    assert captured["payload"] == {"project_ids": [5, 7], "confirmed": True}
    assert resp.json()["confirmed"] is True
    assert resp.json()["project_ids"] == [5, 7]


def test_update_unknown_project_404(client, create_user, monkeypatch):
    create_user("editor-f5", "pass123", UserRole.editor)

    def _update(db, entry_id, payload):
        raise ProjectNotFoundError("Project(s) not found: [999]")

    monkeypatch.setattr(fulda_route.fulda_crud, "update_entry", _update)
    resp = client.patch(
        "/api/v1/import/fulda/entries/1",
        json={"project_ids": [999]},
        headers=basic_auth_header("editor-f5", "pass123"),
    )
    assert resp.status_code == 404


def test_delete_entry(client, create_user, monkeypatch):
    create_user("editor-f6", "pass123", UserRole.editor)
    monkeypatch.setattr(fulda_route.fulda_crud, "delete_entry", lambda db, e: True)
    resp = client.delete(
        "/api/v1/import/fulda/entries/1",
        headers=basic_auth_header("editor-f6", "pass123"),
    )
    assert resp.status_code == 204


def test_delete_missing_404(client, create_user, monkeypatch):
    create_user("editor-f7", "pass123", UserRole.editor)
    monkeypatch.setattr(fulda_route.fulda_crud, "delete_entry", lambda db, e: False)
    resp = client.delete(
        "/api/v1/import/fulda/entries/999",
        headers=basic_auth_header("editor-f7", "pass123"),
    )
    assert resp.status_code == 404


def test_confirm_year(client, create_user, monkeypatch):
    create_user("editor-fc", "pass123", UserRole.editor)
    captured = {}

    def _confirm_year(db, year):
        captured["year"] = year
        return 9

    monkeypatch.setattr(fulda_route.fulda_crud, "confirm_year", _confirm_year)
    resp = client.post(
        "/api/v1/import/fulda/years/2026/confirm",
        headers=basic_auth_header("editor-fc", "pass123"),
    )
    assert resp.status_code == 200
    assert resp.json() == {"confirmed": 9}
    assert captured["year"] == 2026


def test_delete_year(client, create_user, monkeypatch):
    create_user("editor-f8", "pass123", UserRole.editor)
    captured = {}

    def _delete_year(db, year):
        captured["year"] = year
        return 12

    monkeypatch.setattr(fulda_route.fulda_crud, "delete_year", _delete_year)
    resp = client.delete(
        "/api/v1/import/fulda/years/2026",
        headers=basic_auth_header("editor-f8", "pass123"),
    )
    assert resp.status_code == 204
    assert captured["year"] == 2026


def test_delete_year_missing_404(client, create_user, monkeypatch):
    create_user("editor-f9", "pass123", UserRole.editor)
    monkeypatch.setattr(fulda_route.fulda_crud, "delete_year", lambda db, year: 0)
    resp = client.delete(
        "/api/v1/import/fulda/years/1999",
        headers=basic_auth_header("editor-f9", "pass123"),
    )
    assert resp.status_code == 404
