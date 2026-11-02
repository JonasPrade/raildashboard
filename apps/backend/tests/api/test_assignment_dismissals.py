"""„Dauerhaft ignorieren“ in Offene Zuordnungen
(docs/features/feature-unassigned-assignments.md): an ignored FinVe, VIB entry,
GVFG Vorhaben or Infraplan row drops out of its open list, shows up in the
ignored list and comes back after a restore."""

from __future__ import annotations

from dashboard_backend.models.gvfg import GvfgEntry, GvfgProgram
from dashboard_backend.models.infraplan import InfraplanEntry, InfraplanReport
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.vib.vib_entry import VibEntry
from dashboard_backend.models.vib.vib_report import VibReport
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header

AUTH = basic_auth_header("editor_dis", "pass")


def _seed(db):
    finve = Finve(id=700001, name="Ausrüstung Leit- und Sicherungstechnik", starting_year=2024)
    vib_report = VibReport(year=2024)
    program = GvfgProgram(year_from=2025, year_to=2029, title="2025", periods=[])
    infraplan = InfraplanReport(year=2026)
    db.add_all([finve, vib_report, program, infraplan])
    db.flush()
    vib = VibEntry(vib_report_id=vib_report.id, vib_name_raw="Lärmsanierung", category="laufend")
    gvfg = GvfgEntry(program=program, key="08 B 1_S", key_raw="08 B 1_S", land="BW", kind="bus",
                     part="finanzrelevant", name="Busbahnhof")
    row = InfraplanEntry(report_id=infraplan.id, section="BP_A", lfd_nr=7, massnahme="Bahnhofsprogramm")
    db.add_all([vib, gvfg, row])
    db.commit()
    return {"finve": finve.id, "vib": vib.id, "gvfg": gvfg.id, "infraplan": row.id}


LISTS = {
    "finve": "/api/v1/admin/unassigned-finves",
    "vib": "/api/v1/admin/unassigned-vib-entries",
    "gvfg": "/api/v1/admin/unassigned-gvfg-entries",
    "infraplan": "/api/v1/admin/unassigned-infraplan-entries",
}


def _open_ids(client, kind):
    resp = client.get(LISTS[kind], headers=AUTH)
    assert resp.status_code == 200, resp.text
    return [row["id"] for row in resp.json()]


def test_dismiss_hides_and_restore_brings_back(client, db_session, create_user):
    create_user("editor_dis", "pass", UserRole.editor)
    ids = _seed(db_session)

    for kind, entry_id in ids.items():
        assert entry_id in _open_ids(client, kind)
        resp = client.put(
            f"/api/v1/admin/dismissed-assignments/{kind}/{entry_id}",
            json={"note": "kein Schienenprojekt"},
            headers=AUTH,
        )
        assert resp.status_code == 204, resp.text
        assert entry_id not in _open_ids(client, kind)

    dismissed = client.get("/api/v1/admin/dismissed-assignments", headers=AUTH).json()
    assert {(d["kind"], d["entry_id"]) for d in dismissed} == set(ids.items())
    by_kind = {d["kind"]: d for d in dismissed}
    assert by_kind["finve"]["label"] == "Ausrüstung Leit- und Sicherungstechnik"
    assert by_kind["infraplan"]["detail"] == "Infraplan 2026 · BP Teil A Nr. 7"
    assert by_kind["gvfg"]["note"] == "kein Schienenprojekt"
    assert by_kind["vib"]["dismissed_by"] == "editor_dis"

    for kind, entry_id in ids.items():
        resp = client.delete(f"/api/v1/admin/dismissed-assignments/{kind}/{entry_id}", headers=AUTH)
        assert resp.status_code == 204
        assert entry_id in _open_ids(client, kind)
    assert client.get("/api/v1/admin/dismissed-assignments", headers=AUTH).json() == []


def test_dismiss_is_idempotent_and_needs_an_existing_record(client, db_session, create_user):
    create_user("editor_dis", "pass", UserRole.editor)
    ids = _seed(db_session)
    url = f"/api/v1/admin/dismissed-assignments/finve/{ids['finve']}"
    assert client.put(url, headers=AUTH).status_code == 204
    assert client.put(url, json={"note": "Begründung nachgetragen"}, headers=AUTH).status_code == 204
    dismissed = client.get("/api/v1/admin/dismissed-assignments", headers=AUTH).json()
    assert len(dismissed) == 1
    assert dismissed[0]["note"] == "Begründung nachgetragen"

    assert client.put("/api/v1/admin/dismissed-assignments/finve/999999", headers=AUTH).status_code == 404
    assert client.put("/api/v1/admin/dismissed-assignments/foo/1", headers=AUTH).status_code == 422


def test_dismiss_requires_permission(client, db_session, create_user):
    create_user("viewer_dis", "pass", UserRole.viewer)
    ids = _seed(db_session)
    resp = client.put(
        f"/api/v1/admin/dismissed-assignments/finve/{ids['finve']}",
        headers=basic_auth_header("viewer_dis", "pass"),
    )
    assert resp.status_code == 403
    assert client.get("/api/v1/admin/dismissed-assignments").status_code == 401
