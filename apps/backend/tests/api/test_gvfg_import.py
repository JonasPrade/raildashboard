"""GVFG import: suggestions, confirm into an edition, annex, reads, permissions."""

from __future__ import annotations

import io
from decimal import Decimal

from dashboard_backend.crud import gvfg as gvfg_crud
from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.gvfg import GvfgEntry, GvfgProgram
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.schemas.users import UserRole
from dashboard_backend.services.gvfg_parser import parse_gvfg_pdf
from tests.api.test_mcp_server import _key_for
from tests.gvfg_pdf_factory import Row
from tests.gvfg_pdf_factory import build_pdf
from tests.unit.test_gvfg_parser import _financial_page, _meta


def _stage(db, pages, filename="gvfg.pdf"):
    result = parse_gvfg_pdf(io.BytesIO(build_pdf(pages))).to_json()
    result["suggestions"] = gvfg_crud.build_suggestions(db, result["entries"])
    record = gvfg_crud.save_parse_result(
        db, filename=filename, result_json=result, status="SUCCESS", error=None, user_info=None
    )
    db.commit()
    return record


def _annex_page():
    row = Row(_meta("1", "02 G 673_A", "U3 Haltestelle Fuhlsbüttler Straße"), [("", ["40,00", "30,00", "18,00"])])
    return {"land": "Hamburg", "kind": "kommunale Vorhaben", "informational": True, "rows": [row], "total": []}


def _projects(db):
    group = ProjectGroup(name="Gemeindeverkehrsfinanzierungsgesetz", short_name="GVFG", color="#000")
    u4 = Project(name="Hamburger Hochbahn, Verlängerung der U4 zur Horner Geest", project_number="02 G 509 _ A")
    u2 = Project(name="Teilautomatisierung U2/U4", project_number="02 G 4518_T")
    other = Project(name="S-Bahn Hamburg", project_number="01 D 508_A")
    db.add_all([group, u4, u2, other])
    db.commit()
    return group, u4, u2


def test_suggestions(db_session):
    _, u4, u2 = _projects(db_session)
    record = _stage(db_session, [_financial_page()])
    by_key = record.result_json["suggestions"]["by_key"]
    assert by_key["02 G 509_A"]["selected"] == [u4.id]
    assert by_key["02 G 509_A"]["source"] == "key"
    assert by_key["02 G 4518_A"]["selected"] == [u2.id]
    assert by_key["02 G 4518_A"]["source"] == "key_without_suffix"
    assert "Schlüssel stimmt nur ohne Suffix überein" in by_key["02 G 4518_A"]["flags"]
    assert str(u4.id) in record.result_json["suggestions"]["projects"]


def test_confirm_annex_and_reads(client, create_user, db_session):
    editor = create_user("editor", "editorpass", UserRole.editor)
    headers = {"Authorization": f"Bearer {_key_for(db_session, editor)}"}
    group, u4, u2 = _projects(db_session)
    record = _stage(db_session, [_financial_page()])

    response = client.post(
        f"/api/v1/import/gvfg/parse-result/{record.id}/confirm",
        json={"assignments": {"02 G 509_A": [u4.id]}, "create_projects": ["02 G 4518_A"]},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"entries": 2, "links": 2, "projects_created": 1, "groups_added": 2}

    program = db_session.query(GvfgProgram).one()
    assert (program.year_from, program.has_annex) == (2025, False)
    created = db_session.query(Project).filter_by(project_number="02 G 4518_A").one()
    assert [g.short_name for g in created.project_groups] == ["GVFG"]
    assert created.is_draft is True
    entry = db_session.query(GvfgEntry).filter_by(key="02 G 4518_A").one()
    assert [p.id for p in entry.projects] == [created.id]
    db_session.refresh(u4)
    assert [g.short_name for g in u4.project_groups] == ["GVFG"]
    assert db_session.query(ChangeLog).filter_by(project_id=created.id, action="CREATE").count() == 1

    again = client.post(
        f"/api/v1/import/gvfg/parse-result/{record.id}/confirm", json={}, headers=headers
    )
    assert again.status_code == 400

    # The annex adds the informational part to the same edition.
    annex = _stage(db_session, [_annex_page()], filename="anhang.pdf")
    response = client.post(
        f"/api/v1/import/gvfg/parse-result/{annex.id}/confirm", json={}, headers=headers
    )
    assert response.status_code == 200, response.text
    db_session.expire_all()
    parts = sorted((e.key, e.part) for e in db_session.query(GvfgEntry))
    assert parts == [
        ("02 G 4518_A", "finanzrelevant"),
        ("02 G 509_A", "finanzrelevant"),
        ("02 G 673_A", "nachrichtlich"),
    ]

    programs = client.get("/api/v1/gvfg/programs").json()
    assert [p["year_from"] for p in programs] == [2025]
    assert [p["label"] for p in programs[0]["periods"]] == ["1967–2023", "2024", "2025", "ab 2030"]
    entries = client.get(f"/api/v1/gvfg/programs/{program.id}/entries").json()
    u4_entry = next(e for e in entries if e["key"] == "02 G 509_A")
    assert u4_entry["projects"] == [{"id": u4.id, "name": u4.name}]
    assert Decimal(u4_entry["amounts"][0]["aid_total"]) == Decimal("278.67")
    assert Decimal(u4_entry["amounts"][0]["periods"]["2025"]) == Decimal("39.20")

    parent = Project(name="U-Bahn Hamburg")
    db_session.add(parent)
    db_session.flush()
    u4.superior_project_id = parent.id
    db_session.commit()
    assert client.get(f"/api/v1/gvfg/projects/{parent.id}/entries").json() == []
    children = client.get(f"/api/v1/gvfg/projects/{parent.id}/entries?with_subprojects=true").json()
    assert [e["key"] for e in children] == ["02 G 509_A"]

    for_project = client.get(f"/api/v1/gvfg/projects/{u4.id}/entries").json()
    assert [e["key"] for e in for_project] == ["02 G 509_A"]
    assert for_project[0]["program"]["year_from"] == 2025

    # A later parse suggests the projects linked in the edition before.
    record_2 = _stage(db_session, [_financial_page()])
    assert record_2.result_json["suggestions"]["by_key"]["02 G 4518_A"]["source"] == "previous"


