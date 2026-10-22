"""GET /projects/{id}/finves?include_subprojects: a parent project aggregates
the FinVes of all its descendants, each FinVe once."""

from __future__ import annotations

import json

from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.project import Project
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    admin_token,
    mcp_client,
)


def _seed(db):
    parent = Project(name="Ausbaustrecke", is_draft=False)
    db.add(parent)
    db.flush()
    child = Project(name="1. BA", superior_project_id=parent.id, is_draft=False)
    db.add(child)
    db.flush()
    grandchild = Project(name="1. BA, PFA 1", superior_project_id=child.id, is_draft=False)
    own = Finve(id=5001, name="Eigene FinVe")
    shared = Finve(id=5002, name="Geteilte FinVe")
    deep = Finve(id=5003, name="FinVe des Enkels")
    db.add_all([grandchild, own, shared, deep])
    db.flush()
    db.add_all(
        [
            FinveToProject(project_id=parent.id, finve_id=own.id),
            FinveToProject(project_id=child.id, finve_id=shared.id),
            FinveToProject(project_id=grandchild.id, finve_id=shared.id),
            FinveToProject(project_id=grandchild.id, finve_id=deep.id),
        ]
    )
    db.commit()
    return parent


def test_parent_finves_include_all_descendants_once(client, db_session):
    parent = _seed(db_session)

    body = client.get(f"/api/v1/projects/{parent.id}/finves?include_subprojects=true").json()
    assert [(f["id"], f["from_subprojects"]) for f in body] == [
        (5001, False),
        (5002, True),
        (5003, True),
    ]
    assert [[p["name"] for p in f["subprojects"]] for f in body] == [
        [],
        ["1. BA", "1. BA, PFA 1"],
        ["1. BA, PFA 1"],
    ]


def test_parent_finves_default_only_own(client, db_session):
    parent = _seed(db_session)

    body = client.get(f"/api/v1/projects/{parent.id}/finves").json()
    assert [(f["id"], f["from_subprojects"]) for f in body] == [(5001, False)]


def test_mcp_list_project_finves_include_subprojects(mcp_client, admin_token, db_session):
    parent = _seed(db_session)

    result = _call(
        mcp_client, admin_token, "list_project_finves", {"project_id": parent.id, "include_subprojects": True}
    )
    assert result["isError"] is False, result
    # A list result comes back as one content item per element.
    assert [json.loads(c["text"])["id"] for c in result["content"]] == [5001, 5002, 5003]
