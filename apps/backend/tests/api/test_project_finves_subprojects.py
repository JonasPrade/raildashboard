"""GET /projects/{id}/finves?include_subprojects: a parent project aggregates
the FinVes of all its descendants, each FinVe once."""

from __future__ import annotations

from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.project import Project


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


def test_parent_finves_default_only_own(client, db_session):
    parent = _seed(db_session)

    body = client.get(f"/api/v1/projects/{parent.id}/finves").json()
    assert [(f["id"], f["from_subprojects"]) for f in body] == [(5001, False)]
