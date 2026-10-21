"""MCP GVFG tools: editions, Vorhaben, a project's funding and correcting links."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from dashboard_backend.models.gvfg import GvfgEntry, GvfgEntryAmount, GvfgProgram
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.schemas.users import UserRole
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    admin_token,
    mcp_client,
)

PERIODS_2023 = [
    {"label": "1967–2021", "year_from": 1967, "year_to": 2021, "kind": "ausgezahlt"},
    {"label": "2023", "year_from": 2023, "year_to": 2023, "kind": "geplant"},
]
PERIODS_2025 = [
    {"label": "1967–2023", "year_from": 1967, "year_to": 2023, "kind": "ausgezahlt"},
    {"label": "2025", "year_from": 2025, "year_to": 2025, "kind": "geplant"},
    {"label": "2026", "year_from": 2026, "year_to": 2026, "kind": "geplant"},
]


def _entry(program, key, name, land="Hamburg", kind="kommunal", part="finanzrelevant", lines=()):
    entry = GvfgEntry(
        program=program, key=key, key_raw=key.replace("_", " _ "), land=land, kind=kind,
        part=part, name=name, funding_type="Neubau", funding_rate=75, commissioning_planned=2030,
    )
    for line_no, (category, cost, aid, periods) in enumerate(lines):
        entry.amounts.append(
            GvfgEntryAmount(
                line_no=line_no, category=category, cost_total=Decimal(cost), aid_total=Decimal(aid),
                periods=periods,
            )
        )
    return entry


def _seed(db):
    group = ProjectGroup(name="Gemeindeverkehrsfinanzierungsgesetz", short_name="GVFG", color="#000")
    bw_group = ProjectGroup(name="GVFG Baden-Württemberg", short_name="GVFG BW", color="#000")
    u4 = Project(name="U4 Horner Geest", project_number="02 G 509_A", is_draft=False)
    dup = Project(name="U4 Horner Geest (Dublette)", project_number="02 G 509 _ A", is_draft=False)
    karlsruhe = Project(name="Stadtbahn Karlsruhe", project_number="08 G 100_A", is_draft=False)
    old = GvfgProgram(year_from=2023, year_to=2027, title="GVFG 2023–2027", stand=date(2023, 9, 1),
                      periods=PERIODS_2023)
    new = GvfgProgram(year_from=2025, year_to=2029, title="GVFG 2025–2029", stand=date(2025, 7, 18),
                      periods=PERIODS_2025)
    u4_old = _entry(old, "02 G 509_A", "Verlängerung U4", lines=[
        ("SUM", "200", "150", {"1967–2021": "10", "2023": "20"}),
        ("C", "200", "150", {"2023": "20"}),
    ])
    u4_new = _entry(new, "02 G 509_A", "Verlängerung U4 Horner Geest", lines=[
        ("SUM", "300", "225", {"1967–2023": "30", "2025": "40", "2026": "50"}),
        ("A", "300", "225", {"2025": "40", "2026": "50"}),
    ])
    open_new = _entry(new, "08 G 100_A", "Stadtbahn Karlsruhe Kriegsstraße", land="Baden-Württemberg",
                      lines=[("SUM", "80", "60", {"2025": "5"})])
    info_new = _entry(new, "02 D 700_A", "S-Bahn Hamburg Ausbau", kind="db", part="nachrichtlich",
                      lines=[("SUM", "50", "30", {})])
    u4_old.projects = [dup]
    u4_new.projects = [u4, dup]
    db.add_all([group, bw_group, u4, dup, karlsruhe, old, new, u4_old, u4_new, open_new, info_new])
    db.commit()
    return {"u4": u4, "dup": dup, "karlsruhe": karlsruhe, "old": old, "new": new,
            "u4_old": u4_old, "u4_new": u4_new, "open_new": open_new}


def _keys(payload):
    return [e["key"] for e in payload["entries"]]


def test_list_programs(mcp_client, admin_token, db_session):
    _seed(db_session)
    payload = _payload(_call(mcp_client, admin_token, "list_gvfg_programs"))
    programs = payload["programs"]
    assert [p["edition"] for p in programs] == ["2025–2029", "2023–2027"]
    assert (programs[0]["entries"], programs[0]["entries_without_project"]) == (3, 2)
    assert (programs[1]["entries"], programs[1]["entries_without_project"]) == (1, 0)
    assert [p["label"] for p in programs[0]["periods"]] == ["1967–2023", "2025", "2026"]


def test_list_entries_newest_edition_and_filters(mcp_client, admin_token, db_session):
    seed = _seed(db_session)
    payload = _payload(_call(mcp_client, admin_token, "list_gvfg_entries"))
    assert payload["edition"] == "2025–2029"
    assert payload["total"] == 3
    assert _keys(payload) == ["08 G 100_A", "02 D 700_A", "02 G 509_A"]
    u4 = next(e for e in payload["entries"] if e["key"] == "02 G 509_A")
    assert u4["categories"] == ["A"]
    assert (u4["cost_total"], u4["aid_total"], u4["aid_planned"]) == (300.0, 225.0, 90.0)
    assert [p["id"] for p in u4["projects"]] == sorted([seed["u4"].id, seed["dup"].id])
    info = next(e for e in payload["entries"] if e["key"] == "02 D 700_A")
    assert info["aid_planned"] is None

    def keys(**args):
        return _keys(_payload(_call(mcp_client, admin_token, "list_gvfg_entries", args)))

    assert keys(search="2 G 509 _ A") == ["02 G 509_A"]
    assert keys(search="02 G 509_T") == ["02 G 509_A"]  # same key without suffix
    assert keys(search="kriegsstraße") == ["08 G 100_A"]
    assert keys(land="baden") == ["08 G 100_A"]
    assert keys(kind="db") == ["02 D 700_A"]
    assert keys(part="nachrichtlich") == ["02 D 700_A"]
    assert keys(has_project=False) == ["08 G 100_A", "02 D 700_A"]
    assert keys(program_id=seed["old"].id) == ["02 G 509_A"]


def test_entries_flag_draft_projects(mcp_client, admin_token, db_session):
    _seed(db_session)
    project = db_session.query(Project).filter_by(project_number="02 G 509_A").one()
    project.is_draft = True
    db_session.commit()
    entries = _payload(_call(mcp_client, admin_token, "list_gvfg_entries", {"search": "02 G 509"}))["entries"]
    assert {p["name"]: p["is_draft"] for e in entries for p in e["projects"]} == {
        "U4 Horner Geest": True,
        "U4 Horner Geest (Dublette)": False,
    }


def test_unknown_program_is_error(mcp_client, admin_token, db_session):
    result = _call(mcp_client, admin_token, "list_gvfg_entries")
    assert result["isError"] is True
    assert "noch keine GVFG-Ausgabe" in result["content"][0]["text"]
    _seed(db_session)
    assert _call(mcp_client, admin_token, "list_gvfg_entries", {"program_id": 999})["isError"] is True


def test_get_entry_with_history(mcp_client, admin_token, db_session):
    seed = _seed(db_session)
    payload = _payload(
        _call(mcp_client, admin_token, "get_gvfg_entry", {"entry_id": seed["u4_new"].id})
    )
    assert payload["edition"] == "2025–2029"
    assert [a["category"] for a in payload["amounts"]] == ["SUM", "A"]
    assert Decimal(payload["amounts"][0]["periods"]["2026"]) == Decimal("50")
    history = payload["history"]
    assert [(h["edition"], h["categories"], h["cost_total"]) for h in history] == [
        ("2025–2029", ["A"], 300.0),
        ("2023–2027", ["C"], 200.0),
    ]


def test_list_project_gvfg(mcp_client, admin_token, db_session):
    seed = _seed(db_session)
    own = _payload(_call(mcp_client, admin_token, "list_project_gvfg", {"project_id": seed["dup"].id}))
    assert [e["edition"] for e in own["entries"]] == ["2025–2029", "2023–2027"]

    parent = Project(name="U-Bahn Hamburg", is_draft=False)
    db_session.add(parent)
    db_session.flush()
    seed["u4"].superior_project_id = parent.id
    db_session.commit()
    alone = _payload(_call(mcp_client, admin_token, "list_project_gvfg", {"project_id": parent.id}))
    assert alone["entries"] == []
    with_children = _payload(
        _call(mcp_client, admin_token, "list_project_gvfg",
              {"project_id": parent.id, "with_subprojects": True})
    )
    assert [e["key"] for e in with_children["entries"]] == ["02 G 509_A"]

    missing = _call(mcp_client, admin_token, "list_project_gvfg", {"project_id": 999999})
    assert missing["isError"] is True


def test_assign_replaces_links_and_adds_groups(mcp_client, admin_token, db_session):
    seed = _seed(db_session)
    payload = _payload(
        _call(mcp_client, admin_token, "assign_gvfg_entry",
              {"entry_id": seed["u4_new"].id, "project_ids": [seed["u4"].id], "all_editions": True})
    )
    assert [(e["edition"], [p["id"] for p in e["projects"]]) for e in payload["updated"]] == [
        ("2025–2029", [seed["u4"].id]),
        ("2023–2027", [seed["u4"].id]),
    ]
    db_session.expire_all()
    assert [p.id for p in seed["u4_old"].projects] == [seed["u4"].id]
    assert [g.short_name for g in seed["u4"].project_groups] == ["GVFG"]

    _payload(
        _call(mcp_client, admin_token, "assign_gvfg_entry",
              {"entry_id": seed["open_new"].id, "project_ids": [seed["karlsruhe"].id]})
    )
    db_session.expire_all()
    assert sorted(g.short_name for g in seed["karlsruhe"].project_groups) == ["GVFG", "GVFG BW"]

    # Only this edition; an empty list removes the link, the groups stay.
    _payload(
        _call(mcp_client, admin_token, "assign_gvfg_entry",
              {"entry_id": seed["u4_new"].id, "project_ids": []})
    )
    db_session.expire_all()
    assert seed["u4_new"].projects == []
    assert [p.id for p in seed["u4_old"].projects] == [seed["u4"].id]
    assert [g.short_name for g in seed["u4"].project_groups] == ["GVFG"]

    unknown = _call(mcp_client, admin_token, "assign_gvfg_entry",
                    {"entry_id": seed["u4_new"].id, "project_ids": [999999]})
    assert unknown["isError"] is True


def test_assign_requires_assignment_manage(mcp_client, create_user, db_session):
    seed = _seed(db_session)
    admin = create_user("admin", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["mcp.access", "gvfg.import"])
    assert _call(mcp_client, token, "list_gvfg_entries")["isError"] is False
    result = _call(mcp_client, token, "assign_gvfg_entry",
                   {"entry_id": seed["u4_new"].id, "project_ids": [seed["u4"].id]})
    assert result["isError"] is True
    assert "assignment.manage" in result["content"][0]["text"]


def test_aid_after_commissioning_questions_it(mcp_client, admin_token, db_session):
    seed = _seed(db_session)
    # Planned commissioning 2025, but the edition still plans 50 of 120 Mio. € for 2026.
    entry = _entry(seed["new"], "02 G 600_A", "Stadtbahn Steilshoop", lines=[
        ("SUM", "160", "120", {"1967–2023": "30", "2025": "40", "2026": "50"}),
    ])
    entry.commissioning_planned = 2025
    project = Project(name="Stadtbahn Steilshoop", project_number="02 G 600_A", is_draft=False)
    entry.projects = [project]
    db_session.add_all([entry, project])
    db_session.commit()

    payload = _payload(_call(mcp_client, admin_token, "list_project_gvfg", {"project_id": project.id}))
    doubt = payload["ibn_doubt"]
    assert (doubt["ibn_year"], doubt["ibn_source"], doubt["edition"]) == (2025, "GVFG 2025–2029", "2025–2029")
    assert (doubt["aid_after"], doubt["aid_total"]) == (50.0, 120.0)
    assert doubt["periods"] == [{"label": "2026", "aid": 50.0}]
    assert doubt["entry_ids"] == [entry.id]

    progress = _payload(_call(mcp_client, admin_token, "get_project_progress", {"project_id": project.id}))
    assert progress["forecast"]["ibn_doubt"] == doubt

    # U4: commissioning 2030, no aid after it.
    u4 = _payload(_call(mcp_client, admin_token, "list_project_gvfg", {"project_id": seed["u4"].id}))
    assert u4["ibn_doubt"] is None
