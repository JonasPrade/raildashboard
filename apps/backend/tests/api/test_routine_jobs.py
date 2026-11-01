"""Scheduled routine jobs (docs/features/feature-routine-abrufe.md, #340).

One test per acceptance criterion: the timetable, the Bauportal task with its
run record and the two observation dates, the recompute of changed projects,
the lock (button against schedule), retries on network errors only, the
global switch, the status block for /admin/system and the „Zeitplan“ marker
of scheduled parliament runs.
"""

from __future__ import annotations

import urllib.error
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest

import dashboard_backend.tasks.bauportal as bauportal_tasks
import dashboard_backend.tasks.parliament as parliament_tasks
import dashboard_backend.tasks.progress as progress_tasks
import dashboard_backend.tasks.routine as routine_tasks
from dashboard_backend.celery_app import celery_app
from dashboard_backend.core.config import settings
from dashboard_backend.models.parliament import ParliamentImportRun
from dashboard_backend.models.projects.bauportal_status import BauportalStatus
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.routine_job_run import RoutineJobRun
from dashboard_backend.schedule import ROUTINE_JOBS, ROUTINE_JOBS_BY_KEY, build_beat_schedule
from dashboard_backend.schemas.users import UserRole
from dashboard_backend.services import job_lock, routine_jobs
from dashboard_backend.services.exceptions import TransientFetchError
from dashboard_backend.services.parliament_import import AbgeordnetenwatchClient
from tests.api.conftest import basic_auth_header

BERLIN = ZoneInfo("Europe/Berlin")
# The repo root's docs/ — absent in the docker test stage (context apps/backend,
# copied to /app), so look upwards instead of assuming a depth.
FEATURE_DOC = next(
    (
        parent / "docs" / "features" / "feature-routine-abrufe.md"
        for parent in Path(__file__).resolve().parents
        if (parent / "docs" / "features").is_dir()
    ),
    Path("/nonexistent/feature-routine-abrufe.md"),
)

# The table E2 of the feature doc: job → (weekday or None = daily, hour, minute).
EXPECTED_TIMETABLE = {
    "bauportal": (None, 2, 40),
    "parliament": (0, 2, 50),  # Monday
    "progress_recompute": (6, 3, 10),  # Sunday
}


# --- helpers -------------------------------------------------------------------


class _TaskSession:
    """The test's session handed to a task: ``close`` must not end the test's
    transaction, and ``rollback`` must not roll back the outer one (the run
    row written before the failure would vanish with it)."""

    def __init__(self, session):
        self._session = session

    def close(self):
        pass

    def rollback(self):
        self._session.expire_all()

    def __getattr__(self, name):
        return getattr(self._session, name)


@pytest.fixture()
def task_db(db_session, monkeypatch):
    factory = lambda: _TaskSession(db_session)  # noqa: E731
    monkeypatch.setattr(bauportal_tasks, "SessionLocal", factory)
    monkeypatch.setattr(parliament_tasks, "Session", factory)
    monkeypatch.setattr(progress_tasks, "Session", factory)
    monkeypatch.setattr(routine_tasks, "Session", factory)
    return db_session


def _record(bauportal_id: int, title: str, status: str) -> dict:
    return {
        "id": bauportal_id,
        "shorttitle": title,
        "icon_title": status,
        "projecttime": "2025 – 2027",
        "url": f"https://bau.example/{bauportal_id}",
        "lat": 51.0,
        "lng": 10.0,
    }


