"""Project merge (feature-project-merge.md): plan vs. apply, link re-pointing,
duplicates, geometry source, redirect, changelog and the permission gate —
through the MCP tool and the REST endpoint.
"""

from __future__ import annotations

import json

import pytest

from dashboard_backend.crud.projects import merge as merge_crud
from dashboard_backend.crud.projects.merge import MergeError, merge_projects
from dashboard_backend.models.associations.text_to_project import TextToProject
from dashboard_backend.models.change_tracking import ChangeLog, ChangeLogEntry
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.projects.project_redirect import ProjectRedirect
from dashboard_backend.models.projects.project_text import ProjectText
from dashboard_backend.models.projects.project_text_type import ProjectTextType
from dashboard_backend.models.todos.todo import Todo
from dashboard_backend.schemas.users import UserRole
from tests.api.test_mcp_server import _call, _key_for, _payload, admin_token, mcp_client  # noqa: F401

POINT = json.dumps({"type": "Point", "coordinates": [9.0, 52.0]})
LINE = json.dumps({"type": "LineString", "coordinates": [[9.0, 52.0], [9.1, 52.1]]})


@pytest.fixture(autouse=True)
def _no_derived_rebuild(monkeypatch):
    """The derived-observation sync reads import tables this test DB lacks."""
    calls: list[int] = []
    monkeypatch.setattr(
        merge_crud.progress_crud, "sync_derived_observations", lambda db, pid: calls.append(pid)
    )
    monkeypatch.setattr(merge_crud.progress_crud, "recompute_progress", lambda db, pid: True)
    return calls


def _duplicates(db):
    group_a = ProjectGroup(name="GVFG", short_name="GVFG", color="#000000")
    group_b = ProjectGroup(name="GVFG BW", short_name="GVFG BW", color="#000000")
    survivor = Project(
        name="Ausbau Holzminden - Kreiensen",
        project_number="03 D 4506_A",
        description="Fördersatz 75 %",
        geojson_representation=POINT,
        nbs=False,
        elektrification=True,
    )
    merged = Project(
        name="Ausbau Holzminden – Kreiensen",
        project_number="03 D 4506_ A",
        justification="Begründung aus der zweiten Welle",
        geojson_representation=LINE,
        length=12.5,
        nbs=True,
    )
    survivor.project_groups = [group_a]
    merged.project_groups = [group_a, group_b]
    db.add_all([group_a, group_b, survivor, merged])
    db.flush()
    child = Project(name="Teilabschnitt", superior_project_id=merged.id, geojson_representation=LINE)
    text_type = ProjectTextType(name="Notiz")
    db.add_all([child, text_type])
    db.flush()
    text = ProjectText(header="Hinweis", text="…", type=text_type.id)
    db.add(text)
    db.flush()
    db.add_all(
        [
            TextToProject(project_id=merged.id, text_id=text.id),
            Todo(title="Prüfen", project_id=merged.id),
            ChangeLog(project_id=merged.id, action="CREATE", entries=[]),
            ProjectProgress(project_id=survivor.id),
            ProjectProgress(
                project_id=merged.id,
                manual_phase_override="BAU",
                manual_override_note="Bauportal",
                has_planfeststellung=True,
            ),
            ProgressObservation(
                project_id=merged.id,
                source_type="MANUELL",
                track="MAIN",
                asserted_state="BAU",
                is_derived=False,
            ),
            ProgressObservation(
                project_id=merged.id,
                source_type="VIB",
                track="MAIN",
                asserted_state="BAU",
                is_derived=True,
            ),
        ]
    )
    db.commit()
    return survivor, merged, child


def test_plan_writes_nothing(db_session):
    survivor, merged, child = _duplicates(db_session)
    plan = merge_projects(db_session, survivor.id, merged.id)

    assert plan["applied"] is False
    assert plan["geometry_from"] == "survivor"
    assert plan["field_changes"]["nbs"] == {"old": False, "new": True}
    assert plan["field_changes"]["justification"]["new"] == "Begründung aus der zweiten Welle"
    assert "description" not in plan["field_changes"]  # survivor's value wins
    assert plan["links"]["project_to_project_group"] == {"moved": 1, "dropped": 1}
    assert plan["links"]["text_to_project"] == {"moved": 1, "dropped": 0}
    assert plan["links"]["progress_observation"] == {"moved": 1, "dropped": 1}
    assert plan["subprojects_moved"] == [child.id]
    assert any("Unterprojekte" in w for w in plan["warnings"])
    assert sorted(plan["progress_changes"]) == [
        "has_planfeststellung",
        "manual_override_note",
        "manual_phase_override",
    ]
    assert db_session.get(Project, merged.id) is not None
    assert db_session.query(ProjectRedirect).count() == 0


