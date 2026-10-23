"""MCP FinVe search: list_finves and get_finve find FinVes independent of a
project link (by number, name or Bedarfsplan number); unlink_finve removes
wrong project links."""

from __future__ import annotations

from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.schemas.users import UserRole
from dashboard_backend.models.projects.budget import Budget
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.project import Project
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    admin_token,
    mcp_client,
)


def _seed(db):
    project = Project(name="ABS 38 München–Mühldorf", is_draft=False)
    linked = Finve(id=2001, name="ABS 38 München–Mühldorf, 1. BA", starting_year=2010)
    unlinked = Finve(id=2002, name="ABS 38 Mühldorf–Freilassing", starting_year=2015)
    other = Finve(id=3001, name="NBS Hamburg–Hannover")
    sammel = Finve(id=4001, name="SV Planung LPH 1-2", is_sammel_finve=True)
    db.add_all([project, linked, unlinked, other, sammel])
    db.flush()
    db.add_all(
        [
            FinveToProject(project_id=project.id, finve_id=linked.id),
            Budget(budget_year=2024, fin_ve=linked.id, bedarfsplan_number="B0038", lfd_nr="7",
                   cost_estimate_actual=100),
            Budget(budget_year=2025, fin_ve=linked.id, bedarfsplan_number="B0038", lfd_nr="7",
                   cost_estimate_actual=120),
            Budget(budget_year=2025, fin_ve=unlinked.id, bedarfsplan_number="B0038", lfd_nr="8",
                   cost_estimate_actual=300),
            Budget(budget_year=2024, fin_ve=other.id, bedarfsplan_number="B0011", lfd_nr="1"),
        ]
    )
    db.commit()
    return project


def _ids(payload):
    return [f["id"] for f in payload["finves"]]


def test_search_by_name_finds_unlinked_finves(mcp_client, admin_token, db_session):
    project = _seed(db_session)
    payload = _payload(_call(mcp_client, admin_token, "list_finves", {"search": "abs 38"}))
    assert payload["total"] == 2
    assert _ids(payload) == [2001, 2002]
    first, second = payload["finves"]
    assert first["projects"] == [{"id": project.id, "name": project.name}]
    assert first["bedarfsplan_numbers"] == ["B0038"]
    assert first["budget_years"] == [2024, 2025]
    assert first["latest_cost_estimate_actual"] == 120
    assert second["projects"] == []


def test_search_by_number_and_bedarfsplan_number(mcp_client, admin_token, db_session):
    _seed(db_session)
    by_number = _payload(_call(mcp_client, admin_token, "list_finves", {"search": "3001"}))
    assert _ids(by_number) == [3001]
    by_search = _payload(_call(mcp_client, admin_token, "list_finves", {"search": "b0038"}))
    assert _ids(by_search) == [2001, 2002]
    by_filter = _payload(
        _call(mcp_client, admin_token, "list_finves", {"bedarfsplan_number": "B0011"})
    )
    assert _ids(by_filter) == [3001]


def test_filters(mcp_client, admin_token, db_session):
    _seed(db_session)
    unassigned = _payload(_call(mcp_client, admin_token, "list_finves", {"has_project": False}))
    assert _ids(unassigned) == [2002, 3001, 4001]
    assigned = _payload(_call(mcp_client, admin_token, "list_finves", {"has_project": True}))
    assert _ids(assigned) == [2001]
    year = _payload(_call(mcp_client, admin_token, "list_finves", {"budget_year": 2025}))
    assert _ids(year) == [2001, 2002]
    sammel = _payload(_call(mcp_client, admin_token, "list_finves", {"is_sammel_finve": True}))
    assert _ids(sammel) == [4001]
    page = _payload(_call(mcp_client, admin_token, "list_finves", {"limit": 2, "offset": 1}))
    assert page["total"] == 4
    assert _ids(page) == [2002, 3001]


def test_get_finve(mcp_client, admin_token, db_session):
    project = _seed(db_session)
    payload = _payload(_call(mcp_client, admin_token, "get_finve", {"finve_id": 2001}))
    assert payload["name"] == "ABS 38 München–Mühldorf, 1. BA"
    assert [b["budget_year"] for b in payload["budgets"]] == [2024, 2025]
    assert payload["projects"] == [{"id": project.id, "name": project.name}]

    missing = _call(mcp_client, admin_token, "get_finve", {"finve_id": 9999})
    assert missing["isError"] is True
    assert "nicht gefunden" in missing["content"][0]["text"]


def test_unlink_finve_removes_only_the_given_projects(mcp_client, admin_token, db_session):
    project = _seed(db_session)
    other = Project(name="ABS 38 Mühldorf–Freilassing", is_draft=False)
    unrelated = Project(name="NBS Hamburg–Hannover", is_draft=False)
    db_session.add_all([other, unrelated])
    db_session.flush()
    db_session.add(FinveToProject(project_id=other.id, finve_id=2001))
    db_session.commit()

    payload = _payload(_call(mcp_client, admin_token, "unlink_finve",
                             {"finve_id": 2001, "project_ids": [project.id, unrelated.id]}))
    assert payload["removed"] == [project.id]
    assert payload["not_linked"] == [unrelated.id]
    assert payload["projects"] == [{"id": other.id, "name": other.name}]
    db_session.expire_all()
    remaining = db_session.query(FinveToProject.project_id).filter_by(finve_id=2001).all()
    assert [r[0] for r in remaining] == [other.id]


def test_unlink_sammel_finve_removes_year_scoped_links(mcp_client, admin_token, db_session):
    project = _seed(db_session)
    # One row only: SQLite ignores the partial unique indexes, so a second year collides.
    db_session.add(FinveToProject(project_id=project.id, finve_id=4001, haushalt_year=2025))
    db_session.commit()
    payload = _payload(_call(mcp_client, admin_token, "unlink_finve",
                             {"finve_id": 4001, "project_ids": [project.id]}))
    assert payload["removed"] == [project.id]
    assert payload["projects"] == []
    db_session.expire_all()
    assert db_session.query(FinveToProject).filter_by(finve_id=4001).count() == 0


def test_unlink_finve_errors(mcp_client, admin_token, db_session):
    project = _seed(db_session)
    missing = _call(mcp_client, admin_token, "unlink_finve",
                    {"finve_id": 9999, "project_ids": [project.id]})
    assert missing["isError"] is True
    assert "nicht gefunden" in missing["content"][0]["text"]
    empty = _call(mcp_client, admin_token, "unlink_finve", {"finve_id": 2001, "project_ids": []})
    assert empty["isError"] is True


def test_unlink_finve_requires_assignment_manage(mcp_client, create_user, db_session):
    project = _seed(db_session)
    admin = create_user("admin", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["mcp.access"])
    result = _call(mcp_client, token, "unlink_finve", {"finve_id": 2001, "project_ids": [project.id]})
    assert result["isError"] is True
    assert "assignment.manage" in result["content"][0]["text"]
    assert db_session.query(FinveToProject).filter_by(finve_id=2001).count() == 1
