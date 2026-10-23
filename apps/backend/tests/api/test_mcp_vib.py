"""MCP VIB tools (feature-vib-import.md → Phase 7): report → Vorhaben with
PFA table → assignment → confirmation → derived observations; check mode on
an existing year."""

from __future__ import annotations

from datetime import date

from dashboard_backend.crud import vib_agent
from dashboard_backend.crud.admin_assignments import assign_vib_entry_to_projects
from dashboard_backend.crud.projects.progress import sync_derived_observations
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.vib.vib_entry import VibEntry
from dashboard_backend.models.vib.vib_report import VibReport
from dashboard_backend.schemas.users import UserRole
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    admin_token,
    mcp_client,
)

NAME = "Lfd. Vorhaben Nr. 2 – ABS Lübeck/Hagenow Land–Rostock–Stralsund (VDE Nr. 1)"


def _seed(db):
    parent = Project(name="ABS Lübeck/Hagenow Land – Rostock – Stralsund")
    other = Project(name="ABS Hamburg – Lübeck")
    db.add_all([parent, other])
    db.flush()
    sub = Project(name="Abschnitt Bad Kleinen – Rostock", superior_project_id=parent.id)
    db.add(sub)
    db.commit()
    return parent, other, sub


def _derived(db, project_id):
    sync_derived_observations(db, project_id)
    db.commit()
    return (
        db.query(ProgressObservation)
        .filter(ProgressObservation.project_id == project_id, ProgressObservation.is_derived.is_(True))
        .all()
    )


def _entry_input(**extra):
    return {
        "vib_section": "B 4.1.1",
        "vib_name_raw": NAME,
        "category": "laufend",
        "page": 56,
        "planungsstand": "Die Bauarbeiten laufen.",
        "status_bau": True,
        "pfa_entries": [
            {"abschnitt_label": "Bad Kleinen – Rostock", "nr_pfa": "2.1", "oertlichkeit": "Bad Kleinen",
             "entwurfsplanung": "abgeschlossen", "datum_pfb": "12/2019", "baubeginn": "03/2021"},
        ],
        **extra,
    }


def _report(client, token, year=2023):
    return _payload(
        _call(client, token, "create_vib_report",
              {"year": year, "report_date": f"{year + 1}-03-15", "drucksache_nr": "20/11000"})
    )


def test_full_flow(mcp_client, admin_token, db_session):
    parent, other, sub = _seed(db_session)
    report = _report(mcp_client, admin_token)

    again = _call(mcp_client, admin_token, "create_vib_report", {"year": 2023, "report_date": "2024-03-15"})
    assert again["isError"] is True
    assert str(report["id"]) in again["content"][0]["text"]

    added = _payload(
        _call(mcp_client, admin_token, "add_vib_entries",
              {"report_id": report["id"], "entries": [_entry_input()]})
    )["entries"]
    entry = added[0]
    assert entry["vib_section"] == "B.4.1.1"
    assert entry["confirmed"] is False
    # One pre-assigned project at most, with its reason; the "Lfd. Vorhaben
    # Nr." prefix no longer drowns the name match.
    assert entry["project_ids"] == [parent.id]
    assert entry["assignment_note"].startswith("Automatischer Vorschlag (Namensähnlichkeit")
    assert entry["assignment_note"].endswith("ungeprüft")
    assert entry["suggestions"][0]["project_id"] == parent.id

    # Unconfirmed: nothing reaches the progress yet.
    assert _derived(db_session, parent.id) == []

    # Same section twice is refused.
    dup = _call(mcp_client, admin_token, "add_vib_entries",
                {"report_id": report["id"], "entries": [_entry_input()]})
    assert dup["isError"] is True and "B.4.1.1" in dup["content"][0]["text"]

    # Several projects for one Vorhaben, with one reason.
    assigned = _payload(
        _call(mcp_client, admin_token, "assign_vib_entry",
              {"entry_id": entry["id"], "project_ids": [parent.id, other.id],
               "note": "Sammelvorhaben: beide Oberprojekte"})
    )
    assert sorted(assigned["project_ids"]) == sorted([parent.id, other.id])
    pfa = assigned["pfa_entries"][0]
    assert pfa["suggested_project_id"] == sub.id

    _payload(_call(mcp_client, admin_token, "assign_vib_pfa", {"pfa_id": pfa["id"], "project_id": sub.id}))

    confirmed = _payload(_call(mcp_client, admin_token, "confirm_vib_report", {"report_id": report["id"]}))
    assert confirmed["confirmed_now"] == 1
    assert confirmed["report"]["confirmed"] == 1 and confirmed["report"]["assigned"] == 1

    # The assigned PFA section carries its dates to the subproject (the parents'
    # flattened entry phase is suppressed once a section is split out).
    assert any(o.source_type == "VIB" for o in _derived(db_session, sub.id))

    # A later MCP change reopens the entry until confirmed again.
    _payload(_call(mcp_client, admin_token, "update_vib_entry",
                   {"entry_id": entry["id"], "changes": {"status_abgeschlossen": True}}))
    assert _derived(db_session, sub.id) == []
    open_entries = _payload(_call(mcp_client, admin_token, "list_vib_entries",
                                  {"report_id": report["id"], "only_open": True}))["entries"]
    assert [e["id"] for e in open_entries] == [entry["id"]]


