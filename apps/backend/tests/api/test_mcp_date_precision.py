"""MCP: date precision of planning-state observations (issue #248) — add,
update in place, forecast labels, list output and the date filters."""

from __future__ import annotations

from datetime import date

from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _payload,
    admin_token,
    mcp_client,
)


def _hlk_project(db, name="HLK Hagen – Hamm"):
    group = db.query(ProjectGroup).filter_by(short_name="HLK").one_or_none()
    if group is None:
        group = ProjectGroup(
            name="Hochleistungskorridorsanierung", short_name="HLK", color="#000000",
            assumed_build_months=6,
        )
        db.add(group)
    project = Project(name=name, is_draft=False)
    project.project_groups = [group]
    db.add(project)
    db.commit()
    return project


def _step(view, phase):
    return next(s for s in view["forecast"]["next_steps"] if s["phase"] == phase)


def test_year_observation_feeds_an_assumed_commissioning(mcp_client, admin_token, db_session):
    project = _hlk_project(db_session)
    view = _payload(
        _call(
            mcp_client,
            admin_token,
            "add_progress_observation",
            {
                "project_id": project.id,
                "track": "MAIN",
                "asserted_state": "BAU",
                "observed_date": "2028-05-17",
                "date_precision": "YEAR",
                "is_expected": True,
                "source_type": "MEDIEN",
            },
        )
    )
    [obs] = view["observations"]
    # YEAR is stored as 1 Jan and never shown as a day.
    assert (obs["observed_date"], obs["date_precision"], obs["date_text"]) == ("2028-01-01", "YEAR", "2028")
    bau, ibn = _step(view, "BAU"), _step(view, "IN_BETRIEB")
    assert (bau["date_precision"], bau["date_text"]) == ("YEAR", "2028")
    assert (ibn["source"], ibn["date_precision"], ibn["date_text"]) == (
        "Annahme",
        "ASSUMED",
        "ca. 07/2028 (Annahme)",
    )
    assert ibn["derivation"] == "Annahme: 6 Monate Bauzeit ab Baubeginn 2028 (Manuell)"

    progress = db_session.query(ProjectProgress).filter_by(project_id=project.id).one()
    db_session.refresh(progress)
    assert (progress.construction_start_date, progress.construction_start_precision) == (date(2028, 1, 1), "YEAR")
    assert (progress.commissioning_date, progress.commissioning_precision) == (date(2028, 7, 1), "ASSUMED")


def test_default_precision_is_exact(mcp_client, admin_token, db_session):
    project = _hlk_project(db_session)
    view = _payload(
        _call(
            mcp_client,
            admin_token,
            "add_progress_observation",
            {"project_id": project.id, "track": "MAIN", "asserted_state": "BAU", "observed_date": "2026-02-06"},
        )
    )
    assert view["observations"][0]["date_precision"] == "EXACT"
    assert view["observations"][0]["date_text"] == "06.02.2026"


def test_update_observation_sets_precision_in_place(mcp_client, admin_token, db_session):
    project = _hlk_project(db_session)
    obs = ProgressObservation(
        project_id=project.id, source_type="MEDIEN", track="MAIN", asserted_state="BAU",
        observed_date=date(2032, 1, 1), is_expected=True, note="nicht in der Reihung 2027–2031",
    )
    db_session.add(obs)
    db_session.commit()

    view = _payload(
        _call(
            mcp_client,
            admin_token,
            "update_progress_observation",
            {
                "project_id": project.id,
                "observation_id": obs.id,
                "date_precision": "NOT_BEFORE",
                "date_label": "Priorisierung 2027 offen",
            },
        )
    )
    [row] = view["observations"]
    assert row["id"] == obs.id  # changed in place, not re-created
    assert row["date_text"] == "nach 2031 – Priorisierung 2027 offen"
    assert row["note"] == "nicht in der Reihung 2027–2031"
    ibn = _step(view, "IN_BETRIEB")
    assert (ibn["date_precision"], ibn["date_text"]) == ("NOT_BEFORE", "frühestens 07/2032")

    [entry] = db_session.query(ChangeLog).filter_by(project_id=project.id, action="UPDATE").one().entries
    assert "01.01.2032" in entry.old_value
    assert "nach 2031 – Priorisierung 2027 offen" in entry.new_value

    cleared = _payload(
        _call(
            mcp_client,
            admin_token,
            "update_progress_observation",
            {"project_id": project.id, "observation_id": obs.id, "clear_date_label": True},
        )
    )
    assert cleared["observations"][0]["date_text"] == "nach 2031"


def test_derived_observation_cannot_be_updated(mcp_client, admin_token, db_session):
    project = _hlk_project(db_session)
    derived = ProgressObservation(
        project_id=project.id, source_type="VIB", track="MAIN", asserted_state="BAU", is_derived=True
    )
    db_session.add(derived)
    db_session.commit()
    result = _call(
        mcp_client,
        admin_token,
        "update_progress_observation",
        {"project_id": project.id, "observation_id": derived.id, "date_precision": "YEAR"},
    )
    assert result["isError"] is True
    assert "Abgeleitete" in result["content"][0]["text"]


def _seed_dates(db):
    """One project per case of the filter „Bau 2028–2030“."""
    cases = {
        "exact-2029": (date(2029, 3, 1), "EXACT"),
        "year-2028": (date(2028, 1, 1), "YEAR"),
        "year-2031": (date(2031, 1, 1), "YEAR"),
        "month-12-2027": (date(2027, 12, 1), "MONTH"),
        "not-before-2029": (date(2029, 1, 1), "NOT_BEFORE"),
        "assumed-2030": (date(2030, 6, 1), "ASSUMED"),
        "no-date": (None, None),
    }
    for name, (value, precision) in cases.items():
        project = Project(name=name, is_draft=False)
        db.add(project)
        db.flush()
        db.add(
            ProjectProgress(
                project_id=project.id,
                construction_start_date=value,
                construction_start_precision=precision,
            )
        )
    db.commit()


def _names(result):
    return sorted(p["name"] for p in _payload(result)["projects"])


def test_construction_period_filter_excludes_lower_bounds(mcp_client, admin_token, db_session):
    _seed_dates(db_session)
    result = _call(
        mcp_client,
        admin_token,
        "list_projects",
        {
            "filters": [
                {"field": "construction_start", "op": "gte", "value": "2028-03-01"},
                {"field": "construction_start", "op": "lte", "value": "2030-12-31"},
            ]
        },
    )
    assert _names(result) == ["assumed-2030", "exact-2029", "year-2028"]


def test_date_open_filter_and_list_output(mcp_client, admin_token, db_session):
    _seed_dates(db_session)
    payload = _payload(_call(mcp_client, admin_token, "list_projects", {"date_open": True}))
    [entry] = payload["projects"]
    assert entry["name"] == "not-before-2029"
    assert entry["construction_start"] == {"date": "2029-01-01", "precision": "NOT_BEFORE", "text": "nach 2028"}
    assert entry["commissioning"] is None

    rest = _call(mcp_client, admin_token, "list_projects", {"date_open": False})
    assert "not-before-2029" not in _names(rest)
    assert "no-date" in _names(rest)