@pytest.fixture()
def bauportal_http(monkeypatch):
    """Mocked Bauportal API: ``responses`` is a list of httpx.Response or
    exceptions, consumed one per request (the last one repeats)."""
    state = {"responses": [], "calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        item = state["responses"][min(state["calls"], len(state["responses"])) - 1]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(bauportal_tasks, "_transport", httpx.MockTransport(handler))
    return state


@pytest.fixture()
def no_recompute(monkeypatch):
    import dashboard_backend.crud._importer_common as common

    calls: list[list[int]] = []
    monkeypatch.setattr(common, "recompute_for", lambda db, ids: calls.append(sorted(ids)))
    return calls


@pytest.fixture()
def routine_enabled(monkeypatch):
    monkeypatch.setattr(settings, "routine_jobs_enabled", True)


# --- timetable -----------------------------------------------------------------


def test_beat_schedule_matches_the_feature_doc():
    assert set(ROUTINE_JOBS_BY_KEY) == set(EXPECTED_TIMETABLE)
    schedule = build_beat_schedule(True)
    assert len(schedule) == 3
    for job in ROUTINE_JOBS:
        weekday, hour, minute = EXPECTED_TIMETABLE[job.key]
        assert (job.weekday, job.hour, job.minute) == (weekday, hour, minute)
        entry = schedule[f"routine-{job.key}"]
        assert entry["task"] == job.task_name
        # The name resolves to a registered wrapper task. (Not via
        # celery_app.tasks: that finalizes the app and upsets other tests.)
        wrapper = getattr(routine_tasks, entry["task"].rsplit(".", 1)[1])
        assert wrapper.name == entry["task"]
        cron = entry["schedule"]
        assert cron.hour == {hour} and cron.minute == {minute}
        # crontab's day_of_week: Sunday = 0, Monday = 1.
        expected_dow = set(range(7)) if weekday is None else {(weekday + 1) % 7}
        assert cron.day_of_week == expected_dow
    # All before the Borg backup at 04:05.
    assert all((j.hour, j.minute) < (4, 5) for j in ROUTINE_JOBS)


def test_feature_doc_names_the_same_times():
    if not FEATURE_DOC.exists():  # the docker test stage only has apps/backend
        pytest.skip("feature doc not in the build context")
    text = FEATURE_DOC.read_text()
    assert "Bauportal täglich 02:40, Abgeordnete montags 02:50, Neuberechnung sonntags 03:10" in text


def test_celery_reads_the_schedule_in_berlin_time():
    assert celery_app.conf.timezone == "Europe/Berlin"
    assert celery_app.conf.beat_schedule_filename.startswith("/tmp/")


def test_switched_off_the_schedule_is_empty():
    assert build_beat_schedule(False) == {}
    # The test suite runs with ROUTINE_JOBS_ENABLED=false (conftest.py).
    assert settings.routine_jobs_enabled is False
    assert celery_app.conf.beat_schedule == {}


def test_next_run_respects_weekday_and_time():
    saturday_noon = datetime(2026, 10, 31, 12, 0, tzinfo=BERLIN)
    bauportal = ROUTINE_JOBS_BY_KEY["bauportal"]
    assert bauportal.next_run(saturday_noon) == datetime(2026, 11, 1, 2, 40, tzinfo=BERLIN)
    assert ROUTINE_JOBS_BY_KEY["progress_recompute"].next_run(saturday_noon) == datetime(
        2026, 11, 1, 3, 10, tzinfo=BERLIN
    )
    assert ROUTINE_JOBS_BY_KEY["parliament"].next_run(saturday_noon) == datetime(
        2026, 11, 2, 2, 50, tzinfo=BERLIN
    )
    # Exactly at the slot → the next one.
    at_slot = datetime(2026, 11, 1, 2, 40, tzinfo=BERLIN)
    assert bauportal.next_run(at_slot) == datetime(2026, 11, 2, 2, 40, tzinfo=BERLIN)


# --- Bauportal task: run record, dates, recompute --------------------------------


def test_bauportal_run_writes_a_run_row_and_both_dates(task_db, bauportal_http, no_recompute):
    project = Project(name="ABS Oldenburg – Wilhelmshaven")
    task_db.add(project)
    task_db.flush()
    old = datetime(2026, 7, 15)
    confirmed = BauportalStatus(
        bauportal_id=1, shorttitle="ABS Oldenburg-Wilhelmshaven",
        status_raw="Projekt in der Planungsphase", fetched_at=old,
        status_changed_at=old, last_seen_at=old, project_id=project.id, confirmed=True,
    )
    unchanged = BauportalStatus(
        bauportal_id=2, shorttitle="Ölweiche Nord", status_raw="Projekt in der Planungsphase",
        fetched_at=old, status_changed_at=old, last_seen_at=old,
    )
    task_db.add_all([confirmed, unchanged])
    task_db.commit()

    bauportal_http["responses"] = [
        httpx.Response(
            200,
            json=[
                _record(1, "ABS Oldenburg-Wilhelmshaven", "Projekt in der Bauphase"),
                _record(2, "Ölweiche Nord", "Projekt in der Planungsphase"),
                _record(3, "Neu Bahnhof X", "Projekt in der Bauphase"),
            ],
        )
    ]
    result = bauportal_tasks.refresh_bauportal.apply(kwargs={"user_id": None})
    assert result.successful(), result.traceback
    stats = result.result
    assert (stats["created"], stats["updated"], stats["status_changed"]) == (1, 2, 1)
    assert stats["recomputed_projects"] == 1
    assert no_recompute == [[project.id]]

    task_db.expire_all()
    changed = task_db.query(BauportalStatus).filter_by(bauportal_id=1).one()
    same = task_db.query(BauportalStatus).filter_by(bauportal_id=2).one()
    new = task_db.query(BauportalStatus).filter_by(bauportal_id=3).one()
    assert changed.status_changed_at > old and changed.last_seen_at > old
    assert same.status_changed_at == old  # no status change → no new observation date
    assert same.last_seen_at > old  # but seen again („Stand“)
    assert new.status_changed_at is not None and new.last_seen_at is not None
    assert changed.fetched_at == old  # kept until the contract release

    run = task_db.query(RoutineJobRun).one()
    assert (run.job, run.status, run.triggered_by_user_id) == ("bauportal", "success", None)
    assert run.finished_at is not None and run.stats["fetched"] == 3


def test_changed_status_recomputes_with_the_change_date(task_db, bauportal_http):
    project = Project(name="ABS Oldenburg – Wilhelmshaven")
    task_db.add(project)
    task_db.flush()
    old = datetime(2026, 7, 15)
    task_db.add(
        BauportalStatus(
            bauportal_id=1, shorttitle="ABS Oldenburg-Wilhelmshaven",
            status_raw="Projekt in der Planungsphase", fetched_at=old,
            status_changed_at=old, last_seen_at=old, project_id=project.id, confirmed=True,
        )
    )
    task_db.commit()
    bauportal_http["responses"] = [
        httpx.Response(200, json=[_record(1, "ABS Oldenburg-Wilhelmshaven", "Projekt in der Bauphase")])
    ]
    result = bauportal_tasks.refresh_bauportal.apply()
    assert result.successful(), result.traceback

    observation = (
        task_db.query(ProgressObservation)
        .filter_by(project_id=project.id, source_type="BAUPORTAL")
        .one()
    )
    assert observation.asserted_state == "BAU"
    # The day of the status change, not the first fetch in July.
    assert observation.observed_date == datetime.utcnow().date()


def test_derived_observation_uses_status_changed_at_not_last_seen(task_db):
    from dashboard_backend.crud.projects.progress import recompute_progress

    project = Project(name="Röblingen")
    task_db.add(project)
    task_db.flush()
    task_db.add(
        BauportalStatus(
            bauportal_id=9, shorttitle="Röblingen", status_raw="Projekt in der Bauphase",
            fetched_at=datetime(2026, 1, 2), status_changed_at=datetime(2026, 3, 4),
            last_seen_at=datetime(2026, 10, 31), project_id=project.id, confirmed=True,
        )
    )
    task_db.commit()
    recompute_progress(task_db, project.id)
    observation = task_db.query(ProgressObservation).filter_by(project_id=project.id).one()
    assert observation.observed_date == date(2026, 3, 4)


def test_project_page_entry_carries_last_seen_at(client, db_session):
    project = Project(name="Röblingen")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        BauportalStatus(
            bauportal_id=9, shorttitle="Röblingen", status_raw="Projekt in der Bauphase",
            fetched_at=datetime(2026, 1, 2), status_changed_at=datetime(2026, 3, 4),
            last_seen_at=datetime(2026, 10, 31), project_id=project.id, confirmed=True,
        )
    )
    db_session.commit()
    body = client.get(f"/api/v1/projects/{project.id}/bauportal").json()
    assert body[0]["last_seen_at"].startswith("2026-10-31")
    assert body[0]["status_changed_at"].startswith("2026-03-04")


