"""Tests for /api/v1/admin/unassigned-* endpoints."""
from __future__ import annotations

import base64

import dashboard_backend.api.v1.endpoints.admin_assignments as admin_route
from dashboard_backend.schemas.admin_assignments import (
    UnassignedFinveSchema,
    UnassignedVibEntrySchema,
)
from dashboard_backend.schemas.users import UserRole


MOCK_FINVES = [
    UnassignedFinveSchema(id=1, name="ABS Test", is_sammel_finve=False, starting_year=2020),
    UnassignedFinveSchema(id=2, name="SV Sammel", is_sammel_finve=True, starting_year=2022),
]

MOCK_VIB_ENTRIES = [
    UnassignedVibEntrySchema(
        id=10,
        vib_name_raw="Ausbau Strecke X",
        vib_section="B.4.1",
        category="laufend",
        report_year=2024,
    ),
]


def _auth(username: str, password: str) -> dict[str, str]:
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def test_get_unassigned_finves_requires_auth(client):
    resp = client.get("/api/v1/admin/unassigned-finves")
    assert resp.status_code == 401


def test_get_unassigned_finves_returns_list(client, monkeypatch, create_user):
    create_user("editor_fa1", "pass", UserRole.editor)
    monkeypatch.setattr(admin_route, "list_unassigned_finves", lambda db: MOCK_FINVES)

    resp = client.get("/api/v1/admin/unassigned-finves", headers=_auth("editor_fa1", "pass"))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["id"] == 1
    assert body[1]["is_sammel_finve"] is True


def test_get_unassigned_finves_empty(client, monkeypatch, create_user):
    create_user("editor_fa2", "pass", UserRole.editor)
    monkeypatch.setattr(admin_route, "list_unassigned_finves", lambda db: [])

    resp = client.get("/api/v1/admin/unassigned-finves", headers=_auth("editor_fa2", "pass"))
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_unassigned_vib_entries_requires_auth(client):
    resp = client.get("/api/v1/admin/unassigned-vib-entries")
    assert resp.status_code == 401


def test_get_unassigned_vib_entries_returns_list(client, monkeypatch, create_user):
    create_user("editor_fa3", "pass", UserRole.editor)
    monkeypatch.setattr(admin_route, "list_unassigned_vib_entries", lambda db: MOCK_VIB_ENTRIES)

    resp = client.get("/api/v1/admin/unassigned-vib-entries", headers=_auth("editor_fa3", "pass"))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["report_year"] == 2024
    assert body[0]["vib_section"] == "B.4.1"


def test_get_unassigned_vib_entries_empty(client, monkeypatch, create_user):
    create_user("editor_fa4", "pass", UserRole.editor)
    monkeypatch.setattr(admin_route, "list_unassigned_vib_entries", lambda db: [])

    resp = client.get("/api/v1/admin/unassigned-vib-entries", headers=_auth("editor_fa4", "pass"))
    assert resp.status_code == 200
    assert resp.json() == []


def test_assign_finve_requires_auth(client):
    resp = client.patch(
        "/api/v1/admin/unassigned-finves/1/assign",
        json={"project_ids": [5]},
    )
    assert resp.status_code == 401


def test_assign_finve_not_found(client, monkeypatch, create_user):
    create_user("editor_fa5", "pass", UserRole.editor)
    monkeypatch.setattr(admin_route, "get_finve", lambda db, finve_id: None)

    resp = client.patch(
        "/api/v1/admin/unassigned-finves/9999/assign",
        json={"project_ids": [5]},
        headers=_auth("editor_fa5", "pass"),
    )
    assert resp.status_code == 404


def test_assign_vib_entry_requires_auth(client):
    resp = client.patch(
        "/api/v1/admin/unassigned-vib-entries/1/assign",
        json={"project_ids": [5]},
    )
    assert resp.status_code == 401


def test_assign_vib_entry_not_found(client, monkeypatch, create_user):
    create_user("editor_fa6", "pass", UserRole.editor)
    monkeypatch.setattr(admin_route, "get_vib_entry", lambda db, entry_id: None)

    resp = client.patch(
        "/api/v1/admin/unassigned-vib-entries/9999/assign",
        json={"project_ids": [5]},
        headers=_auth("editor_fa6", "pass"),
    )
    assert resp.status_code == 404
