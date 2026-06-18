"""Tests for the /api/v1/projects/{id}/progress endpoints.

Following the project convention, the CRUD layer is monkeypatched so these
tests do not need the progress tables in the SQLite schema.
"""

from __future__ import annotations

import dashboard_backend.api.v1.endpoints.project_progress as progress_route
from dashboard_backend.crud.projects.progress import DerivedObservationDeleteError
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def _make_view(project_id: int = 1, **overrides) -> dict:
    view = {
        "project_id": project_id,
        "effective_phase": "BAU",
        "computed_phase": "VORPLANUNG",
        "computed_confidence": 0.82,
        "is_overridden": True,
        "manual_override_note": "Baustart laut Pressemitteilung",
        "computed_at": None,
        "has_planfeststellung": True,
        "parl_befassung_relevant": True,
        "parl_befassung_relevant_override": None,
        "lifecycle_status": "AKTIV",
        "pf_state": "LAEUFT",
        "parl_state": "OFFEN",
        "observations": [],
        "contributions": [],
        "pf_documents": [],
        "parl_documents": [],
        "is_superior": False,
        "span_min_phase": None,
        "span_max_phase": None,
        "children": [],
    }
    view.update(overrides)
    return view


# --- GET (public) ------------------------------------------------------------


def test_get_progress_is_public(client, monkeypatch):
    monkeypatch.setattr(progress_route.progress_crud, "get_progress_view", lambda db, pid: _make_view(pid))
    resp = client.get("/api/v1/projects/1/progress")
    assert resp.status_code == 200
    body = resp.json()
    assert body["effective_phase"] == "BAU"
    assert body["is_overridden"] is True


def test_get_progress_404(client, monkeypatch):
    monkeypatch.setattr(progress_route.progress_crud, "get_progress_view", lambda db, pid: None)
    resp = client.get("/api/v1/projects/999/progress")
    assert resp.status_code == 404


# --- PATCH (gated) -----------------------------------------------------------


def test_patch_requires_auth(client):
    resp = client.patch("/api/v1/projects/1/progress", json={"lifecycle_status": "PAUSIERT"})
    assert resp.status_code == 401


def test_patch_forbidden_for_viewer(client, create_user, monkeypatch):
    create_user("viewer1", "pass123", UserRole.viewer)
    resp = client.patch(
        "/api/v1/projects/1/progress",
        json={"lifecycle_status": "PAUSIERT"},
        headers=basic_auth_header("viewer1", "pass123"),
    )
    assert resp.status_code == 403


def test_patch_override_wins(client, create_user, monkeypatch):
    create_user("editor1", "pass123", UserRole.editor)
    captured = {}

    def _update(db, pid, payload):
        captured.update(payload)
        return object()  # truthy → not 404

    monkeypatch.setattr(progress_route.progress_crud, "update_progress", _update)
    monkeypatch.setattr(
        progress_route.progress_crud,
        "get_progress_view",
        lambda db, pid: _make_view(pid, manual_phase_override="VORPLANUNG", effective_phase="VORPLANUNG"),
    )

    resp = client.patch(
        "/api/v1/projects/1/progress",
        json={"manual_phase_override": "VORPLANUNG"},
        headers=basic_auth_header("editor1", "pass123"),
    )
    assert resp.status_code == 200
    assert captured["manual_phase_override"] == "VORPLANUNG"
    assert resp.json()["effective_phase"] == "VORPLANUNG"


# --- Observations ------------------------------------------------------------


def test_add_observation(client, create_user, monkeypatch):
    create_user("editor2", "pass123", UserRole.editor)
    monkeypatch.setattr(
        progress_route.progress_crud, "create_observation", lambda db, pid, data, user: object()
    )
    monkeypatch.setattr(progress_route.progress_crud, "get_progress_view", lambda db, pid: _make_view(pid))
    resp = client.post(
        "/api/v1/projects/1/progress/observations",
        json={"track": "MAIN", "asserted_state": "BAU"},
        headers=basic_auth_header("editor2", "pass123"),
    )
    assert resp.status_code == 201


def test_delete_derived_observation_rejected(client, create_user, monkeypatch):
    create_user("editor3", "pass123", UserRole.editor)

    def _delete(db, pid, oid):
        raise DerivedObservationDeleteError("derived")

    monkeypatch.setattr(progress_route.progress_crud, "delete_observation", _delete)
    resp = client.delete(
        "/api/v1/projects/1/progress/observations/5",
        headers=basic_auth_header("editor3", "pass123"),
    )
    assert resp.status_code == 409


def test_delete_manual_observation_ok(client, create_user, monkeypatch):
    create_user("editor4", "pass123", UserRole.editor)
    monkeypatch.setattr(progress_route.progress_crud, "delete_observation", lambda db, pid, oid: True)
    monkeypatch.setattr(progress_route.progress_crud, "get_progress_view", lambda db, pid: _make_view(pid))
    resp = client.delete(
        "/api/v1/projects/1/progress/observations/5",
        headers=basic_auth_header("editor4", "pass123"),
    )
    assert resp.status_code == 200


# --- Track documents ---------------------------------------------------------


def test_link_document_rejects_main_track(client, create_user, monkeypatch):
    create_user("editor5", "pass123", UserRole.editor)
    resp = client.post(
        "/api/v1/projects/1/progress/tracks/MAIN/documents",
        json={"document_id": 7},
        headers=basic_auth_header("editor5", "pass123"),
    )
    assert resp.status_code == 400


def test_link_document_pf(client, create_user, monkeypatch):
    create_user("editor6", "pass123", UserRole.editor)
    monkeypatch.setattr(
        progress_route.progress_crud, "link_track_document", lambda db, pid, track, did: object()
    )
    monkeypatch.setattr(progress_route.progress_crud, "get_progress_view", lambda db, pid: _make_view(pid))
    resp = client.post(
        "/api/v1/projects/1/progress/tracks/PF/documents",
        json={"document_id": 7},
        headers=basic_auth_header("editor6", "pass123"),
    )
    assert resp.status_code == 201
