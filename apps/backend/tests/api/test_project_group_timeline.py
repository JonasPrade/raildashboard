"""GET /project_groups/{id}/timeline — real CRUD against the SQLite test DB."""

from datetime import date

import pytest

from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.vib.vib_entry import VibEntry
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry


@pytest.fixture()
def seeded(db_session):
    group = ProjectGroup(name="Bedarfsplan", short_name="BP")
    parent = Project(name="ABS Nord")
    dated_leaf = Project(name="ABS Süd")
    undated = Project(name="Nur Schätzung")
    draft = Project(name="Entwurf", is_draft=True)
    db_session.add_all([parent, dated_leaf, undated, draft])
    db_session.flush()
    child = Project(name="ABS Nord PFA 1", superior_project_id=parent.id)
    db_session.add(child)
    db_session.flush()
    group.projects = [parent, child, dated_leaf, undated, draft]
    db_session.add(group)

    # The parent's VIB entry has a PFA assigned to the child (dates pool upward).
    entry = VibEntry(vib_report_id=1, vib_section="A", vib_name_raw="ABS Nord", projects=[parent])
    db_session.add(entry)
    db_session.flush()
    db_session.add(
        VibPfaEntry(
            vib_entry_id=entry.id,
            project_id=child.id,
            datum_pfb="03/2024",
            baubeginn="2. Quartal 2026",
            inbetriebnahme="Ende 2031",
        )
    )
    # Manual expected opening on the leaf + editorial parliamentary date.
    db_session.add(
        ProgressObservation(
            project_id=dated_leaf.id,
            source_type="MANUELL",
            track="MAIN",
            asserted_state="IN_BETRIEB",
            observed_date=date(2030, 12, 1),
            is_expected=True,
        )
    )
    db_session.add(
        ProjectProgress(
            project_id=dated_leaf.id,
            lifecycle_status="PAUSIERT",
            parl_befassung_date=date(2021, 6, 1),
        )
    )
    # Evidence only → not credible enough for the timeline.
    db_session.add(
        ProgressObservation(
            project_id=undated.id,
            source_type="VIB",
            track="MAIN",
            asserted_state="VORPLANUNG",
            observed_date=date(2024, 12, 31),
        )
    )
    db_session.commit()
    return {"group": group, "parent": parent, "child": child, "leaf": dated_leaf}


def test_timeline_lists_only_projects_with_concrete_dates(client, seeded):
    resp = client.get(f"/api/v1/project_groups/{seeded['group'].id}/timeline")
    assert resp.status_code == 200
    body = resp.json()
    names = [item["name"] for item in body["items"]]
    assert names == ["ABS Nord", "ABS Süd"]  # no subproject, no draft, no undated
    assert body["without_dates_count"] == 1

    parent = body["items"][0]
    by_key = {(m["kind"], m["phase"]): m for m in parent["milestones"]}
    assert by_key[("PHASE", "BAU")]["date"] == "2026-05-15"
    assert by_key[("PHASE", "BAU")]["source"] == "VIB-PFA"
    assert by_key[("PHASE", "IN_BETRIEB")]["date"] == "2031-12-15"
    assert by_key[("PFB", None)]["date"] == "2024-03-15"

    leaf = body["items"][1]
    assert leaf["lifecycle_status"] == "PAUSIERT"
    kinds = {(m["kind"], m["phase"], m["source"]) for m in leaf["milestones"]}
    assert ("PHASE", "IN_BETRIEB", "Manuell") in kinds
    assert ("PARL", None, "Manuell") in kinds


def test_timeline_with_subprojects(client, seeded):
    resp = client.get(
        f"/api/v1/project_groups/{seeded['group'].id}/timeline",
        params={"only_superior": "false"},
    )
    names = [item["name"] for item in resp.json()["items"]]
    assert "ABS Nord PFA 1" in names


def test_timeline_etag(client, seeded):
    url = f"/api/v1/project_groups/{seeded['group'].id}/timeline"
    etag = client.get(url).headers["etag"]
    assert client.get(url, headers={"If-None-Match": etag}).status_code == 304


def test_timeline_unknown_group(client):
    assert client.get("/api/v1/project_groups/999999/timeline").status_code == 404


def _expected(project_id, phase, when):
    return ProgressObservation(
        project_id=project_id,
        source_type="MANUELL",
        track="MAIN",
        asserted_state=phase,
        observed_date=when,
        is_expected=True,
    )


def test_timeline_separate_construction_stages(client, db_session):
    """HLK 11 case: the superior row keeps first BAU / last IB but lists the
    two stages as separate construction periods."""

    group = ProjectGroup(name="Korridorsanierung", short_name="HLK")
    parent = Project(name="HLK 11")
    db_session.add(parent)
    db_session.flush()
    stage1 = Project(name="HLK 11-1", superior_project_id=parent.id)
    stage2 = Project(name="HLK 11-2", superior_project_id=parent.id)
    db_session.add_all([stage1, stage2])
    db_session.flush()
    group.projects = [parent, stage1, stage2]
    db_session.add(group)
    db_session.add_all(
        [
            _expected(stage1.id, "BAU", date(2028, 1, 1)),
            _expected(stage1.id, "IN_BETRIEB", date(2028, 7, 1)),
            _expected(stage2.id, "BAU", date(2031, 1, 1)),
            _expected(stage2.id, "IN_BETRIEB", date(2031, 7, 1)),
        ]
    )
    db_session.commit()

    body = client.get(f"/api/v1/project_groups/{group.id}/timeline").json()
    (row,) = body["items"]
    by_phase = {m["phase"]: m["date"] for m in row["milestones"] if m["kind"] == "PHASE"}
    assert by_phase == {"BAU": "2028-01-01", "IN_BETRIEB": "2031-07-01"}
    assert row["construction_periods"] == [
        {"start": "2028-01-01", "end": "2028-07-01"},
        {"start": "2031-01-01", "end": "2031-07-01"},
    ]


def test_timeline_stages_from_pfas_on_the_superior_vib_entry(client, db_session):
    """The superior's VIB link reaches every section; each section counts only
    for the subproject it is assigned to, so the stages stay separate."""

    group = ProjectGroup(name="Ausbau", short_name="AB")
    parent = Project(name="ABS West")
    db_session.add(parent)
    db_session.flush()
    stage1 = Project(name="ABS West PFA 1", superior_project_id=parent.id)
    stage2 = Project(name="ABS West PFA 2", superior_project_id=parent.id)
    db_session.add_all([stage1, stage2])
    db_session.flush()
    group.projects = [parent, stage1, stage2]
    db_session.add(group)
    entry = VibEntry(vib_report_id=1, vib_section="A", vib_name_raw="ABS West", projects=[parent])
    db_session.add(entry)
    db_session.flush()
    db_session.add_all(
        [
            VibPfaEntry(vib_entry_id=entry.id, project_id=stage1.id, baubeginn="01/2027", inbetriebnahme="12/2027"),
            VibPfaEntry(vib_entry_id=entry.id, project_id=stage2.id, baubeginn="01/2030", inbetriebnahme="12/2030"),
        ]
    )
    db_session.commit()

    body = client.get(f"/api/v1/project_groups/{group.id}/timeline").json()
    (row,) = body["items"]
    assert len(row["construction_periods"]) == 2
