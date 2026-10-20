"""Infraplan stage 2: review, suggestions, subprojects, confirmation, years,
open assignments (/api/v1/import/infraplan, /api/v1/admin)."""

from __future__ import annotations

from datetime import date

import pytest

from dashboard_backend.crud import infraplan_import as crud
from dashboard_backend.models.infraplan import (
    InfraplanEntry,
    InfraplanEntryProject,
    InfraplanParseResult,
    InfraplanReport,
)
from dashboard_backend.models.projects.project import Project
from dashboard_backend.schemas.infraplan_import import InfraplanParsedRow
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header

BASE = "/api/v1/import/infraplan"
ADMIN = "/api/v1/admin"


def row(section: str, lfd_nr: int, **values) -> dict:
    data = {
        "row_key": f"{section}-{lfd_nr}",
        "section": section,
        "lfd_nr": lfd_nr,
        "page": 34,
        "cost_kind": "GESAMTKOSTEN" if section.startswith("GVFG") else "GWU",
        **values,
    }
    return InfraplanParsedRow(**data).model_dump(mode="json")


def make_draft(db, rows: list[dict], *, year: int = 2026, warnings: list | None = None) -> InfraplanParseResult:
    record = InfraplanParseResult(
        year=year,
        file_name="infraplan.pdf",
        status="SUCCESS",
        result_json={"sections": [], "rows": rows, "footnotes": {}, "page_count": 160},
        warnings_json=warnings or [],
    )
    db.add(record)
    db.flush()
    return record


def project(db, name: str, **values) -> Project:
    item = Project(name=name, **values)
    db.add(item)
    db.flush()
    return item


@pytest.fixture()
def editor(create_user):
    create_user("editor-ipr", "pass123", UserRole.editor)
    return basic_auth_header("editor-ipr", "pass123")


# --- review ------------------------------------------------------------------


def test_get_draft_lists_referenced_projects(client, editor, db_session):
    p = project(db_session, "ABS Magdeburg – Stendal – Uelzen")
    draft = make_draft(
        db_session,
        [row("BP_A", 1, project_ids=[p.id], assignment_source="FUZZY"), row("BP_A", 2)],
    )

    body = client.get(f"{BASE}/parse-result/{draft.id}", headers=editor).json()

    assert body["projects"][str(p.id)]["name"] == p.name
    assert body["assigned_count"] == 1
    assert body["previous_year"] is None
    assert body["report_year_exists"] is False


