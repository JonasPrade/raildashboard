"""Tests for the /api/v1/projects/{id}/progress endpoints.

Following the project convention, the CRUD layer is monkeypatched so these
tests do not need the progress tables in the SQLite schema.
"""

from __future__ import annotations

import types

import dashboard_backend.api.deps as api_deps
import dashboard_backend.api.v1.endpoints.project_progress as progress_route
from dashboard_backend.crud.projects.progress import (
    DerivedObservationDeleteError,
    DerivedObservationUpdateError,
)
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def _project_exists(db, pid):
    """Stand-in for api.deps.get_project_by_id — the SQLite test schema has no
    project table, so the fetch-or-404 dependency is patched to succeed."""
    return types.SimpleNamespace(id=pid)


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
    monkeypatch.setattr(api_deps, "get_project_by_id", _project_exists)
    monkeypatch.setattr(progress_route.progress_crud, "get_progress_view", lambda db, pid: _make_view(pid))
    resp = client.get("/api/v1/projects/1/progress")
    assert resp.status_code == 200
    body = resp.json()
    assert body["effective_phase"] == "BAU"
    assert body["is_overridden"] is True


def test_get_progress_hides_usernames_from_anonymous(client, create_user, monkeypatch):
    observation = {
        "id": 1,
        "source_type": "MANUELL",
        "track": "MAIN",
        "asserted_state": "BAU",
        "is_derived": False,
        "username_snapshot": "editor-p",
        "created_at": "2026-10-01T12:00:00",
    }
    monkeypatch.setattr(api_deps, "get_project_by_id", _project_exists)
    monkeypatch.setattr(
        progress_route.progress_crud,
        "get_progress_view",
        lambda db, pid: _make_view(pid, observations=[dict(observation)]),
    )

    anonymous = client.get("/api/v1/projects/1/progress")
    assert anonymous.status_code == 200
    assert anonymous.json()["observations"][0]["username_snapshot"] is None

    create_user("viewer-p", "pass123", UserRole.viewer)
    signed_in = client.get("/api/v1/projects/1/progress", headers=basic_auth_header("viewer-p", "pass123"))
    assert signed_in.json()["observations"][0]["username_snapshot"] == "editor-p"


def test_get_progress_404(client, monkeypatch):
    monkeypatch.setattr(api_deps, "get_project_by_id", lambda db, pid: None)
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
    monkeypatch.setattr(api_deps, "get_project_by_id", _project_exists)
    captured = {}

    def _update(db, pid, payload, user):
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


def test_patch_planfeststellung_details(client, create_user, monkeypatch):
    """The editorial PF detail fields (date, note, Beschluss link) flow through."""
    create_user("editor-pf", "pass123", UserRole.editor)
    monkeypatch.setattr(api_deps, "get_project_by_id", _project_exists)
    captured = {}

    def _update(db, pid, payload, user):
        captured.update(payload)
        return object()  # truthy → not 404

    monkeypatch.setattr(progress_route.progress_crud, "update_progress", _update)
    monkeypatch.setattr(
        progress_route.progress_crud,
        "get_progress_view",
        lambda db, pid: _make_view(
            pid,
            pf_text="PFB liegt vor",
            pf_links=[{"url": "https://example.org/pfb.pdf", "comment": "Beschluss"}],
            pf_date="2026-03-15",
        ),
    )

    resp = client.patch(
        "/api/v1/projects/1/progress",
        json={
            "pf_text": "PFB liegt vor",
            "pf_links": [{"url": "https://example.org/pfb.pdf", "comment": "Beschluss"}],
            "pf_date": "2026-03-15",
        },
        headers=basic_auth_header("editor-pf", "pass123"),
    )
    assert resp.status_code == 200
    assert captured["pf_text"] == "PFB liegt vor"
    assert captured["pf_links"] == [{"url": "https://example.org/pfb.pdf", "comment": "Beschluss"}]
    assert str(captured["pf_date"]) == "2026-03-15"
    body = resp.json()
    assert body["pf_text"] == "PFB liegt vor"
    assert body["pf_links"] == [{"url": "https://example.org/pfb.pdf", "comment": "Beschluss"}]
    assert body["pf_date"] == "2026-03-15"


# --- Observations ------------------------------------------------------------


def test_add_observation(client, create_user, monkeypatch):
    create_user("editor2", "pass123", UserRole.editor)
    monkeypatch.setattr(api_deps, "get_project_by_id", _project_exists)
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
    monkeypatch.setattr(api_deps, "get_project_by_id", _project_exists)

    def _delete(db, pid, oid, user):
        raise DerivedObservationDeleteError("derived")

    monkeypatch.setattr(progress_route.progress_crud, "delete_observation", _delete)
    resp = client.delete(
        "/api/v1/projects/1/progress/observations/5",
        headers=basic_auth_header("editor3", "pass123"),
    )
    assert resp.status_code == 409


