"""MCP Infraplan tools (feature-infraplan-import.md → "MCP & Skill"): draft →
suggestions → agent assignment → subproject → confirmation → KPI values."""

from __future__ import annotations

import fitz
import pytest

from dashboard_backend.models.infraplan import InfraplanEntryProject, InfraplanKpiValue
from dashboard_backend.models.projects.project import Project
from dashboard_backend.utils.file_storage import save_infraplan_pdf
from tests.api.test_infraplan_review import make_draft, project, row
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    _role_user,
    admin_token,
    mcp_client,
)


@pytest.fixture(autouse=True)
def pdf_dir(tmp_path, monkeypatch):
    from dashboard_backend.core.config import settings

    monkeypatch.setattr(settings, "infraplan_pdf_dir", str(tmp_path / "infraplan"))


def _seed(db):
    parent = project(db, "PB 07: ABS Karlsruhe – Basel")
    hit = project(db, "Knoten Hamburg")
    draft = make_draft(
        db,
        [
            row("BP_A", 1, suggestions=[{"project_id": hit.id, "confidence": 1.0, "reason": "NUMBER"}]),
            row("BP_A", 2, massnahme="Abschnitt 9.2 Schliengen – Eimeldingen"),
            row("BP_B", 1, massnahme="Unklar"),
        ],
    )
    db.commit()
    return parent, hit, draft


def test_full_flow(mcp_client, admin_token, db_session):
    parent, hit, draft = _seed(db_session)

    drafts = _payload(_call(mcp_client, admin_token, "list_infraplan_drafts"))
    assert drafts["drafts"][0]["id"] == draft.id
    assert drafts["drafts"][0]["warnings"] == []

    applied = _payload(_call(mcp_client, admin_token, "apply_infraplan_suggestions", {"draft_id": draft.id}))
    assert applied == {"applied": 1, "still_open": 2}

    open_rows = _payload(
        _call(mcp_client, admin_token, "get_infraplan_draft", {"draft_id": draft.id, "only_open": True})
    )
    assert [r["row_key"] for r in open_rows["rows"]] == ["BP_A-2", "BP_B-1"]

    created = _payload(
        _call(
            mcp_client,
            admin_token,
            "create_infraplan_subproject",
            {"draft_id": draft.id, "row_key": "BP_A-2", "parent_id": parent.id},
        )
    )
    sub = db_session.get(Project, created["project_id"])
    assert sub.superior_project_id == parent.id
    assert created["row"]["assignment_source"] == "AGENT"

    no_note = _call(
        mcp_client,
        admin_token,
        "assign_infraplan_row",
        {"draft_id": draft.id, "row_key": "BP_B-1", "project_ids": [hit.id], "note": " "},
    )
    assert no_note["isError"] is True

    assigned = _payload(
        _call(
            mcp_client,
            admin_token,
            "assign_infraplan_row",
            {"draft_id": draft.id, "row_key": "BP_B-1", "project_ids": [hit.id], "note": "Name passt"},
        )
    )
    assert (assigned["assignment_source"], assigned["assignment_note"]) == ("AGENT", "Name passt")

    confirmed = _payload(
        _call(
            mcp_client,
            admin_token,
            "confirm_infraplan_import",
            {"draft_id": draft.id, "published_on": "2026-10-06"},
        )
    )
    assert confirmed["entries"] == 3 and confirmed["unassigned"] == 0
    sources = {link.assignment_source for link in db_session.query(InfraplanEntryProject)}
    assert sources == {"NUMBER", "AGENT"}

    # After the confirmation the same tool corrects the confirmed entry.
    moved = _payload(
        _call(
            mcp_client,
            admin_token,
            "assign_infraplan_row",
            {"draft_id": draft.id, "row_key": "BP_B-1", "project_ids": [parent.id], "note": "korrigiert"},
        )
    )
    assert moved["project_ids"] == [parent.id]

    entries = _payload(_call(mcp_client, admin_token, "get_project_infraplan", {"project_id": hit.id}))
    assert [e["section"] for e in entries["entries"]] == ["BP_A"]