def test_previous_year_assignment_is_suggested(mcp_client, admin_token, db_session):
    parent, other, _ = _seed(db_session)
    old = VibReport(year=2022, report_date=date(2023, 3, 1))
    db_session.add(old)
    db_session.flush()
    db_session.add(VibEntry(vib_report_id=old.id, vib_section="B.4.1.1", vib_name_raw=NAME,
                            category="laufend", projects=[other]))
    db_session.commit()

    report = _report(mcp_client, admin_token)
    entry = _payload(_call(mcp_client, admin_token, "add_vib_entries",
                           {"report_id": report["id"], "entries": [_entry_input()]}))["entries"][0]
    assert entry["project_ids"] == [other.id]
    assert "Vorjahr" in entry["assignment_note"]


def test_validation_and_permission(mcp_client, admin_token, create_user, db_session):
    report = _report(mcp_client, admin_token)
    bad = _call(mcp_client, admin_token, "add_vib_entries",
                {"report_id": report["id"], "entries": [_entry_input(vib_section="4.1")]})
    assert bad["isError"] is True
    no_note = _call(mcp_client, admin_token, "assign_vib_entry", {"entry_id": 1, "project_ids": [], "note": " "})
    assert no_note["isError"] is True

    admin = create_user("admin2", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["mcp.access", "progress.edit"])
    denied = _call(mcp_client, token, "list_vib_reports", {})
    assert denied["isError"] is True and "vib.import" in denied["content"][0]["text"]


def test_existing_entries_count_as_confirmed_and_editor_assignment_confirms(db_session):
    parent, _, _ = _seed(db_session)
    report = VibReport(year=2021)
    db_session.add(report)
    db_session.flush()
    legacy = VibEntry(vib_report_id=report.id, vib_name_raw="Alt", category="laufend",
                      status_bau=True, projects=[parent])
    db_session.add(legacy)
    db_session.commit()
    assert legacy.confirmed is True
    assert _derived(db_session, parent.id)

    agent = VibEntry(vib_report_id=report.id, vib_name_raw="Neu", category="laufend",
                     status_planung=True, confirmed=False)
    db_session.add(agent)
    db_session.commit()
    assign_vib_entry_to_projects(db_session, agent.id, [parent.id])
    db_session.commit()
    db_session.refresh(agent)
    assert agent.confirmed is True


def test_section_normalisation():
    assert vib_agent.normalize_section("B 4.1.1") == "B.4.1.1"
    assert vib_agent.normalize_section("b4.2.10") == "B.4.2.10"


# --- Phase 8: PFA rows → subprojects -------------------------------------------

KARLSRUHE = "Lfd. Vorhaben Nr. 24 – ABS/NBS Karlsruhe–Offenburg–Freiburg–Basel (1. und 2. Baustufe)"


def _seed_karlsruhe(db):
    bundle = Project(name="Projektbündel 7: Karlsruhe – Basel (Oberrhein)")
    db.add(bundle)
    db.flush()
    middle = Project(name="ABS/NBS Karlsruhe - Basel", superior_project_id=bundle.id)
    foreign = Project(name="ABS Kehl - Appenweier", superior_project_id=bundle.id)
    db.add_all([middle, foreign])
    db.flush()
    a7 = Project(name="ABS/NBS Karlsruhe – Basel, Abschnitt 7 Appenweier Kenzingen",
                 project_number="2-005-V02-Abschnitt7", superior_project_id=middle.id)
    a9 = Project(name="ABS/NBS Karlsruhe – Basel, Abschnitt 9 Müllheim – Basel",
                 project_number="2-005-V02-Abschnitt9", superior_project_id=middle.id)
    db.add_all([a7, a9])
    db.commit()
    return bundle, middle, foreign, a7, a9


