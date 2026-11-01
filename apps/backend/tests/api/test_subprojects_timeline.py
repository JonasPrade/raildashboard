"""GET /projects/{id}/subprojects/timeline — real CRUD against the SQLite test DB."""

from datetime import date

import pytest

from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project


def _expected(project_id, phase, when):
    return ProgressObservation(
        project_id=project_id,
        source_type="MANUELL",
        track="MAIN",
        asserted_state=phase,
        observed_date=when,
        is_expected=True,
    )


@pytest.fixture()
def seeded(db_session):
    parent = Project(name="HLK 11")
    db_session.add(parent)
    db_session.flush()
    stage2 = Project(name="HLK 11-2", superior_project_id=parent.id)
    stage1 = Project(name="HLK 11-1", superior_project_id=parent.id)
    undated = Project(name="HLK 11-3", superior_project_id=parent.id)
    draft = Project(name="HLK 11-Entwurf", superior_project_id=parent.id, is_draft=True)
    db_session.add_all([stage2, stage1, undated, draft])
    db_session.flush()
    grandchild = Project(name="HLK 11-1a", superior_project_id=stage1.id)
    db_session.add(grandchild)
    db_session.flush()
    db_session.add_all(
        [
            # Stage 1 gets its dates only through its own subproject (pooled).
            _expected(grandchild.id, "BAU", date(2028, 1, 1)),
            _expected(grandchild.id, "IN_BETRIEB", date(2028, 7, 1)),
            _expected(stage2.id, "BAU", date(2031, 1, 1)),
            _expected(stage2.id, "IN_BETRIEB", date(2031, 7, 1)),
        ]
    )
    db_session.commit()
    return {"parent": parent, "stage1": stage1, "stage2": stage2, "undated": undated}


def test_subprojects_timeline_lists_direct_children(client, seeded):
    resp = client.get(f"/api/v1/projects/{seeded['parent'].id}/subprojects/timeline")
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == seeded["parent"].id
    # Direct children only (no grandchild, no draft), ordered by name.
    assert [item["name"] for item in body["items"]] == ["HLK 11-1", "HLK 11-2"]
    assert body["without_dates"] == [{"project_id": seeded["undated"].id, "name": "HLK 11-3"}]

    stage1 = body["items"][0]
    assert stage1["superior_project_id"] == seeded["parent"].id
    by_phase = {m["phase"]: m["date"] for m in stage1["milestones"] if m["kind"] == "PHASE"}
    assert by_phase == {"BAU": "2028-01-01", "IN_BETRIEB": "2028-07-01"}


def test_subprojects_timeline_leaf_project_is_empty(client, seeded):
    body = client.get(f"/api/v1/projects/{seeded['stage2'].id}/subprojects/timeline").json()
    assert body["items"] == []
    assert body["without_dates"] == []


def test_subprojects_timeline_etag(client, seeded):
    url = f"/api/v1/projects/{seeded['parent'].id}/subprojects/timeline"
    etag = client.get(url).headers["etag"]
    assert client.get(url, headers={"If-None-Match": etag}).status_code == 304


def test_subprojects_timeline_unknown_project(client):
    assert client.get("/api/v1/projects/999999/subprojects/timeline").status_code == 404