def test_confirm_refused_with_warnings(mcp_client, admin_token, db_session):
    draft = make_draft(
        db_session,
        [row("BP_A", 2)],
        warnings=[{"kind": "GAP", "section": "BP_A", "lfd_nr": 1, "message": "BP_A: laufende Nummer 1 fehlt."}],
    )
    db_session.commit()

    result = _call(mcp_client, admin_token, "confirm_infraplan_import", {"draft_id": draft.id})

    assert result["isError"] is True
    assert "Warnung" in result["content"][0]["text"]


def test_kpi_values_land_unchecked(mcp_client, admin_token, db_session):
    draft = make_draft(db_session, [row("BP_A", 1)])
    db_session.commit()
    _payload(_call(mcp_client, admin_token, "confirm_infraplan_import", {"draft_id": draft.id}))

    kpis = _payload(_call(mcp_client, admin_token, "list_infraplan_kpis"))
    assert "neu_gebaute_gleis_km" in {k["key"] for k in kpis["kpis"]}

    written = _payload(
        _call(
            mcp_client,
            admin_token,
            "set_infraplan_kpi_values",
            {
                "year": 2026,
                "values": [
                    {"kpi_key": "neu_gebaute_gleis_km", "year": 2025, "value_kind": "IST", "value": 41, "source_page": 60}
                ],
            },
        )
    )
    assert written["written"] == 1
    assert db_session.query(InfraplanKpiValue).one().status == "UNGEPRUEFT"

    values = _payload(_call(mcp_client, admin_token, "get_infraplan_kpi_values", {"year": 2026}))
    assert values["values"][0]["status"] == "UNGEPRUEFT"


def test_page_image_is_image_content(mcp_client, admin_token, db_session):
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Steuerungskennzahl")
    pdf = doc.tobytes()
    doc.close()
    draft = make_draft(db_session, [])
    draft.pdf_path = save_infraplan_pdf(draft.id, pdf)
    db_session.commit()

    result = _call(mcp_client, admin_token, "get_infraplan_page_image", {"draft_id": draft.id, "page": 1})

    assert result["isError"] is False
    assert result["content"][0]["type"] == "image"
    assert result["content"][0]["mimeType"] == "image/png"
    missing = _call(mcp_client, admin_token, "get_infraplan_page_image", {"draft_id": draft.id, "page": 9})
    assert missing["isError"] is True


def test_requires_permission(mcp_client, db_session):
    reader = _role_user(db_session, "reader-ip", ["mcp.access"])
    token = _key_for(db_session, reader)
    draft = make_draft(db_session, [row("BP_A", 1)])
    db_session.commit()

    for name, args in (
        ("list_infraplan_drafts", {}),
        ("confirm_infraplan_import", {"draft_id": draft.id}),
        ("set_infraplan_kpi_values", {"year": 2026, "values": []}),
    ):
        result = _call(mcp_client, token, name, args)
        assert result["isError"] is True
        assert "infraplan.import" in result["content"][0]["text"]


def test_data_gap_lists_open_rows(mcp_client, admin_token, db_session):
    draft = make_draft(db_session, [row("BP_D", 3, massnahme="Offen")])
    db_session.commit()
    _payload(_call(mcp_client, admin_token, "confirm_infraplan_import", {"draft_id": draft.id}))

    gaps = _payload(_call(mcp_client, admin_token, "list_data_gaps", {"gaps": ["infraplan_unassigned"]}))

    assert gaps["infraplan_unassigned"]["count"] == 1
    assert gaps["infraplan_unassigned"]["draft_id"] == draft.id
    assert gaps["infraplan_unassigned"]["entries"][0]["row_key"] == "BP_D-3"


# --- Ausbau 2027: batch calls, compact view, page text ------------------------------


