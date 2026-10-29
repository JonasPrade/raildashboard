"""Sammel-FinVe year comparison (docs/features/feature-haushalt-import.md →
„Jahresvergleich“): per Haushalt edition new / kept / dropped projects, the
editions listing a project, and the planning-state observation dated by the
first listing instead of the agreement's conclusion year."""

from __future__ import annotations

from datetime import date

from dashboard_backend.crud.projects.progress import recompute_progress
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.projects.budget import Budget
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project


def _seed(db):
    old = Project(name="ABS Alt", is_draft=False)
    stays = Project(name="NBS Bleibt", is_draft=False)
    new = Project(name="NBS Neu", is_draft=False)
    sammel = Finve(id=763, name="SV Lph. 1/2 A", starting_year=2012, is_sammel_finve=True)
    db.add_all([old, stays, new, sammel])
    db.flush()
    db.add_all([Budget(budget_year=y, fin_ve=sammel.id) for y in (2025, 2026, 2027)])
    db.add_all(
        [
            FinveToProject(project_id=old.id, finve_id=sammel.id, haushalt_year=2025),
            FinveToProject(project_id=stays.id, finve_id=sammel.id, haushalt_year=2025),
            FinveToProject(project_id=stays.id, finve_id=sammel.id, haushalt_year=2026),
            FinveToProject(project_id=stays.id, finve_id=sammel.id, haushalt_year=2027),
            FinveToProject(project_id=new.id, finve_id=sammel.id, haushalt_year=2026),
            FinveToProject(project_id=new.id, finve_id=sammel.id, haushalt_year=2027),
        ]
    )
    db.commit()
    return old, stays, new


def _names(refs):
    return [r["name"] for r in refs]


def test_sammel_years_diff_per_edition(client, db_session):
    _seed(db_session)
    res = client.get("/api/v1/finves/763/sammel-years")
    assert res.status_code == 200
    body = res.json()
    assert body["starting_year"] == 2012
    years = {y["year"]: y for y in body["years"]}
    assert sorted(years) == [2025, 2026, 2027]
    assert years[2025]["previous_year"] is None
    assert _names(years[2025]["kept"]) == ["ABS Alt", "NBS Bleibt"]
    assert _names(years[2026]["added"]) == ["NBS Neu"]
    assert _names(years[2026]["kept"]) == ["NBS Bleibt"]
    assert _names(years[2026]["removed"]) == ["ABS Alt"]
    assert years[2027]["added"] == [] and years[2027]["removed"] == []


def test_sammel_years_404(client):
    assert client.get("/api/v1/finves/999999/sammel-years").status_code == 404


def test_project_finves_carry_listing_years(client, db_session):
    _, _, new = _seed(db_session)
    res = client.get(f"/api/v1/projects/{new.id}/finves")
    assert res.status_code == 200
    (finve,) = res.json()
    assert finve["haushalt_years"] == [2026, 2027]
    assert finve["first_edition_year"] == 2025
    assert finve["listing_label"] == "Haushalt 2026–2027"


def test_progress_observation_dated_by_first_listing(db_session):
    old, _, new = _seed(db_session)
    recompute_progress(db_session, new.id)
    recompute_progress(db_session, old.id)
    obs_new = db_session.query(ProgressObservation).filter_by(project_id=new.id, finve_id=763).one()
    assert obs_new.observed_date == date(2026, 1, 1)
    assert "Haushalt 2026–2027" in obs_new.note
    obs_old = db_session.query(ProgressObservation).filter_by(project_id=old.id, finve_id=763).one()
    assert obs_old.observed_date == date(2025, 1, 1)
    assert "ggf. früher" in obs_old.note
