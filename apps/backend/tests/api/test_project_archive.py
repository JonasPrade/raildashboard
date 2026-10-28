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


def _sammel_year_links(db, project):
    """Sammel-FinVes 763 and 1168 with a Haushalt year link, as for project 1471.
    (One year each: SQLite ignores the partial unique indexes.)"""
    for fid, name in ((763, "SV Lph. 1/2 A"), (1168, "SV Lph. 3/ 4")):
        db.add(Finve(id=fid, name=name, is_sammel_finve=True))
        db.flush()
        db.add(FinveToProject(project_id=project.id, finve_id=fid, haushalt_year=2027))
    db.commit()


def test_archive_keeps_sammel_finve_year_links(db_session):
    _, old, _ = _family(db_session)
    _sammel_year_links(db_session, old)

    result = archive_crud.archive_project(db_session, old.id, REASON, None, None)

    assert result["project"].is_archived is True
    assert result["kept_links"] == {"sammel_finve_year_links": [763, 1168]}
    # Kept as history: neither deleted nor moved.
    links = db_session.query(FinveToProject).filter(FinveToProject.project_id == old.id).count()
    assert links == 2


def test_archive_refused_with_permanent_sammel_finve_link(db_session):
    _, old, _ = _family(db_session)
    _sammel_year_links(db_session, old)
    db_session.add(Finve(id=900, name="SV Lph. 5", is_sammel_finve=True))
    db_session.flush()
    db_session.add(FinveToProject(project_id=old.id, finve_id=900, haushalt_year=None))
    db_session.commit()

    with pytest.raises(archive_crud.ArchiveError, match=r"FinVe: 900 \(SV Lph. 5\)") as exc:
        archive_crud.archive_project(db_session, old.id, REASON, None, None)
    assert "763" not in str(exc.value) and "1168" not in str(exc.value)


def test_archive_refused_with_gvfg_link(db_session):
    from datetime import date

    from dashboard_backend.models.gvfg import GvfgEntry, GvfgProgram

    _, old, _ = _family(db_session)
    _sammel_year_links(db_session, old)
    program = GvfgProgram(
        year_from=2025, year_to=2029, title="GVFG 2025–2029", stand=date(2025, 7, 18), periods=[]
    )
    entry = GvfgEntry(
        program=program, key="07 G 7050_A", key_raw="07 G 7050 _A", land="Rheinland-Pfalz",
        kind="kommunal", part="finanzrelevant", name="Mainz-Finthen",
    )
    entry.projects.append(old)
    db_session.add(program)
    db_session.commit()

    with pytest.raises(archive_crud.ArchiveError, match=r"GVFG: 07 G 7050_A \(2025\)"):
        archive_crud.archive_project(db_session, old.id, REASON, None, None)


def test_sammel_year_links_do_not_lift_the_subproject_block(db_session):
    parent, _, _ = _family(db_session)
    _sammel_year_links(db_session, parent)
    with pytest.raises(archive_crud.ArchiveError, match="Teilprojekte"):
        archive_crud.archive_project(db_session, parent.id, REASON, None, None)


def test_archived_project_leaves_sammel_finve_evaluations(db_session):
    from dashboard_backend.crud.finves import (
        get_project_finves_with_budgets,
        list_finves,
        list_sammel_finves_progress,
    )

    parent, old, new = _family(db_session)
    _sammel_year_links(db_session, old)
    db_session.add(FinveToProject(project_id=new.id, finve_id=763, haushalt_year=2027))
    db_session.commit()
    archive_crud.archive_project(db_session, old.id, REASON, None, None)

    by_id = {f.id: f for f in list_finves(db_session)}
    assert by_id[763].project_count == 1
    assert by_id[763].project_names == ["PFA 1"]
    assert [(p.id, p.is_archived) for p in by_id[763].projects] == [(new.id, False), (old.id, True)]
    assert by_id[1168].project_count == 0

    progress = {f.finve_id: [p.id for p in f.projects] for f in list_sammel_finves_progress(db_session)}
    assert progress == {763: [new.id], 1168: []}

    # The parent's FinVe sums only reach 763 through the active subproject.
    parent_finves = get_project_finves_with_budgets(db_session, parent, include_subprojects=True)
    assert [(f.id, [p.id for p in f.subprojects]) for f in parent_finves] == [(763, [new.id])]


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


# --- Ersetzt durch (#261) ----------------------------------------------------


