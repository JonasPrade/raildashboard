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
