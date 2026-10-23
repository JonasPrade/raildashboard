"""Full planning-state resync (crud.projects.progress.recompute_all_progress)
and its admin endpoint POST /api/v1/admin/progress-recompute."""

from __future__ import annotations

from datetime import date, datetime

from dashboard_backend.crud.projects.progress import recompute_all_progress
from dashboard_backend.models.gvfg import GvfgEntry, GvfgProgram
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def _seed(db):
    """Two projects whose cache is fresh but predates the GVFG source: the
    lazy resync would leave both "unknown" for another day."""
    tram = Project(name="Straßenbahn Mainz-Finthen")
    empty = Project(name="Projekt ohne Quellen")
    db.add_all([tram, empty])
    db.flush()
    program = GvfgProgram(
        year_from=2025, year_to=2029, title="GVFG 2025–2029", stand=date(2025, 7, 18), periods=[]
    )
    entry = GvfgEntry(
        program=program, key="07 G 7050_A", key_raw="07 G 7050 _A", land="Rheinland-Pfalz",
        kind="kommunal", part="finanzrelevant", name="Mainz-Finthen", lph="9", commissioning_actual=2024,
    )
    entry.projects.append(tram)
    db.add(program)
    for project in (tram, empty):
        db.add(
            ProjectProgress(
                project_id=project.id,
                lifecycle_status="AKTIV",
                computed_phase="NICHT_GESTARTET",
                computed_confidence=0.0,
                computed_at=datetime.utcnow(),
            )
        )
    db.commit()
    return tram, empty


def test_recompute_all_reaches_projects_the_lazy_resync_skips(db_session):
    tram, empty = _seed(db_session)
    batches = []

    stats = recompute_all_progress(
        db_session, date(2026, 10, 23), batch_size=1, on_batch=lambda done, total: batches.append((done, total))
    )

    assert stats == {"projects": 2, "known_before": 0, "known_after": 1, "phase_changed": 1}
    assert batches == [(1, 2), (2, 2)]
    tram_progress = db_session.query(ProjectProgress).filter_by(project_id=tram.id).one()
    assert tram_progress.computed_phase == "IN_BETRIEB"
    assert tram_progress.computed_confidence > 0
    observation = db_session.query(ProgressObservation).filter_by(project_id=tram.id).one()
    assert (observation.source_type, observation.is_derived) == ("GVFG", True)
    empty_progress = db_session.query(ProjectProgress).filter_by(project_id=empty.id).one()
    assert (empty_progress.computed_phase, empty_progress.computed_confidence) == ("NICHT_GESTARTET", 0)


def test_recompute_all_is_idempotent(db_session):
    _seed(db_session)
    recompute_all_progress(db_session, date(2026, 10, 23))
    stats = recompute_all_progress(db_session, date(2026, 10, 23))
    assert stats == {"projects": 2, "known_before": 1, "known_after": 1, "phase_changed": 0}
    assert db_session.query(ProgressObservation).count() == 1


def test_recompute_endpoint_is_gated(client, create_user):
    assert client.post("/api/v1/admin/progress-recompute").status_code == 401
    create_user("leser", "pw", UserRole.viewer)
    resp = client.post("/api/v1/admin/progress-recompute", headers=basic_auth_header("leser", "pw"))
    assert resp.status_code == 403


def test_recompute_endpoint_starts_a_task(client, create_user, monkeypatch):
    create_user("verwalterin", "pw", UserRole.admin)

    import dashboard_backend.tasks.progress as progress_tasks

    class FakeTask:
        id = "task-456"

    monkeypatch.setattr(progress_tasks.recompute_all_progress_task, "delay", lambda: FakeTask())
    resp = client.post("/api/v1/admin/progress-recompute", headers=basic_auth_header("verwalterin", "pw"))
    assert resp.status_code == 202
    assert resp.json() == {"task_id": "task-456"}