def test_reimport_replaces_periods(client, create_user, db_session):
    """A re-import of the financial part drops year columns an older parse read
    wrongly (e.g. a header typo stored as its own column) and keeps the links."""
    editor = create_user("editor", "editorpass", UserRole.editor)
    headers = {"Authorization": f"Bearer {_key_for(db_session, editor)}"}
    _, u4, _ = _projects(db_session)
    first = _stage(db_session, [_financial_page()])
    client.post(
        f"/api/v1/import/gvfg/parse-result/{first.id}/confirm",
        json={"assignments": {"02 G 509_A": [u4.id]}},
        headers=headers,
    )
    program = db_session.query(GvfgProgram).one()
    program.periods = program.periods + [{"label": "1967–2022", "year_from": 1967, "year_to": 2022, "kind": "ausgezahlt"}]
    db_session.commit()

    again = _stage(db_session, [_financial_page()])
    selected = again.result_json["suggestions"]["by_key"]["02 G 509_A"]["selected"]
    response = client.post(
        f"/api/v1/import/gvfg/parse-result/{again.id}/confirm",
        json={"assignments": {"02 G 509_A": selected}},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    db_session.expire_all()
    program = db_session.query(GvfgProgram).one()
    assert [p["label"] for p in program.periods] == ["1967–2023", "2024", "2025", "ab 2030"]
    entry = db_session.query(GvfgEntry).filter_by(key="02 G 509_A").one()
    assert [p.id for p in entry.projects] == [u4.id]


def test_import_needs_permission(client, create_user, db_session):
    viewer = create_user("viewer", "viewerpass", UserRole.viewer)
    headers = {"Authorization": f"Bearer {_key_for(db_session, viewer)}"}
    record = _stage(db_session, [_financial_page()])
    assert client.get("/api/v1/import/gvfg/parse-result", headers=headers).status_code == 403
    assert (
        client.post(
            f"/api/v1/import/gvfg/parse-result/{record.id}/confirm", json={}, headers=headers
        ).status_code
        == 403
    )


def test_unassigned_and_assign(client, create_user, db_session):
    editor = create_user("editor", "editorpass", UserRole.editor)
    headers = {"Authorization": f"Bearer {_key_for(db_session, editor)}"}
    group, u4, u2 = _projects(db_session)
    record = _stage(db_session, [_financial_page()])
    client.post(
        f"/api/v1/import/gvfg/parse-result/{record.id}/confirm",
        json={"assignments": {"02 G 509_A": [u4.id], "02 G 4518_A": []}},
        headers=headers,
    )

    open_entries = client.get("/api/v1/admin/unassigned-gvfg-entries", headers=headers).json()
    assert [e["key"] for e in open_entries] == ["02 G 4518_A"]
    entry_id = open_entries[0]["id"]

    assert (
        client.patch(
            f"/api/v1/admin/unassigned-gvfg-entries/{entry_id}/assign", json={"project_ids": [999999]}, headers=headers
        ).status_code
        == 422
    )
    response = client.patch(
        f"/api/v1/admin/unassigned-gvfg-entries/{entry_id}/assign", json={"project_ids": [u2.id]}, headers=headers
    )
    assert response.status_code == 204, response.text
    assert client.get("/api/v1/admin/unassigned-gvfg-entries", headers=headers).json() == []
    db_session.refresh(u2)
    assert [g.short_name for g in u2.project_groups] == ["GVFG"]
