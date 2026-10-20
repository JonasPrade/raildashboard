"""Infraplan stages 3 and 4: planning state, PaBe relevance, forecast, cost
forecast, project/year reads and KPI values."""

from __future__ import annotations

from datetime import date

import pytest

from dashboard_backend.models.infraplan import InfraplanKpiValue
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header
from tests.api.test_infraplan_review import make_draft, project, row

BASE = "/api/v1/import/infraplan"
PUBLIC = "/api/v1/infraplan"


@pytest.fixture()
def editor(create_user):
    create_user("editor-ipy", "pass123", UserRole.editor)
    return basic_auth_header("editor-ipy", "pass123")


def confirm(client, editor, draft, published_on="2026-10-06"):
    resp = client.post(
        f"{BASE}/confirm",
        json={"parse_result_id": draft.id, "published_on": published_on},
        headers=editor,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def magdeburg_row(project_id: int, **values) -> dict:
    return row(
        "BP_A",
        20,
        primary_number="E.1637290101",
        state_raw="Bau",
        under_construction=True,
        ibn_raw="2030",
        ibn_year=2030,
        cost_mio=1720.48,
        footnote_refs=[14],
        footnotes={"14": "GWU 1.720,48 Mio. € bezieht sich auf Teil A 20 und Teil A 33"},
        parl_state="NICHT_VEREINBART",
        project_ids=[project_id],
        assignment_source="MANUAL",
        **values,
    )


# --- stage 3: planning state ---------------------------------------------------


def test_confirm_materialises_phase_and_forecast(client, editor, db_session):
    p = project(db_session, "ABS Magdeburg – Stendal – Uelzen")
    confirm(client, editor, make_draft(db_session, [magdeburg_row(p.id)]))

    derived = (
        db_session.query(ProgressObservation)
        .filter_by(project_id=p.id, is_derived=True, source_type="INFRAPLAN")
        .all()
    )
    assert {(o.track, o.asserted_state, o.is_expected) for o in derived} == {
        ("MAIN", "BAU", False),
        ("MAIN", "IN_BETRIEB", True),
    }
    assert {o.observed_date for o in derived if not o.is_expected} == {date(2026, 10, 6)}

    progress = client.get(f"/api/v1/projects/{p.id}/progress").json()
    assert progress["computed_phase"] == "BAU"
    steps = {s["phase"]: s for s in progress["forecast"]["next_steps"]}
    assert steps["IN_BETRIEB"]["expected_date"] == "2030-12-31"
    assert steps["IN_BETRIEB"]["source"] == "Infraplan"


def test_nicht_vereinbart_overrides_group_default(client, editor, db_session):
    group = ProjectGroup(name="Bedarfsplan", short_name="BSWAG-VB")
    db_session.add(group)
    p = project(db_session, "Bedarfsplanprojekt")
    p.project_groups = [group]
    db_session.flush()
    assert client.get(f"/api/v1/projects/{p.id}/progress").json()["parl_befassung_relevant"] is True

    confirm(client, editor, make_draft(db_session, [magdeburg_row(p.id)]))

    body = client.get(f"/api/v1/projects/{p.id}/progress").json()
    assert body["parl_befassung_relevant"] is False

    # The manual decision still wins.
    client.patch(f"/api/v1/projects/{p.id}/progress", json={"parl_befassung_relevant": True}, headers=editor)
    assert client.get(f"/api/v1/projects/{p.id}/progress").json()["parl_befassung_relevant"] is True


def test_parl_track_from_running_procedure(client, editor, db_session):
    p = project(db_session, "Mit Befassung")
    confirm(
        client,
        editor,
        make_draft(db_session, [magdeburg_row(p.id, parl_raw="Verfahren läuft") | {"parl_state": "LAEUFT"}]),
    )

    body = client.get(f"/api/v1/projects/{p.id}/progress").json()
    assert body["parl_befassung_relevant"] is True
    assert body["parl_state"] == "LAEUFT"


def test_delete_year_removes_derived_observations(client, editor, db_session):
    p = project(db_session, "Wird gelöscht")
    confirm(client, editor, make_draft(db_session, [magdeburg_row(p.id)]))
    assert db_session.query(ProgressObservation).filter_by(source_type="INFRAPLAN").count() == 2

    client.delete(f"{BASE}/report/2026", headers=editor)

    assert db_session.query(ProgressObservation).filter_by(source_type="INFRAPLAN").count() == 0


def test_only_newest_year_counts(client, editor, db_session):
    p = project(db_session, "Zwei Jahrgänge")
    confirm(client, editor, make_draft(db_session, [magdeburg_row(p.id)], year=2026))
    later = row("BP_B", 4, lph_from=3, lph_to=4, state_raw="Lph 3-4", project_ids=[p.id], assignment_source="MANUAL")
    confirm(client, editor, make_draft(db_session, [later], year=2027), published_on="2027-10-01")

    main = {
        o.asserted_state
        for o in db_session.query(ProgressObservation).filter_by(
            project_id=p.id, source_type="INFRAPLAN", track="MAIN", is_expected=False
        )
    }
    assert main == {"GENEHMIGUNGSPLANUNG"}


# --- stage 3: project read and costs -----------------------------------------------


def test_project_infraplan_entries_and_cost(client, editor, db_session):
    p = project(db_session, "ABS Magdeburg – Stendal – Uelzen")
    other = project(db_session, "Stendal Einbindung")
    rows = [
        magdeburg_row(p.id),
        row(
            "BP_A",
            33,
            cost_ref_raw="Ref. Teil A 20",
            cost_ref={"section": "BP_A", "lfd_nr": 20, "resolved": True},
            project_ids=[other.id],
            assignment_source="MANUAL",
        ),
    ]
    confirm(client, editor, make_draft(db_session, rows))

    body = client.get(f"{PUBLIC}/projects/{p.id}").json()
    assert body["latest_year"] == 2026
    assert body["missing_in_latest"] is False
    assert [(e["section"], e["lfd_nr"], e["cost_mio"]) for e in body["entries"]] == [("BP_A", 20, 1720.48)]
    assert body["cost_forecast"]["total_mio"] == 1720.48
    assert body["cost_forecast"]["label"] == "Gesamtkostenprognose (Infraplan 2026)"
    assert "14" in body["cost_forecast"]["footnotes"]

    referenced = client.get(f"{PUBLIC}/projects/{other.id}").json()
    assert referenced["entries"][0]["resolved_cost_mio"] == 1720.48


def test_parent_sums_subprojects_once(client, editor, db_session):
    parent = project(db_session, "Elternprojekt")
    a = project(db_session, "Teil A", superior_project_id=parent.id)
    b = project(db_session, "Teil B", superior_project_id=parent.id)
    rows = [
        row("BP_B", 1, cost_mio=100.0, project_ids=[a.id], assignment_source="MANUAL"),
        # Collective GWU: both subprojects carry the same row → counted once.
        row("BP_B", 2, cost_mio=50.5, project_ids=[a.id, b.id], assignment_source="MANUAL"),
        row(
            "BP_B",
            3,
            cost_ref={"section": "BP_B", "lfd_nr": 1, "resolved": True},
            project_ids=[b.id],
            assignment_source="MANUAL",
        ),
    ]
    confirm(client, editor, make_draft(db_session, rows))

    forecast = client.get(f"{PUBLIC}/projects/{parent.id}").json()["cost_forecast"]
    assert forecast["from_subprojects"] is True
    assert forecast["total_mio"] == 150.5


def test_gvfg_cost_label(client, editor, db_session):
    p = project(db_session, "S-Bahn")
    confirm(
        client,
        editor,
        make_draft(db_session, [row("GVFG_A", 1, cost_mio=12.3, project_ids=[p.id], assignment_source="NUMBER")]),
    )

    label = client.get(f"{PUBLIC}/projects/{p.id}").json()["cost_forecast"]["label"]
    assert label == "Gesamtkosten (Länderangabe, Infraplan 2026)"


def test_missing_in_latest_year(client, editor, db_session):
    p = project(db_session, "Fällt heraus")
    confirm(client, editor, make_draft(db_session, [magdeburg_row(p.id)], year=2026))
    confirm(client, editor, make_draft(db_session, [row("BP_A", 1)], year=2027))

    body = client.get(f"{PUBLIC}/projects/{p.id}").json()
    assert body["latest_year"] == 2027
    assert body["missing_in_latest"] is True


def test_public_reports_and_entries(client, editor, db_session):
    p = project(db_session, "Öffentlich")
    confirm(client, editor, make_draft(db_session, [magdeburg_row(p.id), row("BP_D", 1)]))

    assert client.get(f"{PUBLIC}/reports").json()[0]["entry_count"] == 2
    entries = client.get(f"{PUBLIC}/reports/2026/entries").json()
    assert entries[0]["projects"] == [{"id": p.id, "name": "Öffentlich"}]
    assert entries[1]["section_title"].startswith("Bedarfsplan, Teil D")
    assert client.get(f"{PUBLIC}/reports/1999/entries").status_code == 404


def test_project_infraplan_unknown_project(client):
    assert client.get(f"{PUBLIC}/projects/999999").status_code == 404


# --- stage 4: KPIs --------------------------------------------------------------------


def test_kpi_defaults_and_manual_values_are_public(client, editor, db_session):
    confirm(client, editor, make_draft(db_session, [row("BP_A", 1)]))

    kpis = client.get(f"{BASE}/kpis", headers=editor).json()
    assert len(kpis) == 25
    assert kpis[0]["key"] == "neu_gebaute_gleis_km"
    etcs = next(k for k in kpis if k["key"] == "etcs_strecken_km")
    assert (etcs["total_series"], etcs["companion_key"]) == ("Gesamtnetz", "etcs_ausruestungsgrad")

    resp = client.put(
        f"{BASE}/report/2026/kpi-values",
        json={
            "values": [
                {"kpi_key": "neu_gebaute_gleis_km", "year": 2025, "value_kind": "IST", "value": 41},
                {"kpi_key": "neu_gebaute_gleis_km", "year": 2030, "value_kind": "ZIEL", "value": 120.5},
            ]
        },
        headers=editor,
    )
    assert resp.json() == {"written": 2, "removed": 0, "definitions_created": 0}

    public = {k["key"]: k for k in client.get(f"{PUBLIC}/kpis").json()}
    assert [(v["year"], v["value_kind"], v["value"]) for v in public["neu_gebaute_gleis_km"]["values"]] == [
        (2025, "IST", 41.0),
        (2030, "ZIEL", 120.5),
    ]


def test_kpi_upsert_remove_and_series(client, editor, db_session):
    confirm(client, editor, make_draft(db_session, [row("BP_A", 1)]))
    slot = {"kpi_key": "umsetzung_kmm", "year": 2026, "value_kind": "ZIEL", "series": "ÜLS"}

    client.put(f"{BASE}/report/2026/kpi-values", json={"values": [slot | {"value": 10}]}, headers=editor)
    client.put(f"{BASE}/report/2026/kpi-values", json={"values": [slot | {"value": 12}]}, headers=editor)
    assert db_session.query(InfraplanKpiValue).one().value == 12

    resp = client.put(f"{BASE}/report/2026/kpi-values", json={"values": [slot | {"value": None}]}, headers=editor)
    assert resp.json()["removed"] == 1
    assert db_session.query(InfraplanKpiValue).count() == 0


def test_kpi_unknown_key_needs_definition(client, editor, db_session):
    confirm(client, editor, make_draft(db_session, [row("BP_A", 1)]))
    value = {"kpi_key": "neue_kennzahl", "year": 2026, "value_kind": "IST", "value": 1}

    refused = client.put(f"{BASE}/report/2026/kpi-values", json={"values": [value]}, headers=editor)
    assert refused.status_code == 422

    created = client.put(
        f"{BASE}/report/2026/kpi-values",
        json={
            "values": [value],
            "definitions": [{"key": "neue_kennzahl", "name": "Neue Kennzahl", "kind": "INFORMATION", "unit": "%"}],
        },
        headers=editor,
    )
    assert created.json()["definitions_created"] == 1


def test_unchecked_values_hidden_until_approved(client, editor, db_session):
    from dashboard_backend.crud import infraplan as infraplan_crud
    from dashboard_backend.crud.infraplan_import import get_report_by_year

    confirm(client, editor, make_draft(db_session, [row("BP_A", 1)]))
    report = get_report_by_year(db_session, 2026)
    infraplan_crud.set_kpi_values(
        db_session,
        report,
        [{"kpi_key": "etcs_strecken_km", "year": 2025, "value_kind": "IST", "value": 600, "source_page": 72}],
        [],
        status="UNGEPRUEFT",
        username="agent",
    )

    public = {k["key"]: k for k in client.get(f"{PUBLIC}/kpis").json()}
    assert public["etcs_strecken_km"]["values"] == []
    assert client.get(f"{BASE}/report", headers=editor).json()[0]["kpi_unchecked_count"] == 1

    assert client.post(f"{BASE}/report/2026/kpi-values/approve", headers=editor).json() == {"approved": 1}
    public = {k["key"]: k for k in client.get(f"{PUBLIC}/kpis").json()}
    assert public["etcs_strecken_km"]["values"][0]["value"] == 600.0


def test_kpi_settings_are_editable_and_public(client, editor, db_session):
    url = f"{BASE}/kpis/betriebsleistung"
    resp = client.patch(
        url,
        json={"unit": " Mio. Trkm ", "chart_layout": "split", "companion_key": "kapazitaetsauslastung", "companion_label": "Auslastung"},
        headers=editor,
    )
    assert resp.status_code == 200, resp.text
    assert (resp.json()["unit"], resp.json()["chart_layout"]) == ("Mio. Trkm", "split")

    public = {k["key"]: k for k in client.get(f"{PUBLIC}/kpis").json()}
    assert public["betriebsleistung"]["companion_key"] == "kapazitaetsauslastung"

    # Only the fields sent change; null clears an optional one.
    cleared = client.patch(url, json={"chart_layout": None}, headers=editor).json()
    assert (cleared["chart_layout"], cleared["unit"]) == (None, "Mio. Trkm")


def test_kpi_settings_are_validated(client, editor, db_session):
    url = f"{BASE}/kpis/betriebsleistung"
    client.get(f"{BASE}/kpis", headers=editor)  # creates the defaults
    assert client.patch(f"{BASE}/kpis/gibt_es_nicht", json={"unit": "%"}, headers=editor).status_code == 404
    assert client.patch(url, json={"companion_key": "betriebsleistung"}, headers=editor).status_code == 422
    assert client.patch(url, json={"companion_key": "gibt_es_nicht"}, headers=editor).status_code == 422
    assert client.patch(url, json={"chart_layout": "pie"}, headers=editor).status_code == 422
    assert client.patch(url, json={"name": None}, headers=editor).status_code == 422
    assert client.patch(url, json={"unit": "%"}).status_code == 401


def test_kpi_values_require_year(client, editor):
    assert client.get(f"{BASE}/report/2026/kpi-values", headers=editor).status_code == 404


# --- repair of full stops read as U+FFFD -----------------------------------------


def test_repair_full_stops_fixes_confirmed_year_in_place(client, editor, db_session):
    from dashboard_backend.crud.infraplan_import import repair_full_stops
    from dashboard_backend.models.infraplan import InfraplanEntry, InfraplanEntryProject

    p = project(db_session, "Hanau – Gelnhausen")
    q = project(db_session, "Puttgarden")
    draft = make_draft(
        db_session,
        [
            row(
                "BP_A", 2,
                project_numbers_raw="E�1637260058",
                massnahme="4gl� Ausbau Hanau-Gelnhausen",
                cost_raw="Ref� Teil A 3 | E�1631230009",
                footnotes={"10": "Der GWU-Wert in Höhe von 1�676,02 Mio� €"},
                project_ids=[p.id],
                assignment_source="AGENT",
                assignment_note="Name stimmt",
            ),
            row(
                "BP_A", 3,
                project_numbers_raw="E�1631230009",
                state_raw="Lph� 3",
                cost_raw="8�044,54",
                project_ids=[q.id],
                assignment_source="MANUAL",
            ),
        ],
    )
    confirm(client, editor, draft)

    # A dry run writes nothing.
    assert repair_full_stops(db_session, apply=False)[0]["rows_changed"] == 2
    assert "\ufffd" in str(db_session.get(type(draft), draft.id).result_json)

    summaries = repair_full_stops(db_session, apply=True)

    assert summaries[0]["rows_changed"] == 2
    assert summaries[0]["entries_changed"] == 2
    assert summaries[0]["warnings"] == []
    entries = {e.lfd_nr: e for e in db_session.query(InfraplanEntry).filter_by(section="BP_A")}
    assert entries[2].massnahme == "4gl. Ausbau Hanau-Gelnhausen"
    assert entries[2].primary_number == "E.1637260058"
    assert entries[2].footnotes == {"10": "Der GWU-Wert in Höhe von 1.676,02 Mio. €"}
    assert entries[2].cost_ref_entry_id == entries[3].id
    assert float(entries[3].cost_mio) == 8044.54
    assert entries[3].lph_from == 3
    # The links of the confirmed year stay.
    links = {(link.entry_id, link.project_id) for link in db_session.query(InfraplanEntryProject)}
    assert links == {(entries[2].id, p.id), (entries[3].id, q.id)}
    # The draft keeps its review state.
    stored = {r["lfd_nr"]: r for r in draft.result_json["rows"]}
    assert stored[2]["project_ids"] == [p.id]
    assert stored[2]["assignment_note"] == "Name stimmt"
    assert stored[2]["massnahme"] == "4gl. Ausbau Hanau-Gelnhausen"

    # A second run finds nothing left to do.
    assert repair_full_stops(db_session, apply=True) == []
