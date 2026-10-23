"""Project archive (feature-project-archive.md): mandatory reason, refusals
naming the links, the filters everywhere drafts are filtered, the parent
aggregation (geometry, planning-state subtree, sums), the changelog — through
the REST endpoints and the MCP tools.
"""

from __future__ import annotations

import json

import pytest

from dashboard_backend.crud.projects import archive as archive_crud
from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.crud.projects.projects import (
    ProjectHierarchyError,
    get_draft_projects,
    get_project_options,
    get_projects,
    get_subprojects,
    has_subprojects,
    subtree_ids,
    validate_superior_project,
)
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header
from tests.api.test_mcp_server import (  # noqa: F401
    _call,
    _key_for,
    _payload,
    _role_user,
    admin_token,
    mcp_client,
)

LINE_A = {"type": "LineString", "coordinates": [[9.0, 52.0], [9.1, 52.1]]}
LINE_B = {"type": "LineString", "coordinates": [[10.0, 53.0], [10.1, 53.1]]}
REASON = "Ersetzt durch PFA-Abschnitte laut VIB 2024"


@pytest.fixture(autouse=True)
def _progress_calls(monkeypatch):
    """The planning-state recompute reads import tables this test DB lacks —
    record which projects it was asked for instead."""
    calls: list[int] = []
    monkeypatch.setattr(
        archive_crud.progress_crud, "recompute_progress", lambda db, pid: calls.append(pid) or True
    )
    return calls


def _family(db):
    parent = Project(name="ABS/NBS Hamburg–Lübeck–Puttgarden", geojson_from_subprojects=True)
    db.add(parent)
    db.flush()
    old = Project(
        name="Alte Teilmaßnahme",
        superior_project_id=parent.id,
        geojson_representation=json.dumps(LINE_A),
    )
    new = Project(
        name="PFA 1",
        superior_project_id=parent.id,
        geojson_representation=json.dumps(LINE_B),
    )
    db.add_all([old, new])
    db.commit()
    return parent, old, new


def _parent_lines(db, parent):
    db.refresh(parent)
    features = json.loads(parent.geojson_representation)["features"]
    return [f["geometry"]["coordinates"] for f in features]


# --- CRUD --------------------------------------------------------------------


def test_archive_drops_child_from_every_aggregation(db_session, _progress_calls):
    parent, old, new = _family(db_session)

    result = archive_crud.archive_project(db_session, old.id, REASON, None, "admin")

    assert result["project"].is_archived is True
    assert result["project"].archived_reason == REASON
    assert result["project"].archived_at is not None
    # Geometry: only the remaining child, recomputed on archiving.
    assert _parent_lines(db_session, parent) == [LINE_B["coordinates"]]
    assert _progress_calls == [parent.id]
    # Lists, pickers, subprojects, sums, planning-state subtree.
    assert old.id not in {p.id for p in get_projects(db_session)}
    assert old.id not in {row.id for row in get_project_options(db_session)}
    assert [p.id for p in get_subprojects(db_session, parent.id)] == [new.id]
    assert subtree_ids(db_session, parent.id) == [parent.id, new.id]
    children = progress_crud._load_subtree(db_session, parent.id)
    assert [c.id for c in children[parent.id]] == [new.id]


def test_parent_with_only_archived_children_is_no_superior(db_session):
    parent, old, new = _family(db_session)
    archive_crud.archive_project(db_session, new.id, REASON, None, None)
    archive_crud.archive_project(db_session, old.id, REASON, None, None)

    assert has_subprojects(db_session, parent.id) is False
    assert progress_crud._load_subtree(db_session, parent.id) == {}
    db_session.refresh(parent)
    assert parent.geojson_representation is None


def test_unarchive_restores_aggregation(db_session, _progress_calls):
    parent, old, _ = _family(db_session)
    archive_crud.archive_project(db_session, old.id, REASON, None, None)

    restored = archive_crud.unarchive_project(db_session, old.id, "doch noch gültig", None, None)

    assert restored.is_archived is False
    assert restored.archived_reason is None and restored.archived_at is None
    assert sorted(_parent_lines(db_session, parent)) == sorted(
        [LINE_A["coordinates"], LINE_B["coordinates"]]
    )
    assert _progress_calls == [parent.id, parent.id]


def test_drafts_list_hides_archived(db_session):
    draft = Project(name="Entwurf", is_draft=True)
    archived_draft = Project(name="Ersetzt", is_draft=True)
    db_session.add_all([draft, archived_draft])
    db_session.commit()
    archive_crud.archive_project(db_session, archived_draft.id, REASON, None, None)

    assert [p.name for p in get_draft_projects(db_session)] == ["Entwurf"]


def test_archive_needs_reason(db_session):
    _, old, _ = _family(db_session)
    with pytest.raises(archive_crud.ArchiveError, match="Begründung"):
        archive_crud.archive_project(db_session, old.id, "   ", None, None)


def test_archive_refused_with_finve_link(db_session):
    _, old, _ = _family(db_session)
    finve = Finve(id=4711, name="ABS Lübeck")
    db_session.add(finve)
    db_session.flush()
    db_session.add(FinveToProject(project_id=old.id, finve_id=finve.id))
    db_session.commit()

    with pytest.raises(archive_crud.ArchiveError, match=r"FinVe: 4711 \(ABS Lübeck\)"):
        archive_crud.archive_project(db_session, old.id, REASON, None, None)
    db_session.refresh(old)
    assert old.is_archived is False