def test_assign_rows_in_one_call_with_partial_success(mcp_client, admin_token, db_session):
    a = project(db_session, "Knoten Hamburg")
    b = project(db_session, "Knoten Köln")
    draft = make_draft(db_session, [row("BP_A", 1), row("BP_A", 2), row("BP_A", 3)])
    db_session.commit()

    result = _payload(
        _call(
            mcp_client,
            admin_token,
            "assign_infraplan_rows",
            {
                "draft_id": draft.id,
                "rows": [
                    {"row_key": "BP_A-1", "project_ids": [a.id], "note": "Name passt"},
                    {"row_key": "BP_A-2", "project_ids": [a.id, b.id], "note": "Sammelzeile"},
                    {"row_key": "BP_A-9", "project_ids": [a.id], "note": "gibt es nicht"},
                    {"row_key": "BP_A-3", "project_ids": [99999], "note": "falsches Projekt"},
                    {"row_key": "BP_A-3", "project_ids": [b.id], "note": " "},
                ],
            },
        )
    )

    assert (result["ok"], result["failed"]) == (2, 3)
    assert [r["ok"] for r in result["rows"]] == [True, True, False, False, False]
    assert "BP_A-9" in result["rows"][2]["error"]
    assert "99999" in result["rows"][3]["error"]
    assert "Begründung" in result["rows"][4]["error"]
    db_session.refresh(draft)
    rows = {r["row_key"]: r for r in draft.result_json["rows"]}
    assert rows["BP_A-2"]["project_ids"] == [a.id, b.id]
    assert (rows["BP_A-1"]["assignment_source"], rows["BP_A-1"]["assignment_note"]) == ("AGENT", "Name passt")
    assert not rows["BP_A-3"].get("project_ids")


def test_assign_rows_after_confirmation_changes_the_year(mcp_client, admin_token, db_session):
    a = project(db_session, "Knoten Hamburg")
    b = project(db_session, "Knoten Köln")
    draft = make_draft(db_session, [row("BP_A", 1, project_ids=[a.id]), row("BP_A", 2)])
    db_session.commit()
    _payload(_call(mcp_client, admin_token, "confirm_infraplan_import", {"draft_id": draft.id}))

    result = _payload(
        _call(
            mcp_client,
            admin_token,
            "assign_infraplan_rows",
            {
                "draft_id": draft.id,
                "rows": [
                    {"row_key": "BP_A-1", "project_ids": [b.id], "note": "korrigiert"},
                    {"row_key": "BP_A-2", "project_ids": [a.id], "note": "nachgetragen"},
                ],
            },
        )
    )

    assert result["confirmed_year"] == 2026 and result["ok"] == 2
    links = {(link.project_id, link.note) for link in db_session.query(InfraplanEntryProject)}
    assert links == {(b.id, "korrigiert"), (a.id, "nachgetragen")}


def test_create_subprojects_with_and_without_parent(mcp_client, admin_token, db_session):
    parent = project(db_session, "ABS/NBS Karlsruhe – Basel")
    draft = make_draft(
        db_session,
        [
            row("BP_A", 1, massnahme="Abschnitt 9.2 Haltingen – Weil am Rhein", project_ids=[parent.id]),
            row("GVFG_A", 8, primary_number="07 D 2825_A", massnahme="Elektrifizierung der Ahrtalbahn"),
        ],
    )
    db_session.commit()

    result = _payload(
        _call(
            mcp_client,
            admin_token,
            "create_infraplan_subprojects",
            {
                "draft_id": draft.id,
                "items": [
                    {"row_key": "BP_A-1", "parent_id": parent.id},
                    {"row_key": "GVFG_A-8", "note": "GVFG-Vorhaben ohne Elternprojekt"},
                    {"row_key": "BP_A-1", "parent_id": 99999},
                ],
            },
        )
    )

    assert (result["ok"], result["failed"]) == (2, 1)
    sub = db_session.get(Project, result["rows"][0]["project_id"])
    assert (sub.superior_project_id, sub.is_draft) == (parent.id, True)
    assert result["rows"][0]["project_ids"] == [sub.id]  # the parent link is replaced
    own = db_session.get(Project, result["rows"][1]["project_id"])
    assert (own.superior_project_id, own.project_number, own.name) == (
        None, "07 D 2825_A", "Elektrifizierung der Ahrtalbahn"
    )


