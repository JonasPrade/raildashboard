"""Editable FinVe ↔ project links (docs/features/feature-finve-zuordnung.md):
add/remove via REST and MCP, changelog entry ``finve_ids`` with revert, planning
state recomputed, Sammel-FinVe year links untouched, Haushalt confirm delta."""

from __future__ import annotations

import json

from dashboard_backend.api.v1.endpoints.haushalt_import import permanent_link_delta
from dashboard_backend.crud.projects.progress import recompute_progress
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _payload,
    admin_token,
    mcp_client,
)


def _seed(db):
    stuttgart = Project(name="Stuttgart 21", is_draft=False)
    gaeubahn = Project(name="Gäubahn Abschnitt Nord", is_draft=False)
    other = Project(name="NBS Stuttgart – Ulm", is_draft=False)
    digital = Finve(id=900008, name="Digitaler Knoten Stuttgart", starting_year=2020)
    sammel = Finve(id=4001, name="SV Planung LPH 1-2", is_sammel_finve=True)
    db.add_all([stuttgart, gaeubahn, other, digital, sammel])
    db.flush()
    db.add_all(
        [
            FinveToProject(project_id=stuttgart.id, finve_id=digital.id),
            FinveToProject(project_id=gaeubahn.id, finve_id=digital.id),
            FinveToProject(project_id=gaeubahn.id, finve_id=sammel.id, haushalt_year=2025),
        ]
    )
    db.commit()
    return stuttgart, gaeubahn, other


def _links(db, finve_id, year=None):
    q = db.query(FinveToProject.project_id).filter(FinveToProject.finve_id == finve_id)
    q = q.filter(FinveToProject.haushalt_year.is_(None) if year is None else FinveToProject.haushalt_year == year)
    return sorted(r[0] for r in q)


def _finve_observations(db, project_id, finve_id):
    return (
        db.query(ProgressObservation)
        .filter(ProgressObservation.project_id == project_id, ProgressObservation.finve_id == finve_id)
        .count()
    )


def _patch(client, finve_id, body, user="editor_fl"):
    return client.patch(
        f"/api/v1/finves/{finve_id}/projects", json=body, headers=basic_auth_header(user, "pass")
    )


def test_remove_and_add_project_logs_and_recomputes(client, db_session, create_user):
    create_user("editor_fl", "pass", UserRole.editor)
    stuttgart, gaeubahn, other = _seed(db_session)
    # Materialise the FinVe observation first, as the running system has it.
    recompute_progress(db_session, gaeubahn.id)
    assert _finve_observations(db_session, gaeubahn.id, 900008) == 1

    resp = _patch(client, 900008, {"remove_project_ids": [gaeubahn.id], "add_project_ids": [other.id]})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [p["id"] for p in body["projects"]] == sorted([stuttgart.id, other.id])
    assert sorted(body["changed_project_ids"]) == sorted([gaeubahn.id, other.id])

    db_session.expire_all()
    assert _links(db_session, 900008) == sorted([stuttgart.id, other.id])
    # The Sammel-FinVe year link of the same project is untouched.
    assert _links(db_session, 4001, 2025) == [gaeubahn.id]
    assert _finve_observations(db_session, gaeubahn.id, 900008) == 0
    assert _finve_observations(db_session, other.id, 900008) == 1

    log = db_session.query(ChangeLog).filter(ChangeLog.project_id == gaeubahn.id).one()
    entry = log.entries[0]
    assert entry.field_name == "finve_ids"
    assert json.loads(entry.old_value) == [900008]
    assert json.loads(entry.new_value) == []


def test_revert_restores_link(client, db_session, create_user):
    create_user("editor_fl", "pass", UserRole.editor)
    _, gaeubahn, _ = _seed(db_session)
    assert _patch(client, 900008, {"remove_project_ids": [gaeubahn.id]}).status_code == 200

    entry_id = (
        db_session.query(ChangeLog).filter(ChangeLog.project_id == gaeubahn.id).one().entries[0].id
    )
    resp = client.post(
        f"/api/v1/projects/{gaeubahn.id}/changelog/revert",
        json={"changelog_entry_id": entry_id},
        headers=basic_auth_header("editor_fl", "pass"),
    )
    assert resp.status_code == 200, resp.text
    db_session.expire_all()
    assert gaeubahn.id in _links(db_session, 900008)
    actions = [c.action for c in db_session.query(ChangeLog).filter(ChangeLog.project_id == gaeubahn.id)]
    assert sorted(actions) == ["PATCH", "REVERT"]