def test_archive_refused_with_active_subprojects(db_session):
    parent, old, new = _family(db_session)
    with pytest.raises(archive_crud.ArchiveError, match="Teilprojekte") as exc:
        archive_crud.archive_project(db_session, parent.id, REASON, None, None)
    assert str(old.id) in str(exc.value) and str(new.id) in str(exc.value)


def test_archive_refused_for_cancelled_project(db_session):
    _, old, _ = _family(db_session)
    db_session.add(ProjectProgress(project_id=old.id, lifecycle_status="ABGEBROCHEN"))
    db_session.commit()
    with pytest.raises(archive_crud.ArchiveError, match="ABGEBROCHEN"):
        archive_crud.archive_project(db_session, old.id, REASON, None, None)


def test_archived_project_cannot_become_parent(db_session):
    _, old, new = _family(db_session)
    archive_crud.archive_project(db_session, old.id, REASON, None, None)
    with pytest.raises(ProjectHierarchyError, match="archiviert"):
        validate_superior_project(db_session, new.id, old.id)


# --- REST --------------------------------------------------------------------


def test_rest_archive_list_and_unarchive(client, create_user, db_session):
    create_user("admin", "pass123", UserRole.admin)
    headers = basic_auth_header("admin", "pass123")
    parent, old, _ = _family(db_session)

    resp = client.post(f"/api/v1/projects/{old.id}/archive", json={"reason": REASON}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["project"]["is_archived"] is True
    assert resp.json()["kept_links"] == {}

    # Still reachable by URL, gone from the public list.
    assert client.get(f"/api/v1/projects/{old.id}").json()["archived_reason"] == REASON
    assert old.id not in {p["id"] for p in client.get("/api/v1/projects/").json()}

    archived = client.get("/api/v1/projects/archived", headers=headers).json()
    assert archived == [
        {
            "id": old.id,
            "name": "Alte Teilmaßnahme",
            "project_number": None,
            "archived_reason": REASON,
            "archived_at": archived[0]["archived_at"],
            "superior_project_id": parent.id,
            "superior_project_name": parent.name,
        }
    ]

    again = client.post(f"/api/v1/projects/{old.id}/archive", json={"reason": REASON}, headers=headers)
    assert again.status_code == 400

    resp = client.post(f"/api/v1/projects/{old.id}/unarchive", json={}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_archived"] is False

    logs = db_session.query(ChangeLog).filter_by(project_id=old.id).order_by(ChangeLog.id).all()
    assert [log.action for log in logs] == ["ARCHIVE", "UNARCHIVE"]
    assert {e.field_name: e.new_value for e in logs[0].entries} == {
        "is_archived": "true",
        "archived_reason": json.dumps(REASON),
    }


def test_rest_archive_needs_delete_permission(client, create_user, db_session):
    create_user("viewer", "pass123", UserRole.viewer)
    _, old, _ = _family(db_session)
    headers = basic_auth_header("viewer", "pass123")
    resp = client.post(f"/api/v1/projects/{old.id}/archive", json={"reason": REASON}, headers=headers)
    assert resp.status_code == 403
    assert client.get("/api/v1/projects/archived", headers=headers).status_code == 403


def test_rest_archive_rejects_empty_reason(client, create_user, db_session):
    create_user("admin", "pass123", UserRole.admin)
    _, old, _ = _family(db_session)
    resp = client.post(
        f"/api/v1/projects/{old.id}/archive",
        json={"reason": ""},
        headers=basic_auth_header("admin", "pass123"),
    )
    assert resp.status_code == 422


# --- MCP ---------------------------------------------------------------------


def test_mcp_archive_and_unarchive(mcp_client, admin_token, db_session):
    parent, old, new = _family(db_session)

    result = _payload(
        _call(mcp_client, admin_token, "archive_project", {"project_id": old.id, "reason": REASON})
    )
    assert result["project"]["is_archived"] is True

    listed = _payload(
        _call(mcp_client, admin_token, "list_projects", {"superior_project_id": parent.id, "drafts": "include"})
    )
    assert [p["id"] for p in listed["projects"]] == [new.id]
    detail = _payload(_call(mcp_client, admin_token, "get_project", {"project_id": old.id}))
    assert detail["is_archived"] is True

    restored = _payload(_call(mcp_client, admin_token, "unarchive_project", {"project_id": old.id}))
    assert restored["is_archived"] is False
    actions = [
        log.action for log in db_session.query(ChangeLog).filter_by(project_id=old.id).order_by(ChangeLog.id)
    ]
    assert actions == ["ARCHIVE", "UNARCHIVE"]


def test_mcp_archive_needs_delete_permission(mcp_client, db_session):
    _, old, _ = _family(db_session)
    token = _key_for(db_session, _role_user(db_session, "editorish", ["mcp.access", "project.edit"]))
    result = _call(mcp_client, token, "archive_project", {"project_id": old.id, "reason": REASON})
    assert result["isError"] is True
    assert "project.delete" in result["content"][0]["text"]


def test_mcp_archive_refusal_names_links(mcp_client, admin_token, db_session):
    parent, _, _ = _family(db_session)
    result = _call(mcp_client, admin_token, "archive_project", {"project_id": parent.id, "reason": REASON})
    assert result["isError"] is True
    assert "Teilprojekte" in result["content"][0]["text"]