def test_create_subproject_after_confirmation(mcp_client, admin_token, db_session):
    parent = project(db_session, "Knoten Frankfurt")
    draft = make_draft(db_session, [row("BP_A", 34, massnahme="Gleis 25", project_ids=[parent.id])])
    db_session.commit()
    _payload(_call(mcp_client, admin_token, "confirm_infraplan_import", {"draft_id": draft.id}))

    created = _payload(
        _call(
            mcp_client,
            admin_token,
            "create_infraplan_subproject",
            {"draft_id": draft.id, "row_key": "BP_A-34", "parent_id": parent.id},
        )
    )

    links = [link.project_id for link in db_session.query(InfraplanEntryProject)]
    assert links == [created["project_id"]]


def test_compact_draft_lists_all_sections(mcp_client, admin_token, db_session):
    hit = project(db_session, "Knoten Hamburg")
    draft = make_draft(
        db_session,
        [
            row("BP_A", 1, bezeichnung="Großknoten Hamburg", massnahme="Elmshorn",
                suggestions=[{"project_id": hit.id, "confidence": 0.9, "reason": "CONTEXT", "detail": "Teilprojekt"}]),
            row("GVFG_A", 1, primary_number="07 D 2825_A", laender="Rheinland-Pfalz", project_ids=[hit.id]),
        ],
    )
    db_session.commit()

    result = _payload(_call(mcp_client, admin_token, "get_infraplan_draft", {"draft_id": draft.id, "compact": True}))

    assert result["total_matching"] == 2
    first, second = result["rows"]
    assert first == {
        "row_key": "BP_A-1",
        "bezeichnung": "Großknoten Hamburg",
        "massnahme": "Elmshorn",
        "best": {"project_id": hit.id, "name": "Knoten Hamburg", "confidence": 0.9, "reason": "CONTEXT", "detail": "Teilprojekt"},
    }
    assert (second["number"], second["laender"], second["project_ids"]) == ("07 D 2825_A", "Rheinland-Pfalz", [hit.id])
    assert result["assigned_projects"] == {str(hit.id): "Knoten Hamburg"}
    assert "projects" not in result


def test_page_text_and_kpi_suggestions(mcp_client, admin_token, db_session):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 60), "Neu gebaute Gleiskilometer")
    for x, year, value in ((100, 2024, "65"), (150, 2025, "67"), (200, 2026, "64")):
        page.insert_text((x, 200), value)
        page.insert_text((x - 6, 260), str(year))
    pdf = doc.tobytes()
    doc.close()
    draft = make_draft(db_session, [])
    draft.pdf_path = save_infraplan_pdf(draft.id, pdf)
    db_session.commit()

    text = _payload(_call(mcp_client, admin_token, "get_infraplan_page_text", {"draft_id": draft.id, "page": 1}))
    assert any("2024@" in line and "2026@" in line for line in text["lines"])

    suggested = _payload(
        _call(mcp_client, admin_token, "suggest_infraplan_kpi_values", {"draft_id": draft.id, "page": 1})
    )
    (chart,) = suggested["charts"]
    assert [(v["year"], v["value"], v["kind_guess"]) for v in chart["values"]] == [
        (2024, 65.0, "IST"), (2025, 67.0, "IST"), (2026, 64.0, "ZIEL")
    ]
    missing = _call(mcp_client, admin_token, "get_infraplan_page_text", {"draft_id": draft.id, "page": 5})
    assert missing["isError"] is True