# --- retries --------------------------------------------------------------------


def test_network_errors_are_retried_three_times(task_db, bauportal_http, no_recompute):
    bauportal_http["responses"] = [httpx.ConnectError("no route to host")]
    result = bauportal_tasks.refresh_bauportal.apply()
    assert result.failed()
    assert bauportal_http["calls"] == 4  # first attempt + 3 retries
    run = task_db.query(RoutineJobRun).one()  # one row across all attempts
    assert run.status == "error" and "no route to host" in run.error


def test_server_error_then_success_ends_in_one_successful_run(task_db, bauportal_http, no_recompute):
    bauportal_http["responses"] = [
        httpx.Response(503),
        httpx.Response(502),
        httpx.Response(200, json=[_record(1, "Bahnhof Y", "Projekt in der Bauphase")]),
    ]
    result = bauportal_tasks.refresh_bauportal.apply()
    assert result.successful(), result.traceback
    assert bauportal_http["calls"] == 3
    run = task_db.query(RoutineJobRun).one()
    assert run.status == "success" and run.error is None


def test_data_errors_are_not_retried(task_db, bauportal_http, no_recompute):
    bauportal_http["responses"] = [httpx.Response(200, json={"unexpected": "shape"})]
    result = bauportal_tasks.refresh_bauportal.apply()
    assert result.failed()
    assert bauportal_http["calls"] == 1
    run = task_db.query(RoutineJobRun).one()
    assert run.status == "error" and "Unexpected Bauportal response" in run.error


