"""A parent's commissioning includes every part (#344) — timeline, forecast
and list cache read the subtree the same way.

Case: ABS München – Mühldorf – Freilassing. Baustufe 1 is in service since
12/2017, the Teilmaßnahmen are still in planning without dates; the parent
used to show „In Betrieb“ from 2017.
"""

from __future__ import annotations

from datetime import date

import pytest

from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.vib.vib_entry import VibEntry
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry
from dashboard_backend.models.vib.vib_report import VibReport


def _bound_text() -> str:
    return f"nach {date.today().year}"


@pytest.fixture()
def muehldorf(db_session):
    group = ProjectGroup(name="Bedarfsplan Test", short_name="BPT")
    parent = Project(name="ABS München – Mühldorf – Freilassing")
    db_session.add(parent)
    db_session.flush()
    stage = Project(name="Baustufe 1a", superior_project_id=parent.id)
    tm1 = Project(name="Teilmaßnahme 1", superior_project_id=parent.id)
    julbach = Project(name="Bahnhof Julbach", superior_project_id=parent.id)
    cancelled = Project(name="Verworfene Variante", superior_project_id=parent.id)
    db_session.add_all([stage, tm1, julbach, cancelled])
    db_session.flush()
    group.projects = [parent, stage, tm1, julbach, cancelled]
    db_session.add(group)

    report = VibReport(year=2023)
    db_session.add(report)
    db_session.flush()
    entry = VibEntry(
        vib_report_id=report.id,
        vib_section="B.4.1.1",
        vib_name_raw="ABS 38",
        projects=[parent],
        confirmed=True,
    )
    db_session.add(entry)
    db_session.flush()
    db_session.add(
        VibPfaEntry(
            vib_entry_id=entry.id,
            project_id=stage.id,
            nr_pfa="1a",
            datum_pfb="20.03.2002",
            baubeginn="10.08.2002",
            inbetriebnahme="12/2017",
        )
    )
    db_session.add_all(
        [
            ProjectProgress(
                project_id=stage.id,
                computed_phase="IN_BETRIEB",
                computed_confidence=0.6,
            ),
            ProjectProgress(
                project_id=tm1.id,
                computed_phase="GENEHMIGUNGSPLANUNG",
                computed_confidence=0.35,
            ),
            ProjectProgress(
                project_id=cancelled.id,
                computed_phase="VORPLANUNG",
                computed_confidence=0.5,
                lifecycle_status="ABGEBROCHEN",
            ),
        ]
    )
    db_session.commit()
    return {"group": group, "parent": parent, "stage": stage, "tm1": tm1, "julbach": julbach}


def _row(client, group):
    body = client.get(f"/api/v1/project_groups/{group.id}/timeline").json()
    (row,) = body["items"]
    return row


def test_timeline_holds_the_parent_open(client, muehldorf):
    row = _row(client, muehldorf["group"])
    ibn = [m for m in row["milestones"] if m["kind"] == "PHASE" and m["phase"] == "IN_BETRIEB"]
    assert len(ibn) == 1
    assert ibn[0]["date_precision"] == "NOT_BEFORE"
    assert ibn[0]["date_text"] == _bound_text()
    assert "Termin offen" in ibn[0]["derivation"]

    (part,) = [m for m in row["milestones"] if m["kind"] == "PART_IBN"]
    assert part["date"].startswith("2017-12")

    names = {p["name"] for p in row["pending_parts"]}
    assert names == {"Teilmaßnahme 1", "Bahnhof Julbach"}  # cancelled one left out
    phases = {p["name"]: p["phase"] for p in row["pending_parts"]}
    assert phases == {"Teilmaßnahme 1": "GENEHMIGUNGSPLANUNG", "Bahnhof Julbach": None}


