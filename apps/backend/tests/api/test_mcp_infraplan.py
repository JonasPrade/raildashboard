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
