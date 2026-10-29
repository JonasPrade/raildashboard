"""MCP Haushalt follow-up: open FinVes per report year, candidates, Sammel-FinVe
year links (with changelog and revert) and unmatched rows."""

from __future__ import annotations

import json
from datetime import datetime

from dashboard_backend.crud.sammel_finve_links import SAMMEL_YEARS_FIELD
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.haushalt.haushalts_parse_result import HaushaltsParseResult
from dashboard_backend.models.haushalt.unmatched_budget_row import UnmatchedBudgetRow
from dashboard_backend.models.projects.budget import Budget
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.project import Project
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    _role_user,
    admin_token,
    mcp_client,
)


def _seed(db):
    abs38 = Project(name="ABS 38 München – Mühldorf", is_draft=False)
    knoten = Project(name="Knoten Hamburg", is_draft=False)
    old = Project(name="Alpha-E alt", is_draft=False, is_archived=True)
    db.add_all([abs38, knoten, old])
    db.flush()
    old.replaced_by_project_id = knoten.id
    linked = Finve(id=2001, name="ABS 38 München–Mühldorf, 1. BA")
    unlinked = Finve(id=2002, name="ABS 38 Mühldorf–Freilassing")
    sammel = Finve(id=763, name="SV Lph. 1/2 A", is_sammel_finve=True)
    keyed = Finve(id=900000, name="Lärmsanierung", finve_key="t2:SV 52/2017", temporary_finve_number=True)
    db.add_all([linked, unlinked, sammel, keyed])
    db.flush()
    db.add_all(
        [
            FinveToProject(project_id=abs38.id, finve_id=linked.id),
            FinveToProject(project_id=knoten.id, finve_id=sammel.id, haushalt_year=2026),
            FinveToProject(project_id=old.id, finve_id=sammel.id, haushalt_year=2027),
            Budget(budget_year=2026, fin_ve=linked.id, bedarfsplan_number="B0038", lfd_nr="7"),
            Budget(budget_year=2027, fin_ve=linked.id, bedarfsplan_number="B0038", lfd_nr="7",
                   cost_estimate_actual=120),
            Budget(budget_year=2027, fin_ve=unlinked.id, bedarfsplan_number="B0038", lfd_nr="8"),
            Budget(budget_year=2026, fin_ve=sammel.id, sammel_finve=True),
            Budget(budget_year=2027, fin_ve=sammel.id, sammel_finve=True),
            Budget(budget_year=2027, fin_ve=keyed.id),
            HaushaltsParseResult(
                haushalt_year=2027, pdf_filename="teil_b_2027.pdf", status="SUCCESS",
                confirmed_at=datetime(2026, 9, 10),
                result_json={"year": 2027, "rows": [
                    {"row_key": "763", "finve_number": 763, "table_number": 1,
                     "name": "SV Lph. 1/2 A", "status": "update", "is_sammel_finve": True,
                     "erlaeuterung_projects": ["Knoten Hamburg"],
                     "review_notes": ["Projekt Alpha-E alt ist archiviert"]},
                    {"row_key": "t2:SV 52/2017", "finve_key": "t2:SV 52/2017", "table_number": 2,
                     "name": "Lärmsanierung", "status": "new"},
                ]},
            ),
            HaushaltsParseResult(haushalt_year=2028, pdf_filename="teil_b_2028.pdf", status="SUCCESS"),
            UnmatchedBudgetRow(haushalt_year=2027, raw_finve_number="B0140 L 03", raw_name="Rest"),
        ]
    )
    db.commit()
    return abs38, knoten, old


def test_list_haushalt_years_counts_open_work(mcp_client, admin_token, db_session):
    _seed(db_session)
    payload = _payload(_call(mcp_client, admin_token, "list_haushalt_years"))
    by_year = {y["year"]: y for y in payload["years"]}
    assert [y["year"] for y in payload["years"]] == [2028, 2027, 2026]
    y2027 = by_year[2027]
    assert y2027["finves"] == 4
    # 2002 and the keyed measure have no project; 763 only an archived one in 2027.
    assert y2027["finves_without_project"] == 3
    assert y2027["sammel_without_project"] == 1
    assert y2027["unmatched_open"] == 1
    assert y2027["imports"][0]["confirmed_at"] is not None
    assert by_year[2026]["finves_without_project"] == 0
    assert by_year[2028]["imports"][0]["confirmed_at"] is None


def test_list_haushalt_finves_open_only_and_parse_details(mcp_client, admin_token, db_session):
    _seed(db_session)
    payload = _payload(_call(mcp_client, admin_token, "list_haushalt_finves", {"open_only": True}))
    assert payload["haushalt_year"] == 2027
    assert [f["id"] for f in payload["finves"]] == [763, 2002, 900000]
    sammel = payload["finves"][0]
    assert sammel["open"] is True
    assert sammel["projects"][0]["is_archived"] is True
    assert sammel["erlaeuterung_projects"] == ["Knoten Hamburg"]
    assert sammel["review_notes"]
    assert payload["finves"][2]["table_number"] == 2

    table2 = _payload(_call(mcp_client, admin_token, "list_haushalt_finves", {"table_number": 2}))
    assert [f["id"] for f in table2["finves"]] == [900000]
    year2026 = _payload(_call(mcp_client, admin_token, "list_haushalt_finves", {"haushalt_year": 2026}))
    assert all(not f["open"] for f in year2026["finves"])