def test_client_errors_are_not_retried(task_db, bauportal_http, no_recompute):
    bauportal_http["responses"] = [httpx.Response(404)]
    result = bauportal_tasks.refresh_bauportal.apply()
    assert result.failed()
    assert bauportal_http["calls"] == 1


def test_retry_backoff_is_1_4_16_minutes():
    assert [routine_jobs.retry_countdown(n) for n in range(3)] == [60, 240, 960]


def test_failed_run_releases_the_lock(task_db, bauportal_http, no_recompute):
    token = job_lock.acquire("bauportal")
    bauportal_http["responses"] = [httpx.Response(200, json={"bad": True})]
    bauportal_tasks.refresh_bauportal.apply(kwargs={"lock_token": token})
    assert job_lock.held_since("bauportal") is None


def test_abgeordnetenwatch_network_error_is_transient(monkeypatch):
    def boom(url, timeout):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    monkeypatch.setattr("time.sleep", lambda s: None)
    with pytest.raises(TransientFetchError):
        AbgeordnetenwatchClient(retries=2).get("/parliament-periods")


def test_abgeordnetenwatch_client_error_is_not_transient(monkeypatch):
    def not_found(url, timeout):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", not_found)
    with pytest.raises(RuntimeError) as info:
        AbgeordnetenwatchClient(retries=3).get("/parliament-periods")
    assert not isinstance(info.value, TransientFetchError)
    assert not routine_jobs.is_transient(info.value)


def test_parliament_task_retries_network_errors(task_db, monkeypatch):
    calls = []

    def failing_import(db, **kwargs):
        calls.append(kwargs)
        run = ParliamentImportRun(kind="politicians", status="error", error="timed out")
        db.add(run)
        db.commit()
        raise TransientFetchError("abgeordnetenwatch request failed")

    monkeypatch.setattr(parliament_tasks, "import_politicians", failing_import)
    result = parliament_tasks.refresh_parliament_data.apply()
    assert result.failed()
    assert len(calls) == 4
    assert all(c["user_id"] is None for c in calls)


# --- lock: button against schedule ---------------------------------------------------


def test_button_gets_409_while_a_scheduled_run_holds_the_lock(
    client, create_user, task_db, routine_enabled, monkeypatch
):
    create_user("redakteur", "pw", UserRole.editor)
    queued = []

    class FakeTask:
        id = "scheduled-1"

    monkeypatch.setattr(
        bauportal_tasks.refresh_bauportal, "delay", lambda **kw: queued.append(kw) or FakeTask()
    )
    outcome = routine_jobs.start_scheduled(task_db, "bauportal")
    assert outcome["status"] == "queued"
    assert queued[0]["user_id"] is None

    resp = client.post("/api/v1/import/bauportal/fetch", headers=basic_auth_header("redakteur", "pw"))
    assert resp.status_code == 409
    assert resp.json()["detail"].startswith("Läuft bereits seit ")
    assert len(queued) == 1


