"""Tests for /api/v1/parliament/* and /api/v1/projects/{id}/constituencies.

Reading is public on purpose — the assignment is public information about
officeholders — while an import run is gated behind ``parliament.import``.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import dashboard_backend.api.deps as api_deps
from dashboard_backend.models.associations.project_to_constituency import (
    OVERLAP_KIND_LINE,
    OVERLAP_KIND_POINT,
    ProjectToConstituency,
)
from dashboard_backend.models.parliament import (
    Committee,
    CommitteeMembership,
    Constituency,
    IMPORT_KIND_POLITICIANS,
    IMPORT_STATUS_SUCCESS,
    Mandate,
    ParliamentImportRun,
    ParliamentPeriod,
    Politician,
)
from dashboard_backend.schemas.users import UserRole
from main import app
from tests.api.conftest import PROJECT_TABLE, basic_auth_header

PROJECT_ID = 4242


class FakeProject:
    """Stands in for the Project row — the table is PostGIS-only and absent here."""

    def __init__(self, project_id=PROJECT_ID, geojson='{"type": "FeatureCollection"}'):
        self.id = project_id
        self.name = "ABS Test"
        self.project_number = "2-042-V01"
        self.geojson_representation = geojson
        self.is_draft = False


@pytest.fixture()
def parliament_data(db_session):
    # A real row: the counting queries join ``project`` to skip drafts.
    db_session.execute(
        PROJECT_TABLE.insert().values(
            id=PROJECT_ID, name="ABS Test", project_number="2-042-V01", is_draft=False
        )
    )
    period = ParliamentPeriod(
        external_id=161, label="Bundestag 2025 - 2029", is_current=True
    )
    db_session.add(period)
    db_session.flush()

    offenbach = Constituency(
        parliament_period_id=period.id, number=182, name="Offenbach", state="Hessen"
    )
    flensburg = Constituency(
        parliament_period_id=period.id, number=1, name="Flensburg", state="Schleswig-Holstein"
    )
    empty = Constituency(
        parliament_period_id=period.id, number=42, name="Ohne Mandat", state="Hessen"
    )
    db_session.add_all([offenbach, flensburg, empty])
    db_session.flush()

    transport = Committee(
        external_id=900,
        parliament_period_id=period.id,
        key="verkehr",
        label="Verkehrsausschuss",
    )
    budget = Committee(
        external_id=901,
        parliament_period_id=period.id,
        key="haushalt",
        label="Haushaltsausschuss",
    )
    db_session.add_all([transport, budget])
    db_session.flush()

    chair = Politician(external_id=1, label="Tarek Al-Wazir", last_name="Al-Wazir")
    lister = Politician(external_id=2, label="Änne Beispiel", last_name="Beispiel")
    northern = Politician(external_id=3, label="Nord Licht", last_name="Licht")
    db_session.add_all([chair, lister, northern])
    db_session.flush()

    chair_mandate = Mandate(
        external_id=10,
        politician_id=chair.id,
        parliament_period_id=period.id,
        constituency_id=offenbach.id,
        mandate_type="constituency",
        is_direct_mandate=True,
        fraction_label="BÜNDNIS 90/DIE GRÜNEN",
    )
    list_mandate = Mandate(
        external_id=11,
        politician_id=lister.id,
        parliament_period_id=period.id,
        constituency_id=offenbach.id,
        mandate_type="list",
        is_direct_mandate=False,
        fraction_label="SPD",
    )
    north_mandate = Mandate(
        external_id=12,
        politician_id=northern.id,
        parliament_period_id=period.id,
        constituency_id=flensburg.id,
        mandate_type="list",
        is_direct_mandate=False,
        fraction_label="SPD",
    )
    db_session.add_all([chair_mandate, list_mandate, north_mandate])
    db_session.flush()

    db_session.add(
        CommitteeMembership(
            mandate_id=chair_mandate.id,
            committee_id=transport.id,
            role="chairperson",
            role_label="Vorsitz",
            role_rank=0,
        )
    )
    db_session.add_all(
        [
            ProjectToConstituency(
                project_id=PROJECT_ID,
                constituency_id=offenbach.id,
                length_km=51.0,
                share=0.94,
                overlap_kind=OVERLAP_KIND_LINE,
            ),
            ProjectToConstituency(
                project_id=PROJECT_ID,
                constituency_id=flensburg.id,
                length_km=3.0,
                share=0.06,
                overlap_kind=OVERLAP_KIND_LINE,
            ),
        ]
    )
    db_session.add(
        ParliamentImportRun(
            kind=IMPORT_KIND_POLITICIANS,
            status=IMPORT_STATUS_SUCCESS,
            started_at=datetime.utcnow() - timedelta(days=2),
            finished_at=datetime.utcnow() - timedelta(days=2),
            parliament_period_id=period.id,
            stats={"mandates": 3},
        )
    )
    db_session.commit()
    return {
        "period": period,
        "offenbach": offenbach,
        "flensburg": flensburg,
        "empty": empty,
        "chair_mandate": chair_mandate,
        "list_mandate": list_mandate,
    }


@pytest.fixture()
def project_override():
    app.dependency_overrides[api_deps.get_project_or_404] = lambda: FakeProject()
    yield
    app.dependency_overrides.pop(api_deps.get_project_or_404, None)


# --- project → constituencies -----------------------------------------------


def test_project_constituencies_are_public_and_sorted_by_kilometres(
    client, parliament_data, project_override
):
    resp = client.get(f"/api/v1/projects/{PROJECT_ID}/constituencies")
    assert resp.status_code == 200
    body = resp.json()

    assert body["has_geometry"] is True
    assert [c["number"] for c in body["constituencies"]] == [182, 1]
    assert body["constituencies"][0]["length_km"] == 51.0
    assert body["last_import"]["status"] == "success"


def test_direct_and_list_mandates_are_reported_separately(
    client, parliament_data, project_override
):
    body = client.get(f"/api/v1/projects/{PROJECT_ID}/constituencies").json()
    offenbach = body["constituencies"][0]

    assert [m["name"] for m in offenbach["direct_mandates"]] == ["Tarek Al-Wazir"]
    assert [m["name"] for m in offenbach["list_mandates"]] == ["Änne Beispiel"]
    assert offenbach["has_direct_mandate"] is True
    assert offenbach["direct_mandates"][0]["committees"][0]["role_label"] == "Vorsitz"


def test_constituency_without_a_direct_mandate_says_so(
    client, parliament_data, project_override
):
    body = client.get(f"/api/v1/projects/{PROJECT_ID}/constituencies").json()
    flensburg = next(c for c in body["constituencies"] if c["number"] == 1)

    # Since the electoral reform this is a regular case, not a data gap.
    assert flensburg["has_direct_mandate"] is False
    assert flensburg["has_any_mandate"] is True


def test_project_without_geometry_reports_why_it_is_empty(client, parliament_data):
    app.dependency_overrides[api_deps.get_project_or_404] = lambda: FakeProject(
        project_id=9999, geojson=None
    )
    try:
        body = client.get("/api/v1/projects/9999/constituencies").json()
    finally:
        app.dependency_overrides.pop(api_deps.get_project_or_404, None)

    assert body["has_geometry"] is False
    assert body["constituencies"] == []


# --- politicians ------------------------------------------------------------


def test_politician_list_is_public(client, parliament_data):
    resp = client.get("/api/v1/parliament/politicians")
    assert resp.status_code == 200
    assert {row["name"] for row in resp.json()} == {
        "Tarek Al-Wazir",
        "Änne Beispiel",
        "Nord Licht",
    }


def test_politician_search_is_umlaut_tolerant(client, parliament_data):
    body = client.get("/api/v1/parliament/politicians", params={"query": "anne"}).json()
    assert [row["name"] for row in body] == ["Änne Beispiel"]

    body = client.get("/api/v1/parliament/politicians", params={"query": "al-wazir"}).json()
    assert [row["name"] for row in body] == ["Tarek Al-Wazir"]


def test_committee_filter_narrows_to_the_working_list(client, parliament_data):
    body = client.get("/api/v1/parliament/politicians", params={"committee": "verkehr"}).json()
    assert [row["name"] for row in body] == ["Tarek Al-Wazir"]
    assert body[0]["project_count"] == 1

    assert client.get(
        "/api/v1/parliament/politicians", params={"committee": "haushalt"}
    ).json() == []


def test_unknown_committee_is_rejected(client, parliament_data):
    resp = client.get("/api/v1/parliament/politicians", params={"committee": "sport"})
    assert resp.status_code == 400


def test_fraction_filter(client, parliament_data):
    body = client.get("/api/v1/parliament/politicians", params={"fraction": "SPD"}).json()
    assert {row["name"] for row in body} == {"Änne Beispiel", "Nord Licht"}


def test_politician_detail_lists_the_projects_in_their_constituency(client, parliament_data):
    mandate_id = parliament_data["chair_mandate"].id
    body = client.get(f"/api/v1/parliament/politicians/{mandate_id}").json()

    assert body["constituency"]["number"] == 182
    assert [p["project_id"] for p in body["projects"]] == [PROJECT_ID]
    assert body["projects"][0]["length_km"] == 51.0


def test_politician_detail_404(client, parliament_data):
    assert client.get("/api/v1/parliament/politicians/999999").status_code == 404


# --- constituencies ---------------------------------------------------------


def test_constituency_list_counts_projects_and_mandates(client, parliament_data):
    body = client.get("/api/v1/parliament/constituencies").json()
    by_number = {row["number"]: row for row in body}

    assert by_number[182]["project_count"] == 1
    assert by_number[182]["mandate_count"] == 2
    assert by_number[182]["has_direct_mandate"] is True
    assert by_number[42]["mandate_count"] == 0
    # No outlines imported in this suite — the flag has to say so.
    assert by_number[42]["has_geometry"] is False


def test_constituency_detail(client, parliament_data):
    constituency_id = parliament_data["offenbach"].id
    body = client.get(f"/api/v1/parliament/constituencies/{constituency_id}").json()

    assert body["name"] == "Offenbach"
    assert [p["project_id"] for p in body["projects"]] == [PROJECT_ID]
    assert body["has_any_mandate"] is True


def test_constituency_without_anyone_running_there(client, parliament_data):
    constituency_id = parliament_data["empty"].id
    body = client.get(f"/api/v1/parliament/constituencies/{constituency_id}").json()

    # No direct mandate and nobody on the list either: there is no obvious
    # contact at all, and that is the useful information.
    assert body["has_direct_mandate"] is False
    assert body["has_any_mandate"] is False


def test_constituency_detail_404(client, parliament_data):
    assert client.get("/api/v1/parliament/constituencies/999999").status_code == 404


# --- status & import --------------------------------------------------------


def test_status_reports_period_counts_and_coverage(client, parliament_data):
    body = client.get("/api/v1/parliament/status").json()

    assert body["period"]["external_id"] == 161
    assert body["counts"]["constituencies"] == 3
    assert body["counts"]["mandates"] == 3
    assert body["counts"]["direct_mandates"] == 1
    assert body["counts"]["constituencies_without_direct_mandate"] == 2
    assert body["last_politician_import"]["status"] == "success"
    assert body["is_stale"] is False
    assert set(body["fractions"]) == {"BÜNDNIS 90/DIE GRÜNEN", "SPD"}
    assert {c["key"] for c in body["committees"]} == {"verkehr", "haushalt"}
    assert "GeoBasis-DE" in body["geometry_attribution"]


def test_status_flags_an_old_import_as_stale(client, db_session, parliament_data):
    run = db_session.query(ParliamentImportRun).one()
    run.finished_at = datetime.utcnow() - timedelta(days=90)
    db_session.commit()

    assert client.get("/api/v1/parliament/status").json()["is_stale"] is True


def test_import_requires_authentication(client):
    assert client.post("/api/v1/parliament/import").status_code == 401


def test_import_is_forbidden_without_the_capability(client, create_user):
    create_user("leserin", "pw", UserRole.viewer)
    resp = client.post(
        "/api/v1/parliament/import", headers=basic_auth_header("leserin", "pw")
    )
    assert resp.status_code == 403


def test_import_is_forbidden_for_an_editor_without_the_grant(client, create_user):
    # ``parliament.import`` is in the catalogue but seeded to no system role:
    # an admin grants it per role under /admin/roles.
    create_user("redakteurin", "pw", UserRole.editor)
    resp = client.post(
        "/api/v1/parliament/import", headers=basic_auth_header("redakteurin", "pw")
    )
    assert resp.status_code == 403


def test_import_starts_a_task_for_an_admin(client, create_user, monkeypatch):
    create_user("verwalterin", "pw", UserRole.admin)

    import dashboard_backend.tasks.parliament as parliament_tasks

    class FakeTask:
        id = "task-123"

    monkeypatch.setattr(
        parliament_tasks.refresh_parliament_data, "delay", lambda **kwargs: FakeTask()
    )
    resp = client.post(
        "/api/v1/parliament/import", headers=basic_auth_header("verwalterin", "pw")
    )
    assert resp.status_code == 202
    assert resp.json() == {"task_id": "task-123"}


def test_recompute_links_is_gated_too(client, create_user):
    create_user("leser", "pw", UserRole.viewer)
    resp = client.post(
        "/api/v1/parliament/recompute-links", headers=basic_auth_header("leser", "pw")
    )
    assert resp.status_code == 403