def test_patch_row_sets_projects_values_and_source(client, editor, db_session):
    p = project(db_session, "Knoten Hamburg")
    draft = make_draft(db_session, [row("BP_B", 1, ibn_year=2030)])

    resp = client.patch(
        f"{BASE}/parse-result/{draft.id}/rows/BP_B-1",
        json={"project_ids": [p.id], "note": "Name passt", "values": {"ibn_year": 2031}},
        headers=editor,
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["project_ids"] == [p.id]
    assert body["assignment_source"] == "MANUAL"
    assert body["assignment_note"] == "Name passt"
    assert body["assigned_by"] == "editor-ipr"
    assert body["ibn_year"] == 2031


def test_patch_row_unknown_project_or_row(client, editor, db_session):
    draft = make_draft(db_session, [row("BP_B", 1)])

    missing_project = client.patch(
        f"{BASE}/parse-result/{draft.id}/rows/BP_B-1", json={"project_ids": [999999]}, headers=editor
    )
    missing_row = client.patch(
        f"{BASE}/parse-result/{draft.id}/rows/BP_B-9", json={"project_ids": []}, headers=editor
    )

    assert missing_project.status_code == 404
    assert missing_row.status_code == 404


def test_apply_suggestions_takes_strong_hits_only(client, editor, db_session):
    strong = project(db_session, "Stark")
    weak = project(db_session, "Schwach")
    draft = make_draft(
        db_session,
        [
            row("BP_C", 1, suggestions=[{"project_id": strong.id, "confidence": 0.9, "reason": "FUZZY"}]),
            row("BP_C", 2, suggestions=[{"project_id": weak.id, "confidence": 0.6, "reason": "FUZZY"}]),
        ],
    )

    resp = client.post(
        f"{BASE}/parse-result/{draft.id}/apply-suggestions", json={"min_confidence": 0.85}, headers=editor
    )

    assert resp.json() == {"applied": 1, "unassigned": 1}
    rows = {r["row_key"]: r for r in db_session.get(InfraplanParseResult, draft.id).result_json["rows"]}
    assert rows["BP_C-1"]["project_ids"] == [strong.id]
    assert rows["BP_C-1"]["assignment_source"] == "FUZZY"
    assert rows["BP_C-2"]["project_ids"] == []


def test_create_subproject_replaces_parent_link(client, editor, db_session):
    parent = project(db_session, "PB 07: ABS Karlsruhe – Basel")
    draft = make_draft(
        db_session,
        [row("BP_A", 3, massnahme="Abschnitt 9.2", project_ids=[parent.id], assignment_source="FUZZY")],
    )

    resp = client.post(
        f"{BASE}/parse-result/{draft.id}/rows/BP_A-3/subproject",
        json={"parent_id": parent.id},
        headers=editor,
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    created = db_session.get(Project, body["project_id"])
    assert created.name == "Abschnitt 9.2"
    assert created.superior_project_id == parent.id
    assert created.is_draft is True
    assert body["row"]["project_ids"] == [created.id]


# --- confirm / delete ----------------------------------------------------------


def test_confirm_writes_year_entries_and_links(client, editor, db_session):
    p = project(db_session, "ABS Magdeburg – Stendal – Uelzen")
    draft = make_draft(
        db_session,
        [
            row(
                "BP_A",
                20,
                primary_number="E.1637290101",
                project_numbers=["E.1637290101"],
                state_raw="Bau",
                under_construction=True,
                ibn_raw="2030",
                ibn_year=2030,
                cost_mio=1720.48,
                footnote_refs=[14],
                footnotes={"14": "GWU bezieht sich auf Teil A 20 und 33"},
                parl_state="NICHT_VEREINBART",
                project_ids=[p.id],
                assignment_source="NUMBER",
            ),
            row(
                "BP_A",
                33,
                cost_ref_raw="Ref. Teil A 20",
                cost_ref={"section": "BP_A", "lfd_nr": 20, "resolved": True, "cost_mio": 1720.48},
            ),
        ],
    )

    resp = client.post(
        f"{BASE}/confirm",
        json={"parse_result_id": draft.id, "published_on": "2026-10-06"},
        headers=editor,
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["entries"] == 2
    assert resp.json()["links"] == 1
    assert resp.json()["unassigned"] == 1
    report = db_session.query(InfraplanReport).filter_by(year=2026).one()
    assert report.published_on == date(2026, 10, 6)
    assert report.title == "Infraplan 2026"
    entries = {e.lfd_nr: e for e in db_session.query(InfraplanEntry).filter_by(report_id=report.id)}
    assert float(entries[20].cost_mio) == 1720.48
    assert entries[20].footnotes == {"14": "GWU bezieht sich auf Teil A 20 und 33"}
    assert entries[33].cost_ref_entry_id == entries[20].id
    link = db_session.query(InfraplanEntryProject).one()
    assert (link.project_id, link.assignment_source) == (p.id, "NUMBER")
    assert db_session.get(InfraplanParseResult, draft.id).confirmed_at is not None

    # A confirmed draft no longer takes changes.
    patch = client.patch(f"{BASE}/parse-result/{draft.id}/rows/BP_A-33", json={"project_ids": []}, headers=editor)
    assert patch.status_code == 409


def test_confirm_refuses_warnings_unless_forced(client, editor, db_session):
    draft = make_draft(
        db_session,
        [row("BP_A", 2)],
        warnings=[{"kind": "GAP", "section": "BP_A", "lfd_nr": 1, "message": "BP_A: laufende Nummer 1 fehlt."}],
    )

    refused = client.post(f"{BASE}/confirm", json={"parse_result_id": draft.id}, headers=editor)
    forced = client.post(f"{BASE}/confirm", json={"parse_result_id": draft.id, "force": True}, headers=editor)

    assert refused.status_code == 409
    assert "Warnung" in refused.json()["detail"]
    assert forced.status_code == 200


def test_second_year_refused_delete_and_reconfirm(client, editor, db_session):
    p = project(db_session, "Projekt")
    first = make_draft(db_session, [row("BP_A", 1, project_ids=[p.id], assignment_source="MANUAL")])
    second = make_draft(db_session, [row("BP_A", 1)])
    assert client.post(f"{BASE}/confirm", json={"parse_result_id": first.id}, headers=editor).status_code == 200

    duplicate = client.post(f"{BASE}/confirm", json={"parse_result_id": second.id}, headers=editor)
    assert duplicate.status_code == 409

    assert client.delete(f"{BASE}/report/2026", headers=editor).status_code == 204
    assert db_session.query(InfraplanReport).count() == 0
    assert db_session.query(InfraplanEntry).count() == 0
    assert db_session.query(InfraplanEntryProject).count() == 0
    assert db_session.get(InfraplanParseResult, first.id).confirmed_at is None

    again = client.post(f"{BASE}/confirm", json={"parse_result_id": first.id}, headers=editor)
    assert again.status_code == 200
    assert db_session.query(InfraplanEntry).count() == 1


def test_delete_keeps_other_years(client, editor, db_session):
    older = make_draft(db_session, [row("BP_A", 1)], year=2026)
    newer = make_draft(db_session, [row("BP_A", 1)], year=2027)
    for draft in (older, newer):
        client.post(f"{BASE}/confirm", json={"parse_result_id": draft.id}, headers=editor)

    client.delete(f"{BASE}/report/2027", headers=editor)

    assert [r.year for r in db_session.query(InfraplanReport)] == [2026]
    assert db_session.query(InfraplanEntry).count() == 1
    listed = client.get(f"{BASE}/report", headers=editor).json()
    assert [(r["year"], r["entry_count"]) for r in listed] == [(2026, 1)]


def test_delete_unknown_year(client, editor):
    assert client.delete(f"{BASE}/report/1999", headers=editor).status_code == 404


# --- previous year ---------------------------------------------------------------


def test_previous_year_projects_missing_from_new_draft(client, editor, db_session):
    kept = project(db_session, "Bleibt")
    renamed = project(db_session, "Umbenannt")
    old = make_draft(
        db_session,
        [
            row("BP_A", 1, primary_number="E.1", project_ids=[kept.id], assignment_source="MANUAL"),
            row("BP_A", 2, primary_number="E.2", project_ids=[renamed.id], assignment_source="MANUAL"),
        ],
        year=2026,
    )
    client.post(f"{BASE}/confirm", json={"parse_result_id": old.id}, headers=editor)
    new = make_draft(db_session, [row("BP_A", 1, primary_number="E.1")], year=2027)

    body = client.get(f"{BASE}/parse-result/{new.id}", headers=editor).json()

    assert body["previous_year"] == 2026
    assert [m["project_id"] for m in body["missing_from_previous"]] == [renamed.id]
    assert body["missing_from_previous"][0]["entries"][0]["primary_number"] == "E.2"


def test_reparse_suggests_previous_year_number(db_session):
    """Matching: a link of year N is suggested in N+1 through the number."""
    from dashboard_backend.schemas.infraplan_import import InfraplanParseOutput

    p = project(db_session, "Völlig anderer Name")
    report = InfraplanReport(year=2026)
    db_session.add(report)
    db_session.flush()
    entry = InfraplanEntry(report_id=report.id, section="BP_A", lfd_nr=1, primary_number="E.1637290101")
    db_session.add(entry)
    db_session.flush()
    db_session.add(InfraplanEntryProject(entry_id=entry.id, project_id=p.id, assignment_source="MANUAL"))
    draft = make_draft(db_session, [], year=2027)

    output = InfraplanParseOutput(
        sections=[],
        rows=[InfraplanParsedRow(**row("BP_A", 5, primary_number="E.1637290101"))],
    )
    crud.save_parse_output(db_session, draft, output, [], [])

    saved = draft.result_json["rows"][0]
    assert saved["suggestions"] == [{"project_id": p.id, "confidence": 1.0, "reason": "NUMBER"}]
    assert saved["project_ids"] == [p.id]
    assert saved["assignment_source"] == "NUMBER"


def test_reparse_keeps_assignments(db_session):
    from dashboard_backend.schemas.infraplan_import import InfraplanParseOutput

    p = project(db_session, "Von Hand")
    draft = make_draft(
        db_session, [row("BP_B", 1, project_ids=[p.id], assignment_source="MANUAL", assignment_note="x")]
    )
    output = InfraplanParseOutput(sections=[], rows=[InfraplanParsedRow(**row("BP_B", 1))])

    crud.save_parse_output(db_session, draft, output, [], [])

    saved = draft.result_json["rows"][0]
    assert (saved["project_ids"], saved["assignment_source"], saved["assignment_note"]) == ([p.id], "MANUAL", "x")


# --- open assignments --------------------------------------------------------------


def test_unassigned_entries_and_assign(client, editor, db_session):
    p = project(db_session, "Später zugeordnet")
    draft = make_draft(db_session, [row("BP_D", 4, massnahme="Ausbau")])
    client.post(f"{BASE}/confirm", json={"parse_result_id": draft.id}, headers=editor)

    listed = client.get(f"{ADMIN}/unassigned-infraplan-entries", headers=editor).json()
    assert [(e["section"], e["lfd_nr"], e["report_year"]) for e in listed] == [("BP_D", 4, 2026)]

    resp = client.patch(
        f"{ADMIN}/unassigned-infraplan-entries/{listed[0]['id']}/assign",
        json={"project_ids": [p.id]},
        headers=editor,
    )
    assert resp.status_code == 204
    assert client.get(f"{ADMIN}/unassigned-infraplan-entries", headers=editor).json() == []
    link = db_session.query(InfraplanEntryProject).one()
    assert (link.project_id, link.assignment_source) == (p.id, "MANUAL")


def test_review_requires_permission(client, create_user, db_session):
    create_user("viewer-ipr", "pass123", UserRole.viewer)
    draft = make_draft(db_session, [row("BP_A", 1)])
    viewer = basic_auth_header("viewer-ipr", "pass123")

    assert client.post(f"{BASE}/confirm", json={"parse_result_id": draft.id}, headers=viewer).status_code == 403
    assert client.delete(f"{BASE}/report/2026", headers=viewer).status_code == 403