def test_schedule_is_skipped_and_recorded_while_the_button_run_holds_the_lock(
    client, create_user, task_db, routine_enabled, monkeypatch
):
    create_user("redakteurin", "pw", UserRole.editor)
    queued = []

    class FakeTask:
        id = "button-1"

    monkeypatch.setattr(
        bauportal_tasks.refresh_bauportal, "delay", lambda **kw: queued.append(kw) or FakeTask()
    )
    resp = client.post("/api/v1/import/bauportal/fetch", headers=basic_auth_header("redakteurin", "pw"))
    assert resp.status_code == 202

    outcome = routine_tasks.scheduled_bauportal.apply().result
    assert outcome["status"] == "skipped"
    assert len(queued) == 1
    skipped = task_db.query(RoutineJobRun).filter_by(status="skipped").one()
    assert skipped.job == "bauportal" and skipped.error.startswith("Übersprungen")


def test_parliament_and_recompute_buttons_are_locked_too(client, create_user, monkeypatch):
    create_user("chefin", "pw", UserRole.admin)

    class FakeTask:
        id = "t"

    monkeypatch.setattr(parliament_tasks.refresh_parliament_data, "delay", lambda **kw: FakeTask())
    monkeypatch.setattr(progress_tasks.recompute_all_progress_task, "delay", lambda **kw: FakeTask())
    headers = basic_auth_header("chefin", "pw")
    job_lock.acquire("parliament")
    job_lock.acquire("progress_recompute")
    # parliament.import is granted per role; the admin role has every grant.
    assert client.post("/api/v1/parliament/import", headers=headers).status_code == 409
    assert client.post("/api/v1/admin/progress-recompute", headers=headers).status_code == 409


def test_lock_release_needs_the_token():
    token = job_lock.acquire("bauportal")
    job_lock.release("bauportal", "someone-else")
    assert job_lock.held_since("bauportal") is not None
    with pytest.raises(job_lock.JobAlreadyRunning):
        job_lock.acquire("bauportal")
    job_lock.release("bauportal", token)
    assert job_lock.held_since("bauportal") is None


# --- global switch ------------------------------------------------------------------


def test_switched_off_the_wrapper_queues_nothing(task_db, monkeypatch):
    queued = []
    monkeypatch.setattr(
        bauportal_tasks.refresh_bauportal, "delay", lambda **kw: queued.append(kw)
    )
    outcome = routine_tasks.scheduled_bauportal.apply().result
    assert outcome["status"] == "disabled"
    assert queued == []
    assert job_lock.held_since("bauportal") is None


# --- recompute run record -----------------------------------------------------------


def test_recompute_writes_a_run_row(task_db, monkeypatch):
    monkeypatch.setattr(
        progress_tasks, "recompute_all_progress", lambda db, on_batch=None: {"projects": 0}
    )
    token = job_lock.acquire("progress_recompute")
    result = progress_tasks.recompute_all_progress_task.apply(kwargs={"lock_token": token})
    assert result.successful(), result.traceback
    run = task_db.query(RoutineJobRun).one()
    assert (run.job, run.status, run.stats) == ("progress_recompute", "success", {"projects": 0})
    assert job_lock.held_since("progress_recompute") is None


# --- status for /admin/system -------------------------------------------------------


def _status(client, create_user, name="admin-sys"):
    create_user(name, "pw", UserRole.admin)
    resp = client.get("/api/v1/system/routine-jobs", headers=basic_auth_header(name, "pw"))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_status_requires_settings_manage(client, create_user):
    assert client.get("/api/v1/system/routine-jobs").status_code == 401
    create_user("red", "pw", UserRole.editor)
    resp = client.get("/api/v1/system/routine-jobs", headers=basic_auth_header("red", "pw"))
    assert resp.status_code == 403