def test_delete_manual_observation_ok(client, create_user, monkeypatch):
    create_user("editor4", "pass123", UserRole.editor)
    monkeypatch.setattr(api_deps, "get_project_by_id", _project_exists)
    monkeypatch.setattr(progress_route.progress_crud, "delete_observation", lambda db, pid, oid, user: True)
    monkeypatch.setattr(progress_route.progress_crud, "get_progress_view", lambda db, pid: _make_view(pid))
    resp = client.delete(
        "/api/v1/projects/1/progress/observations/5",
        headers=basic_auth_header("editor4", "pass123"),
    )
    assert resp.status_code == 200


def test_patch_observation_passes_only_given_fields(client, create_user, monkeypatch):
    create_user("editor6", "pass123", UserRole.editor)
    monkeypatch.setattr(api_deps, "get_project_by_id", _project_exists)
    seen = {}

    def _update(db, pid, oid, data, user):
        seen.update(data)
        return object()

    monkeypatch.setattr(progress_route.progress_crud, "update_observation", _update)
    monkeypatch.setattr(progress_route.progress_crud, "get_progress_view", lambda db, pid: _make_view(pid))
    resp = client.patch(
        "/api/v1/projects/1/progress/observations/5",
        json={"date_precision": "NOT_BEFORE", "date_label": "Priorisierung 2027 offen"},
        headers=basic_auth_header("editor6", "pass123"),
    )
    assert resp.status_code == 200
    assert seen == {
        "date_precision": "NOT_BEFORE",
        "date_label": "Priorisierung 2027 offen",
        "clear_date_label": False,
    }


def test_patch_derived_observation_rejected(client, create_user, monkeypatch):
    create_user("editor7", "pass123", UserRole.editor)
    monkeypatch.setattr(api_deps, "get_project_by_id", _project_exists)

    def _update(db, pid, oid, data, user):
        raise DerivedObservationUpdateError("derived")

    monkeypatch.setattr(progress_route.progress_crud, "update_observation", _update)
    resp = client.patch(
        "/api/v1/projects/1/progress/observations/5",
        json={"date_precision": "YEAR"},
        headers=basic_auth_header("editor7", "pass123"),
    )
    assert resp.status_code == 409


def test_patch_observation_rejects_unknown_precision(client, create_user, monkeypatch):
    create_user("editor8", "pass123", UserRole.editor)
    monkeypatch.setattr(api_deps, "get_project_by_id", _project_exists)
    resp = client.patch(
        "/api/v1/projects/1/progress/observations/5",
        json={"date_precision": "QUARTER"},
        headers=basic_auth_header("editor8", "pass123"),
    )
    assert resp.status_code == 422


# --- Track documents ---------------------------------------------------------


def test_link_document_rejects_main_track(client, create_user, monkeypatch):
    create_user("editor5", "pass123", UserRole.editor)
    monkeypatch.setattr(api_deps, "get_project_by_id", _project_exists)
    resp = client.post(
        "/api/v1/projects/1/progress/tracks/MAIN/documents",
        json={"document_id": 7},
        headers=basic_auth_header("editor5", "pass123"),
    )
    assert resp.status_code == 400


def test_link_document_pf(client, create_user, monkeypatch):
    create_user("editor6", "pass123", UserRole.editor)
    monkeypatch.setattr(api_deps, "get_project_by_id", _project_exists)
    monkeypatch.setattr(
        progress_route.progress_crud, "link_track_document", lambda db, pid, track, did, user: object()
    )
    monkeypatch.setattr(progress_route.progress_crud, "get_progress_view", lambda db, pid: _make_view(pid))
    resp = client.post(
        "/api/v1/projects/1/progress/tracks/PF/documents",
        json={"document_id": 7},
        headers=basic_auth_header("editor6", "pass123"),
    )
    assert resp.status_code == 201


# --- Admin conflict list -----------------------------------------------------


def test_progress_conflicts_requires_permission(client, create_user):
    assert client.get("/api/v1/admin/progress-conflicts").status_code == 401
    create_user("viewer9", "pass123", UserRole.viewer)
    resp = client.get(
        "/api/v1/admin/progress-conflicts", headers=basic_auth_header("viewer9", "pass123")
    )
    assert resp.status_code == 403


def test_progress_conflicts_lists_rows(client, create_user, monkeypatch):
    import dashboard_backend.api.v1.endpoints.admin_assignments as admin_route

    create_user("editor9", "pass123", UserRole.editor)
    row = {
        "project_id": 7,
        "project_name": "ABS X",
        "project_number": None,
        "computed_phase": "BAU",
        "conflict": {
            "observation_id": 2,
            "source_type": "VIB",
            "asserted_phase": "VORPLANUNG",
            "observed_date": "2025-12-31",
            "trust": 0.6,
            "contradicted_ids": [1],
            "contradicted_phase": "BAU",
            "applied": False,
        },
        "contradicted": [],
    }
    monkeypatch.setattr(admin_route, "list_progress_conflicts", lambda db: [row])
    resp = client.get(
        "/api/v1/admin/progress-conflicts", headers=basic_auth_header("editor9", "pass123")
    )
    assert resp.status_code == 200
    assert resp.json()[0]["conflict"]["applied"] is False
