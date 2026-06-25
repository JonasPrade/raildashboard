"""Tests for the /api/v1/finves/ endpoint."""
from __future__ import annotations

import dashboard_backend.api.v1.endpoints.finves as finves_route
from dashboard_backend.schemas.projects.project_schema import FinveListItemSchema


MOCK_FINVES = [
    FinveListItemSchema(
        id=1,
        name="ABS Musterstadt–Beispielstadt",
        starting_year=2020,
        cost_estimate_original=50000,
        is_sammel_finve=False,
        temporary_finve_number=False,
        project_count=1,
        project_names=["Musterstadt–Beispielstadt"],
    ),
    FinveListItemSchema(
        id=2,
        name="SV Sammelfinve",
        starting_year=2022,
        cost_estimate_original=None,
        is_sammel_finve=True,
        temporary_finve_number=False,
        project_count=3,
        project_names=["Projekt A", "Projekt B", "Projekt C"],
    ),
]


def test_list_finves_returns_all(client, monkeypatch):
    monkeypatch.setattr(finves_route, "list_finves", lambda db: MOCK_FINVES)

    resp = client.get("/api/v1/finves/")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 2
    assert {item["id"] for item in body} == {1, 2}


def test_list_finves_empty(client, monkeypatch):
    monkeypatch.setattr(finves_route, "list_finves", lambda db: [])

    resp = client.get("/api/v1/finves/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_finves_sammel_flag(client, monkeypatch):
    monkeypatch.setattr(finves_route, "list_finves", lambda db: MOCK_FINVES)

    resp = client.get("/api/v1/finves/")
    body = resp.json()
    sammel = next(item for item in body if item["id"] == 2)
    assert sammel["is_sammel_finve"] is True
    assert sammel["project_count"] == 3


# ---------------------------------------------------------------------------
# Sammel-FinVe progress-phase assignment
# ---------------------------------------------------------------------------

from dashboard_backend.schemas.projects.progress_schema import (  # noqa: E402
    SammelFinveProgressSchema,
)
from dashboard_backend.schemas.users import UserRole  # noqa: E402
from tests.api.conftest import basic_auth_header  # noqa: E402


def _sammel_row(finve_id=763, manual=None, auto="VORPLANUNG"):
    eff = manual or auto
    return SammelFinveProgressSchema(
        finve_id=finve_id,
        name="SV Lph. 1/2 A",
        starting_year=2012,
        progress_phase=manual,
        auto_phase=auto,
        effective_phase=eff,
        needs_assignment=eff is None,
        projects=[],
    )


def test_sammel_progress_is_public(client, monkeypatch):
    monkeypatch.setattr(
        finves_route, "list_sammel_finves_progress", lambda db: [_sammel_row()]
    )
    resp = client.get("/api/v1/finves/sammel-progress")
    assert resp.status_code == 200
    assert resp.json()[0]["effective_phase"] == "VORPLANUNG"


def test_patch_progress_phase_requires_auth(client):
    resp = client.patch("/api/v1/finves/763/progress-phase", json={"progress_phase": "BAU"})
    assert resp.status_code == 401


def test_patch_progress_phase_sets_override(client, create_user, monkeypatch):
    create_user("editor-finve", "pass123", UserRole.editor)
    captured = {}

    def _set(db, finve_id, phase):
        captured["finve_id"] = finve_id
        captured["phase"] = phase
        return object()

    monkeypatch.setattr(finves_route, "set_finve_progress_phase", _set)
    monkeypatch.setattr(
        finves_route,
        "list_sammel_finves_progress",
        lambda db: [_sammel_row(manual="BAU")],
    )
    resp = client.patch(
        "/api/v1/finves/763/progress-phase",
        json={"progress_phase": "BAU"},
        headers=basic_auth_header("editor-finve", "pass123"),
    )
    assert resp.status_code == 200
    assert captured == {"finve_id": 763, "phase": "BAU"}
    assert resp.json()[0]["progress_phase"] == "BAU"


def test_patch_progress_phase_404(client, create_user, monkeypatch):
    create_user("editor-finve2", "pass123", UserRole.editor)
    monkeypatch.setattr(finves_route, "set_finve_progress_phase", lambda db, fid, phase: None)
    resp = client.patch(
        "/api/v1/finves/999/progress-phase",
        json={"progress_phase": "BAU"},
        headers=basic_auth_header("editor-finve2", "pass123"),
    )
    assert resp.status_code == 404