def test_noop_change_writes_no_changelog(client, db_session, create_user):
    create_user("editor_fl", "pass", UserRole.editor)
    stuttgart, _, other = _seed(db_session)
    resp = _patch(client, 900008, {"add_project_ids": [stuttgart.id], "remove_project_ids": [other.id]})
    assert resp.status_code == 200
    assert resp.json()["changed_project_ids"] == []
    assert db_session.query(ChangeLog).count() == 0


def test_unknown_project_or_finve_is_404(client, db_session, create_user):
    create_user("editor_fl", "pass", UserRole.editor)
    _seed(db_session)
    assert _patch(client, 900008, {"add_project_ids": [99999]}).status_code == 404
    assert _patch(client, 123, {"add_project_ids": [1]}).status_code == 404


def test_requires_finve_edit(client, db_session, create_user):
    create_user("viewer_fl", "pass", UserRole.viewer)
    _, gaeubahn, _ = _seed(db_session)
    assert _patch(client, 900008, {"remove_project_ids": [gaeubahn.id]}, user="viewer_fl").status_code == 403
    assert client.patch("/api/v1/finves/900008/projects", json={}).status_code == 401


def test_finve_list_marks_permanent_links(client, db_session):
    stuttgart, gaeubahn, _ = _seed(db_session)
    body = {f["id"]: f for f in client.get("/api/v1/finves/").json()}
    assert body[900008]["permanent_project_ids"] == sorted([stuttgart.id, gaeubahn.id])
    assert body[4001]["permanent_project_ids"] == []
    assert [p["id"] for p in body[4001]["projects"]] == [gaeubahn.id]


def test_project_finves_flag_permanent_links(client, db_session):
    _, gaeubahn, _ = _seed(db_session)
    body = {f["id"]: f for f in client.get(f"/api/v1/projects/{gaeubahn.id}/finves").json()}
    assert body[900008]["linked_permanently"] is True
    assert body[4001]["linked_permanently"] is False


def test_mcp_update_finve_projects(mcp_client, admin_token, db_session):
    stuttgart, gaeubahn, _ = _seed(db_session)
    payload = _payload(
        _call(
            mcp_client,
            admin_token,
            "update_finve_projects",
            {"finve_id": 900008, "remove_project_ids": [gaeubahn.id], "note": "digitale FinVe"},
        )
    )
    assert payload["projects"] == [{"id": stuttgart.id, "name": "Stuttgart 21"}]
    assert payload["changed_project_ids"] == [gaeubahn.id]
    assert payload["note"] == "digitale FinVe"
    db_session.expire_all()
    assert _links(db_session, 900008) == [stuttgart.id]


def test_mcp_update_finve_projects_needs_projects(mcp_client, admin_token, db_session):
    _seed(db_session)
    result = _call(mcp_client, admin_token, "update_finve_projects", {"finve_id": 900008})
    assert result["isError"] is True
    assert "Keine Projekte" in result["content"][0]["text"]


# --- Haushalt confirm: only the reviewer's delta (decision W1) ---------------


def test_delta_keeps_links_edited_after_parse():
    parsed = {"project_ids": [1, 2], "suggested_project_ids": []}
    # Reviewer left the list as parsed → nothing to apply, even if 2 was removed meanwhile.
    assert permanent_link_delta(parsed, [1, 2]) == (set(), set())
    # Reviewer removed 2 and added 3.
    assert permanent_link_delta(parsed, [1, 3]) == ({3}, {2})


def test_delta_new_finve_takes_suggestions():
    parsed = {"project_ids": [5], "suggested_project_ids": [5]}
    assert permanent_link_delta(parsed, [5]) == ({5}, set())


def test_delta_without_parsed_row_only_adds():
    assert permanent_link_delta(None, [7]) == ({7}, set())


def test_archived_project_gets_no_finve(client, db_session, create_user):
    create_user("editor_fl", "pass", UserRole.editor)
    _, _, other = _seed(db_session)
    other.is_archived = True
    other.archived_reason = "ersetzt"
    db_session.commit()
    resp = _patch(client, 900008, {"add_project_ids": [other.id]})
    assert resp.status_code == 409
    assert "archiviert" in resp.json()["detail"]
