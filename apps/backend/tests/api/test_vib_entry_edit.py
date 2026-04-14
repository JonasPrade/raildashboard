"""Tests for PATCH /api/v1/import/vib/entries/{entry_id}."""
from __future__ import annotations

import base64
import dashboard_backend.api.v1.endpoints.vib_import as vib_route
from dashboard_backend.schemas.vib import VibEntrySchema, VibPfaEntrySchema
from dashboard_backend.schemas.users import UserRole


def _auth(u: str, p: str) -> dict:
    return {"Authorization": "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()}


_MOCK_ENTRY = VibEntrySchema(
    id=1,
    vib_report_id=10,
    vib_name_raw="ABS Köln – Aachen",
    category="laufend",
    status_planung=False,
    status_bau=True,
    status_abgeschlossen=False,
    ai_extracted=False,
    project_ids=[5],
    report_year=2024,
    pfa_entries=[VibPfaEntrySchema(id=99, nr_pfa="PFA-1")],
)


def test_patch_vib_entry_requires_auth(client):
    resp = client.patch("/api/v1/import/vib/entries/1", json={"vib_name_raw": "X"})
    assert resp.status_code == 401


def test_patch_vib_entry_requires_editor(client, create_user):
    create_user("viewer_ve1", "pass", UserRole.viewer)
    resp = client.patch(
        "/api/v1/import/vib/entries/1",
        json={"vib_name_raw": "X"},
        headers=_auth("viewer_ve1", "pass"),
    )
    assert resp.status_code == 403


def test_patch_vib_entry_not_found(client, monkeypatch, create_user):
    create_user("editor_ve1", "pass", UserRole.editor)
    monkeypatch.setattr(vib_route, "update_vib_entry", lambda db, eid, data: None)
    resp = client.patch(
        "/api/v1/import/vib/entries/999",
        json={"vib_name_raw": "X"},
        headers=_auth("editor_ve1", "pass"),
    )
    assert resp.status_code == 404


def test_patch_vib_entry_updates_fields(client, monkeypatch, create_user):
    create_user("editor_ve2", "pass", UserRole.editor)

    captured = {}

    def fake_update(db, entry_id, data):
        captured["entry_id"] = entry_id
        captured["data"] = data
        return _MOCK_ENTRY

    monkeypatch.setattr(vib_route, "update_vib_entry", fake_update)
    monkeypatch.setattr(vib_route, "_entry_to_schema", lambda e: _MOCK_ENTRY)

    resp = client.patch(
        "/api/v1/import/vib/entries/1",
        json={"vib_name_raw": "Updated Name", "status_bau": True},
        headers=_auth("editor_ve2", "pass"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 1
    assert body["project_ids"] == [5]
    assert body["report_year"] == 2024
    assert captured["entry_id"] == 1