def test_apply_moves_links_and_leaves_redirect(db_session, create_user, _no_derived_rebuild):
    admin = create_user("admin", "adminpass", UserRole.admin)
    survivor, merged, child = _duplicates(db_session)
    survivor_id, merged_id = survivor.id, merged.id

    result = merge_projects(
        db_session, survivor_id, merged_id, apply=True, user_id=admin.id, username="admin"
    )
    assert result["applied"] is True
    db_session.expire_all()

    assert db_session.get(Project, merged_id) is None
    kept = db_session.get(Project, survivor_id)
    assert kept.nbs is True and kept.elektrification is True
    assert kept.description == "Fördersatz 75 %"
    assert kept.justification == "Begründung aus der zweiten Welle"
    # With the subproject moved over, the survivor aggregates its geometry.
    aggregated = json.loads(kept.geojson_representation)
    assert aggregated["type"] == "FeatureCollection"
    assert len(aggregated["features"]) == 1
    assert sorted(g.short_name for g in kept.project_groups) == ["GVFG", "GVFG BW"]
    assert db_session.get(Project, child.id).superior_project_id == survivor_id
    assert db_session.query(TextToProject).filter_by(project_id=survivor_id).count() == 1
    assert db_session.query(Todo).filter_by(project_id=survivor_id).count() == 1

    observations = db_session.query(ProgressObservation).filter_by(project_id=survivor_id).all()
    assert [o.is_derived for o in observations] == [False]  # derived ones are rebuilt
    assert _no_derived_rebuild == [survivor_id]
    progress = db_session.query(ProjectProgress).filter_by(project_id=survivor_id).one()
    assert progress.manual_phase_override == "BAU"
    assert progress.has_planfeststellung is True
    assert db_session.query(ProjectProgress).filter_by(project_id=merged_id).count() == 0

    # The merged project's history moved over, plus one MERGE entry.
    actions = sorted(c.action for c in db_session.query(ChangeLog).filter_by(project_id=survivor_id))
    assert actions == ["CREATE", "MERGE"]
    marker = (
        db_session.query(ChangeLogEntry)
        .join(ChangeLog)
        .filter(ChangeLog.action == "MERGE", ChangeLogEntry.field_name == "merged_project")
        .one()
    )
    assert json.loads(marker.new_value)["id"] == merged_id

    redirect = db_session.get(ProjectRedirect, merged_id)
    assert redirect.new_project_id == survivor_id
    assert redirect.old_name == "Ausbau Holzminden – Kreiensen"
    assert redirect.merged_by_user_id == admin.id


def test_geometry_from_merged(db_session):
    survivor, merged, child = _duplicates(db_session)
    child.superior_project_id = None  # otherwise the survivor aggregates the child
    db_session.commit()
    survivor_id = survivor.id
    plan = merge_projects(db_session, survivor_id, merged.id, geometry_from="merged", apply=True)
    assert plan["geometry_changed"] is True
    assert plan["field_changes"]["length"] == {"old": None, "new": 12.5}
    db_session.expire_all()
    kept = db_session.get(Project, survivor_id)
    assert kept.geojson_representation == LINE
    assert kept.length == 12.5


def test_survivor_without_geometry_takes_merged(db_session):
    survivor, merged, _ = _duplicates(db_session)
    survivor.geojson_representation = None
    db_session.commit()
    plan = merge_projects(db_session, survivor.id, merged.id)
    assert plan["geometry_from"] == "merged"
    assert plan["warnings"]


def test_redirects_do_not_chain(db_session):
    first = Project(name="A")
    second = Project(name="B")
    third = Project(name="C")
    db_session.add_all([first, second, third])
    db_session.commit()
    a, b, c = first.id, second.id, third.id

    merge_projects(db_session, b, a, apply=True)  # A → B
    merge_projects(db_session, c, b, apply=True)  # B → C, so A must point to C
    db_session.expire_all()
    assert db_session.get(ProjectRedirect, a).new_project_id == c
    assert db_session.get(ProjectRedirect, b).new_project_id == c