def _karlsruhe_entry(client, token, report_id, bundle_id):
    pfas = [
        {"nr_pfa": "7.1", "oertlichkeit": "Appenweier-Hohberg"},
        {"nr_pfa": "7.1", "oertlichkeit": "NBS", "datum_pfb": "vsl. 2025"},
        {"nr_pfa": "9.1", "oertlichkeit": "Schliengen–Eimeldingen", "inbetriebnahme": "12/2012"},
        {"nr_pfa": "ESTW", "oertlichkeit": "Buggingen", "inbetriebnahme": "07.11.2009"},
    ]
    entry = _payload(_call(client, token, "add_vib_entries", {"report_id": report_id, "entries": [
        {"vib_section": "B.4.1.23", "vib_name_raw": KARLSRUHE, "category": "laufend", "pfa_entries": pfas}
    ]}))["entries"][0]
    return _payload(_call(client, token, "assign_vib_entry",
                          {"entry_id": entry["id"], "project_ids": [bundle_id], "note": "Projektbündel 7"}))


def test_pfa_suggestions_from_the_whole_subtree_and_apply(mcp_client, admin_token, db_session):
    bundle, middle, foreign, a7, a9 = _seed_karlsruhe(db_session)
    report = _report(mcp_client, admin_token)
    detail = _karlsruhe_entry(mcp_client, admin_token, report["id"], bundle.id)

    rows = {(p["nr_pfa"], p["oertlichkeit"]): p for p in detail["pfa_entries"]}
    first = rows[("7.1", "Appenweier-Hohberg")]
    # Grandchild found by the section number, not the foreign sibling by name.
    assert first["suggested_project_id"] == a7.id
    assert first["suggestion_strong"] is True
    assert "Abschnittsnummer" in first["suggested_reason"]
    assert rows[("9.1", "Schliengen–Eimeldingen")]["suggested_project_id"] == a9.id
    assert rows[("ESTW", "Buggingen")]["suggested_project_id"] is None
    assert {s["id"] for s in detail["subprojects"]} == {middle.id, foreign.id, a7.id, a9.id}
    assert {s["depth"] for s in detail["subprojects"]} == {1, 2}

    applied = _payload(_call(mcp_client, admin_token, "apply_vib_pfa_suggestions", {"report_id": report["id"]}))
    assert applied["applied_rows"] == 3
    assert applied["entries"][0]["still_open"] == 1
    entry = _payload(_call(mcp_client, admin_token, "get_vib_entry", {"entry_id": detail["id"]}))
    assigned = {p["oertlichkeit"]: p["project_id"] for p in entry["pfa_entries"]}
    assert assigned == {"Appenweier-Hohberg": a7.id, "NBS": a7.id,
                        "Schliengen–Eimeldingen": a9.id, "Buggingen": None}
    assert entry["confirmed"] is False

    # Next year's report takes over the confirmed assignment ("Vorjahr").
    _payload(_call(mcp_client, admin_token, "confirm_vib_report", {"report_id": report["id"]}))
    _payload(_call(mcp_client, admin_token, "assign_vib_pfa",
                   {"pfa_id": rows[("ESTW", "Buggingen")]["id"], "project_id": a9.id}))
    _payload(_call(mcp_client, admin_token, "confirm_vib_report", {"report_id": report["id"]}))
    next_report = _report(mcp_client, admin_token, year=2024)
    following = _karlsruhe_entry(mcp_client, admin_token, next_report["id"], bundle.id)
    estw = next(p for p in following["pfa_entries"] if p["nr_pfa"] == "ESTW")
    assert estw["suggested_project_id"] == a9.id
    assert estw["suggested_reason"] == "Vorjahr: VIB 2023 bestätigt"


