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