def test_rejections(db_session):
    survivor, merged, child = _duplicates(db_session)
    with pytest.raises(MergeError, match="sich selbst"):
        merge_projects(db_session, survivor.id, survivor.id)
    with pytest.raises(MergeError, match="nicht gefunden"):
        merge_projects(db_session, survivor.id, 999_999)
    with pytest.raises(MergeError, match="Unterprojekt"):
        merge_projects(db_session, merged.id, child.id)
    with pytest.raises(MergeError, match="übergeordnetes Projekt"):
        merge_projects(db_session, child.id, merged.id)


# --- MCP tool + REST ---------------------------------------------------------


def test_mcp_merge_plan_then_apply(mcp_client, admin_token, db_session):  # noqa: F811
    survivor, merged, _ = _duplicates(db_session)
    survivor_id, merged_id = survivor.id, merged.id
    args = {"survivor_id": survivor_id, "merged_id": merged_id}

    plan = _payload(_call(mcp_client, admin_token, "merge_projects", args))
    assert plan["applied"] is False
    assert db_session.get(Project, merged_id) is not None

    done = _payload(_call(mcp_client, admin_token, "merge_projects", {**args, "apply": True}))
    assert done["applied"] is True

    # The old id resolves to the survivor in get_project, other tools say where it went.
    detail = _payload(_call(mcp_client, admin_token, "get_project", {"project_id": merged_id}))
    assert detail["id"] == survivor_id
    assert detail["redirected_from"] == merged_id
    progress = _call(mcp_client, admin_token, "get_project_progress", {"project_id": merged_id})
    assert progress["isError"] is True
    assert str(survivor_id) in progress["content"][0]["text"]


def test_mcp_merge_needs_capability(mcp_client, create_user, db_session):  # noqa: F811
    admin = create_user("admin", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["mcp.access", "project.edit", "project.delete"])
    survivor, merged, _ = _duplicates(db_session)
    result = _call(
        mcp_client, token, "merge_projects", {"survivor_id": survivor.id, "merged_id": merged.id}
    )
    assert result["isError"] is True
    assert "project.merge" in result["content"][0]["text"]


def test_rest_merge_and_redirect(mcp_client, admin_token, db_session):  # noqa: F811
    survivor, merged, _ = _duplicates(db_session)
    survivor_id, merged_id = survivor.id, merged.id
    headers = {"Authorization": f"Bearer {admin_token}"}

    rejected = mcp_client.post(
        "/api/v1/projects/merge",
        json={"survivor_id": survivor_id, "merged_id": survivor_id},
        headers=headers,
    )
    assert rejected.status_code == 400

    response = mcp_client.post(
        "/api/v1/projects/merge",
        json={"survivor_id": survivor_id, "merged_id": merged_id, "apply": True},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["applied"] is True

    old_link = mcp_client.get(f"/api/v1/projects/{merged_id}")
    assert old_link.status_code == 200
    assert old_link.json()["id"] == survivor_id
    assert mcp_client.get("/api/v1/projects/999999").status_code == 404


def test_rest_merge_needs_permission(mcp_client, create_user, db_session):  # noqa: F811
    editor = create_user("editor", "editorpass", UserRole.editor)
    token = _key_for(db_session, editor)
    survivor, merged, _ = _duplicates(db_session)
    response = mcp_client.post(
        "/api/v1/projects/merge",
        json={"survivor_id": survivor.id, "merged_id": merged.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_draft_can_be_merged_into_final_survivor(db_session, create_user):
    admin = create_user("admin", "adminpass", UserRole.admin)
    survivor = Project(name="Ausbau A", project_number="01 D 1_A", is_draft=False)
    draft = Project(name="Ausbau A (Import)", project_number="01 D 1_ A", is_draft=True, justification="x")
    db_session.add_all([survivor, draft])
    db_session.commit()
    survivor_id, draft_id = survivor.id, draft.id

    merge_projects(db_session, survivor_id, draft_id, apply=True, user_id=admin.id, username="admin")
    db_session.expire_all()

    assert db_session.get(Project, draft_id) is None
    kept = db_session.get(Project, survivor_id)
    assert kept.is_draft is False
    assert kept.justification == "x"
    assert db_session.query(ProjectRedirect).filter_by(old_project_id=draft_id).count() == 1