def test_archive_with_successor_links_both_ways(client, create_user, db_session):
    create_user("admin", "pass123", UserRole.admin)
    headers = basic_auth_header("admin", "pass123")
    _, old, new = _family(db_session)

    resp = client.post(
        f"/api/v1/projects/{old.id}/archive",
        json={"reason": REASON, "replaced_by_project_id": new.id},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["project"]["replaced_by_project_id"] == new.id

    assert client.get(f"/api/v1/projects/{old.id}/replacement").json() == {
        "replaced_by": {"id": new.id, "name": "PFA 1", "project_number": None},
        "replaces": [],
    }
    assert client.get(f"/api/v1/projects/{new.id}/replacement").json() == {
        "replaced_by": None,
        "replaces": [{"id": old.id, "name": "Alte Teilmaßnahme", "project_number": None}],
    }
    log = db_session.query(ChangeLog).filter_by(project_id=old.id, action="ARCHIVE").one()
    assert {e.field_name: e.new_value for e in log.entries}["replaced_by_project_id"] == str(new.id)

    # Restoring clears the successor (the changelog keeps it).
    client.post(f"/api/v1/projects/{old.id}/unarchive", json={}, headers=headers)
    db_session.refresh(old)
    assert old.replaced_by_project_id is None
    assert client.get(f"/api/v1/projects/{new.id}/replacement").json()["replaces"] == []


@pytest.mark.parametrize(
    "successor, message",
    [("self", "selbst ersetzen"), ("missing", "gibt es nicht"), ("draft", "Entwurf"), ("archived", "selbst archiviert")],
)
def test_archive_rejects_invalid_successor(db_session, successor, message):
    parent, old, new = _family(db_session)
    other = Project(name="Anderes", is_draft=successor == "draft")
    db_session.add(other)
    db_session.commit()
    if successor == "archived":
        archive_crud.archive_project(db_session, other.id, REASON, None, None)
    target = {"self": old.id, "missing": 999999}.get(successor, other.id)
    with pytest.raises(archive_crud.ArchiveError, match=message):
        archive_crud.archive_project(db_session, old.id, REASON, None, None, replaced_by_project_id=target)
    db_session.refresh(old)
    assert old.is_archived is False


def test_successor_map_follows_chain_and_redirects():
    from dashboard_backend.crud.projects.archive import redirect_replaced

    ids, redirected = redirect_replaced([1, 2, 3], {1: 3, 2: 4})
    assert ids == [3, 4]
    assert redirected == {3: 1, 4: 2}


def test_successor_map_skips_archived_without_reachable_successor(db_session):
    a, b, c = (Project(name=n) for n in ("A", "B", "C"))
    db_session.add_all([a, b, c])
    db_session.commit()
    archive_crud.archive_project(db_session, a.id, REASON, None, None, replaced_by_project_id=b.id)
    archive_crud.archive_project(db_session, b.id, REASON, None, None, replaced_by_project_id=c.id)
    assert archive_crud.successor_map(db_session) == {a.id: c.id, b.id: c.id}
    archive_crud.archive_project(db_session, c.id, REASON, None, None)
    assert archive_crud.successor_map(db_session) == {}


def test_mcp_archive_with_successor_and_assignment_warning(mcp_client, admin_token, db_session):
    _, old, new = _family(db_session)
    result = _payload(
        _call(
            mcp_client,
            admin_token,
            "archive_project",
            {"project_id": old.id, "reason": REASON, "replaced_by_project_id": new.id},
        )
    )
    assert result["project"]["replaced_by_project_id"] == new.id
    detail = _payload(_call(mcp_client, admin_token, "get_project", {"project_id": new.id}))
    assert detail["replaces"] == [{"id": old.id, "name": "Alte Teilmaßnahme", "project_number": None}]
    assert archive_crud.archived_warnings(db_session, [old.id, new.id]) == [
        f"Projekt {old.id} „Alte Teilmaßnahme“ ist archiviert und ersetzt durch {new.id} „PFA 1“"
        " — Zuordnung gespeichert; meist gehört sie zum Nachfolger."
    ]


def test_merge_moves_successor_links(db_session, monkeypatch):
    from dashboard_backend.crud.projects import merge as merge_crud

    monkeypatch.setattr(merge_crud.progress_crud, "sync_derived_observations", lambda db, pid: None)
    monkeypatch.setattr(merge_crud.progress_crud, "recompute_progress", lambda db, pid: True)
    old, survivor, merged = (Project(name=n) for n in ("Alt", "Neu", "Neu doppelt"))
    db_session.add_all([old, survivor, merged])
    db_session.commit()
    archive_crud.archive_project(db_session, old.id, REASON, None, None, replaced_by_project_id=merged.id)
    old_id, survivor_id = old.id, survivor.id

    merge_crud.merge_projects(db_session, survivor_id, merged.id, apply=True)
    db_session.expire_all()
    assert db_session.get(Project, old_id).replaced_by_project_id == survivor_id


def test_previous_edition_link_goes_to_successor(db_session, monkeypatch):
    from dashboard_backend.crud import gvfg as gvfg_crud

    old = Project(name="Stadtbahn alt", project_number="08 D 1_A")
    new = Project(name="Stadtbahn neu")
    db_session.add_all([old, new])
    db_session.commit()
    archive_crud.archive_project(db_session, old.id, REASON, None, None, replaced_by_project_id=new.id)
    monkeypatch.setattr(gvfg_crud, "_previous_links", lambda db: {"08 D 1_A": [old.id]})

    out = gvfg_crud.build_suggestions(db_session, [{"key": "08 D 1_A", "name": "Stadtbahn"}])["by_key"]["08 D 1_A"]
    assert out["selected"] == [new.id]
    assert any("umgelenkt" in flag for flag in out["flags"])


def test_infraplan_hit_on_archived_project_moves_to_successor():
    from dashboard_backend.tasks.infraplan_matching import ProjectRef, suggest_rows

    # The archived project is no candidate (load_projects skips it); its number
    # still comes from last year's confirmed link.
    projects = [ProjectRef(2, "NBS/ABS Bielefeld – Seelze")]
    row = {"row_key": "A-1", "section": "A", "primary_number": "2-016-V01"}
    out = suggest_rows([row], projects, {"2-016-V01": [1]}, successors={1: 2})["A-1"]
    assert out[0]["project_id"] == 2
    assert out[0]["redirected_from"] == 1