def test_forecast_and_list_cache_match_the_timeline(client, db_session, muehldorf):
    parent = muehldorf["parent"]
    body = client.get(f"/api/v1/projects/{parent.id}/progress").json()
    steps = {s["phase"]: s for s in body["forecast"]["next_steps"]}
    assert steps["IN_BETRIEB"]["date_precision"] == "NOT_BEFORE"
    assert steps["IN_BETRIEB"]["date_text"] == _bound_text()
    assert "überschritten" not in (body["forecast"]["remaining_text"] or "")

    db_session.expire_all()
    progress = db_session.query(ProjectProgress).filter_by(project_id=parent.id).one()
    assert progress.commissioning_precision == "NOT_BEFORE"
    assert progress.commissioning_date == date(date.today().year + 1, 1, 1)


def test_manual_commissioning_of_the_parent_wins(client, db_session, muehldorf):
    parent = muehldorf["parent"]
    db_session.add(
        ProgressObservation(
            project_id=parent.id,
            source_type="MANUELL",
            track="MAIN",
            asserted_state="IN_BETRIEB",
            observed_date=date(2034, 12, 15),
            is_expected=True,
        )
    )
    db_session.commit()
    row = _row(client, muehldorf["group"])
    (ibn,) = [m for m in row["milestones"] if m["kind"] == "PHASE" and m["phase"] == "IN_BETRIEB"]
    assert (ibn["date"], ibn["source"]) == ("2034-12-15", "Manuell")
    assert ibn["date_precision"] == "EXACT"


def test_all_parts_dated_keeps_the_latest_known_date(client, db_session, muehldorf):
    """Once every part is in service or dated, nothing is held open."""

    for key in ("tm1", "julbach"):
        db_session.add(
            ProgressObservation(
                project_id=muehldorf[key].id,
                source_type="MANUELL",
                track="MAIN",
                asserted_state="IN_BETRIEB",
                observed_date=date(2032, 12, 15),
                is_expected=True,
            )
        )
    db_session.commit()
    row = _row(client, muehldorf["group"])
    (ibn,) = [m for m in row["milestones"] if m["kind"] == "PHASE" and m["phase"] == "IN_BETRIEB"]
    assert ibn["date"] == "2032-12-15"
    assert ibn["date_precision"] == "EXACT"
    assert row["pending_parts"] == []
    assert not [m for m in row["milestones"] if m["kind"] == "PART_IBN"]


def test_open_pfa_section_holds_a_leaf_open(client, db_session):
    """A project without subprojects whose newest PFA table lists a section
    without commissioning: the latest dated section is not the end."""

    group = ProjectGroup(name="Ausbau Test", short_name="AT")
    project = Project(name="ABS Ost")
    db_session.add(project)
    db_session.flush()
    group.projects = [project]
    db_session.add(group)
    old = VibReport(year=2021)
    new = VibReport(year=2023)
    db_session.add_all([old, new])
    db_session.flush()
    for report, sections in (
        # The old table lacks a date for PFA 2 too, but only the newest counts.
        (old, [("1", "06/2020", "12/2024"), ("2", None, None)]),
        (new, [("1", "06/2020", "12/2024"), ("2", None, None)]),
    ):
        entry = VibEntry(
            vib_report_id=report.id, vib_section="B", vib_name_raw="ABS Ost", projects=[project], confirmed=True
        )
        db_session.add(entry)
        db_session.flush()
        for nr, start, opening in sections:
            db_session.add(
                VibPfaEntry(vib_entry_id=entry.id, nr_pfa=nr, baubeginn=start, inbetriebnahme=opening)
            )
    db_session.add(ProjectProgress(project_id=project.id, computed_phase="BAU", computed_confidence=0.6))
    db_session.commit()

    row = _row(client, group)
    (ibn,) = [m for m in row["milestones"] if m["kind"] == "PHASE" and m["phase"] == "IN_BETRIEB"]
    assert ibn["date_precision"] == "NOT_BEFORE"
    assert [p["name"] for p in row["pending_parts"]] == ["ABS Ost: 2"]
    # The section of 12/2024 is a past partial commissioning.
    (part,) = [m for m in row["milestones"] if m["kind"] == "PART_IBN"]
    assert part["date"].startswith("2024-12")