def test_assign_vib_pfas_checks_rows_and_subtree(mcp_client, admin_token, db_session):
    bundle, middle, foreign, a7, a9 = _seed_karlsruhe(db_session)
    outsider = Project(name="Anderes Projekt")
    db_session.add(outsider)
    db_session.commit()
    report = _report(mcp_client, admin_token)
    detail = _karlsruhe_entry(mcp_client, admin_token, report["id"], bundle.id)
    ids = [p["id"] for p in detail["pfa_entries"]]

    bad = _call(mcp_client, admin_token, "assign_vib_pfas",
                {"entry_id": detail["id"], "items": [{"pfa_id": ids[0], "project_id": outsider.id}]})
    assert bad["isError"] is True and "liegt nicht unter" in bad["content"][0]["text"]
    foreign_row = _call(mcp_client, admin_token, "assign_vib_pfas",
                        {"entry_id": detail["id"], "items": [{"pfa_id": 999999, "project_id": a7.id}]})
    assert foreign_row["isError"] is True

    done = _payload(_call(mcp_client, admin_token, "assign_vib_pfas", {"entry_id": detail["id"], "items": [
        {"pfa_id": ids[0], "project_id": a7.id}, {"pfa_id": ids[2], "project_id": a9.id}]}))
    assert [p["project_id"] for p in done["pfa_entries"]] == [a7.id, None, a9.id, None]


def test_create_vib_pfa_subprojects(mcp_client, admin_token, db_session):
    parent, other, sub = _seed(db_session)
    report = _report(mcp_client, admin_token)
    entry = _payload(_call(mcp_client, admin_token, "add_vib_entries", {"report_id": report["id"], "entries": [
        _entry_input(pfa_entries=[
            {"nr_pfa": "3", "oertlichkeit": "Bad Kleinen (e)-Ventschow (a)", "entwurfsplanung": "offen"},
            {"nr_pfa": "3", "oertlichkeit": "Ventschow (e)-Blankenberg (e)", "baubeginn": "03.11.2003",
             "inbetriebnahme": "11.12.2005"},
            {"nr_pfa": "4", "oertlichkeit": "Sanierung Ribnitz-Damgarten West (a)-Stralsund (a)"},
        ])
    ]}))["entries"][0]
    _payload(_call(mcp_client, admin_token, "assign_vib_entry",
                   {"entry_id": entry["id"], "project_ids": [parent.id], "note": "VDE 1"}))
    rows = _payload(_call(mcp_client, admin_token, "get_vib_entry", {"entry_id": entry["id"]}))["pfa_entries"]

    result = _payload(_call(mcp_client, admin_token, "create_vib_pfa_subprojects", {"entry_id": entry["id"], "items": [
        {"pfa_ids": [rows[0]["id"], rows[1]["id"]], "parent_id": parent.id},
        {"pfa_ids": [rows[2]["id"]], "parent_id": sub.id, "name": "Sanierung Ribnitz-Damgarten – Stralsund"},
        {"pfa_ids": [rows[2]["id"]], "parent_id": parent.id},
        {"pfa_ids": [rows[0]["id"]], "parent_id": other.id},
    ]}))
    assert (result["ok"], result["failed"]) == (2, 2)
    first, second, dup, outside = result["items"]
    assert first["name"] == "PFA 3 Bad Kleinen (e)-Ventschow (a) / Ventschow (e)-Blankenberg (e)"
    assert first["parent_was_leaf"] is False
    # sub had no children: now an interim node — the result says so.
    assert second["parent_was_leaf"] is True and "Teilprojekte" in second["warning"]
    assert "andere" in dup["error"] or "zugeordnet" in dup["error"]
    assert "weder" in outside["error"]

    created = db_session.get(Project, first["project_id"])
    db_session.refresh(created)
    assert created.is_draft is True and created.superior_project_id == parent.id
    assert created.geojson_representation is None
    detail = _payload(_call(mcp_client, admin_token, "get_vib_entry", {"entry_id": entry["id"]}))
    assert [p["project_id"] for p in detail["pfa_entries"]] == [first["project_id"]] * 2 + [second["project_id"]]
    assert detail["confirmed"] is False

    # After confirming, the dated row feeds the new draft subproject.
    _payload(_call(mcp_client, admin_token, "confirm_vib_report", {"report_id": report["id"]}))
    assert any(o.source_type == "VIB" for o in _derived(db_session, first["project_id"]))


def test_project_page_suggests_from_the_subtree(client, mcp_client, admin_token, db_session):
    bundle, middle, foreign, a7, a9 = _seed_karlsruhe(db_session)
    report = _report(mcp_client, admin_token)
    _karlsruhe_entry(mcp_client, admin_token, report["id"], bundle.id)

    response = client.get(f"/api/v1/projects/{bundle.id}/vib")
    assert response.status_code == 200
    pfas = {(p["nr_pfa"], p["oertlichkeit"]): p for p in response.json()[0]["pfa_entries"]}
    assert pfas[("7.1", "Appenweier-Hohberg")]["suggested_project_id"] == a7.id
    assert pfas[("ESTW", "Buggingen")]["suggested_project_id"] is None