def test_suggest_projects_combines_reasons(mcp_client, admin_token, db_session):
    abs38, knoten, old = _seed(db_session)
    sammel = _payload(_call(mcp_client, admin_token, "suggest_haushalt_finve_projects",
                            {"finve_id": 763}))
    first = sammel["candidates"][0]
    assert first["id"] == knoten.id
    assert any(r.startswith("erlaeuterung 2027") for r in first["reasons"])
    assert "other_year 2026" in first["reasons"]
    # The archived project's 2027 link is handed on to its successor.
    assert "archived_link 2027" in first["reasons"]
    assert first["successor_of"] == [old.id]
    assert all(c["id"] != old.id for c in sammel["candidates"])

    regular = _payload(_call(mcp_client, admin_token, "suggest_haushalt_finve_projects",
                             {"finve_id": 2002}))
    top = regular["candidates"][0]
    assert top["id"] == abs38.id
    assert "bedarfsplan B0038 (FinVe 2001)" in top["reasons"]


def test_set_sammel_year_projects_logs_and_reverts(mcp_client, admin_token, db_session, client, create_user):
    abs38, knoten, old = _seed(db_session)
    # SQLite turns the partial unique indexes of finve_to_project into full ones,
    # so a project can hold only one link per FinVe here (Postgres: one per year).
    payload = _payload(_call(mcp_client, admin_token, "set_sammel_finve_year_projects", {
        "finve_id": 763, "haushalt_year": 2027, "project_ids": [abs38.id],
        "note": "Erläuterung nennt ABS 38",
    }))
    # Archived history stays next to the new link.
    assert [p["id"] for p in payload["years"]["2027"]] == [abs38.id, old.id]
    assert payload["changed_project_ids"] == [abs38.id]

    following = _payload(_call(mcp_client, admin_token, "set_sammel_finve_year_projects", {
        "finve_id": 763, "haushalt_year": 2026, "project_ids": [], "following_years": True,
    }))
    assert sorted(following["years"]) == ["2026", "2027"]
    assert following["years"]["2026"] == []
    assert [p["id"] for p in following["years"]["2027"]] == [old.id]
    assert following["changed_project_ids"] == [abs38.id, knoten.id]

    entry = (
        db_session.query(ChangeLog)
        .filter(ChangeLog.project_id == abs38.id)
        .order_by(ChangeLog.id.desc())
        .first()
        .entries[0]
    )
    assert entry.field_name == SAMMEL_YEARS_FIELD
    assert json.loads(entry.old_value) == {"finve_id": 763, "years": [2027]}
    assert json.loads(entry.new_value) == {"finve_id": 763, "years": []}

    create_user("reverter", "pw", UserRole.admin)
    response = client.post(f"/api/v1/projects/{abs38.id}/changelog/revert",
                           json={"changelog_entry_id": entry.id},
                           headers=basic_auth_header("reverter", "pw"))
    assert response.status_code == 200, response.text
    db_session.expire_all()
    links = db_session.query(FinveToProject).filter_by(project_id=abs38.id, finve_id=763).all()
    assert [link.haushalt_year for link in links] == [2027]


def test_set_sammel_year_projects_guards(mcp_client, admin_token, db_session):
    abs38, knoten, old = _seed(db_session)
    regular = _call(mcp_client, admin_token, "set_sammel_finve_year_projects",
                    {"finve_id": 2002, "haushalt_year": 2027, "project_ids": [abs38.id]})
    assert regular["isError"] is True
    assert "keine Sammel-FinVe" in regular["content"][0]["text"]
    archived = _call(mcp_client, admin_token, "set_sammel_finve_year_projects",
                     {"finve_id": 763, "haushalt_year": 2027, "project_ids": [old.id]})
    assert archived["isError"] is True
    assert "archiviert" in archived["content"][0]["text"]
    wrong_year = _call(mcp_client, admin_token, "set_sammel_finve_year_projects",
                       {"finve_id": 763, "haushalt_year": 2020, "project_ids": [abs38.id]})
    assert wrong_year["isError"] is True
    assert "nicht im Haushalt 2020" in wrong_year["content"][0]["text"]


def test_set_sammel_year_projects_needs_finve_edit(mcp_client, db_session):
    abs38, _, _ = _seed(db_session)
    token = _key_for(db_session, _role_user(db_session, "reader-hh", ["mcp.access"]))
    result = _call(mcp_client, token, "set_sammel_finve_year_projects",
                   {"finve_id": 763, "haushalt_year": 2027, "project_ids": [abs38.id]})
    assert result["isError"] is True
    assert "finve.edit" in result["content"][0]["text"]


def test_unmatched_rows_list_and_resolve(mcp_client, admin_token, db_session):
    _seed(db_session)
    rows = _payload(_call(mcp_client, admin_token, "list_haushalt_unmatched_rows"))["rows"]
    assert [r["raw_finve_number"] for r in rows] == ["B0140 L 03"]
    resolved = _payload(_call(mcp_client, admin_token, "resolve_haushalt_unmatched_row",
                              {"row_id": rows[0]["id"], "finve_id": 2002}))
    assert resolved["resolved_finve_id"] == 2002
    assert resolved["finve_has_budget_in_year"] is True
    assert _payload(_call(mcp_client, admin_token, "list_haushalt_unmatched_rows"))["rows"] == []
    again = _call(mcp_client, admin_token, "resolve_haushalt_unmatched_row",
                  {"row_id": rows[0]["id"], "finve_id": 2002})
    assert again["isError"] is True