def test_status_lists_the_three_jobs_and_flags_the_switch(client, create_user):
    body = _status(client, create_user)
    assert body["enabled"] is False
    assert body["needs_attention"] is True  # „Zeitplan abgeschaltet“
    assert [j["key"] for j in body["jobs"]] == ["bauportal", "parliament", "progress_recompute"]
    assert body["jobs"][0]["schedule_label"] == "täglich 02:40 Uhr"
    assert body["jobs"][0]["next_run_at"] is None


def test_status_badge_rules(client, create_user, db_session, routine_enabled):
    now = datetime.utcnow()
    db_session.add_all(
        [
            RoutineJobRun(job="bauportal", status="success", started_at=now - timedelta(hours=3),
                          finished_at=now - timedelta(hours=3) + timedelta(seconds=12)),
            RoutineJobRun(job="progress_recompute", status="success",
                          started_at=now - timedelta(days=15), finished_at=now - timedelta(days=15)),
            ParliamentImportRun(kind="politicians", status="success",
                                started_at=now - timedelta(days=2), finished_at=now - timedelta(days=2)),
        ]
    )
    db_session.commit()
    body = _status(client, create_user)
    jobs = {j["key"]: j for j in body["jobs"]}
    assert jobs["bauportal"]["needs_attention"] is False
    assert jobs["bauportal"]["last_run"]["duration_seconds"] == pytest.approx(12)
    assert jobs["bauportal"]["last_run"]["triggered_by_user_id"] is None
    assert jobs["bauportal"]["next_run_at"] is not None
    assert jobs["parliament"]["needs_attention"] is False
    # 15 days > twice the weekly interval.
    assert jobs["progress_recompute"]["overdue"] is True
    assert body["needs_attention"] is True

    db_session.add(RoutineJobRun(job="bauportal", status="error", error="boom", started_at=now))
    db_session.commit()
    jobs = {j["key"]: j for j in _status(client, create_user, "admin-sys2")["jobs"]}
    assert jobs["bauportal"]["needs_attention"] is True
    assert jobs["bauportal"]["last_run"]["error"] == "boom"


def test_scheduled_parliament_runs_show_as_schedule(client, create_user, db_session):
    user = create_user("knopf", "pw", UserRole.admin)
    now = datetime.utcnow()
    db_session.add_all(
        [
            ParliamentImportRun(kind="politicians", status="success", triggered_by_user_id=user.id,
                                started_at=now - timedelta(days=8), finished_at=now - timedelta(days=8)),
            ParliamentImportRun(kind="politicians", status="success", triggered_by_user_id=None,
                                started_at=now - timedelta(days=1), finished_at=now - timedelta(days=1)),
        ]
    )
    db_session.commit()
    status = client.get("/api/v1/parliament/status", headers=basic_auth_header("knopf", "pw")).json()
    assert status["last_politician_import"]["triggered_by_user_id"] is None
    assert status["last_politician_import"]["triggered_by_username"] is None

    jobs = {j["key"]: j for j in _status(client, create_user)["jobs"]}
    assert jobs["parliament"]["last_run"]["triggered_by_user_id"] is None


def test_skipped_parliament_run_shows_in_the_status(client, create_user, db_session):
    now = datetime.utcnow()
    db_session.add(ParliamentImportRun(kind="politicians", status="success",
                                       started_at=now - timedelta(days=7), finished_at=now - timedelta(days=7)))
    db_session.add(RoutineJobRun(job="parliament", status="skipped", started_at=now,
                                 finished_at=now, error="Übersprungen: Der Job lief bereits."))
    db_session.commit()
    jobs = {j["key"]: j for j in _status(client, create_user)["jobs"]}
    assert jobs["parliament"]["last_run"]["status"] == "skipped"
    assert jobs["parliament"]["last_success_at"] is not None


def test_running_since_comes_from_the_lock(client, create_user):
    job_lock.acquire("bauportal")
    jobs = {j["key"]: j for j in _status(client, create_user)["jobs"]}
    since = datetime.fromisoformat(jobs["bauportal"]["running_since"])
    assert datetime.now(timezone.utc) - since < timedelta(minutes=1)
    assert jobs["parliament"]["running_since"] is None


def test_healthz_does_not_depend_on_the_scheduler():
    from dashboard_backend.api.v1.endpoints import health

    source = Path(health.__file__).read_text()
    assert "routine" not in source and "beat" not in source
