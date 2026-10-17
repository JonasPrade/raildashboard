"""MCP Fulda-Runde tools (feature-fulda-import.md): document → entries →
assignment → confirmation → derived observations and forecast."""

from __future__ import annotations

from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.schemas.users import UserRole
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    admin_token,
    mcp_client,
)


def _seed(db):
    parent = Project(name="ABS Köln – Düsseldorf – Dortmund / Münster")
    db.add(parent)
    db.flush()
    pfa = Project(name="RRX PFA 2.0", superior_project_id=parent.id)
    hamburg = Project(name="Großknoten Hamburg")
    db.add_all([pfa, hamburg])
    db.commit()
    return parent, pfa, hamburg


def _document(client, token):
    return _payload(
        _call(
            client,
            token,
            "create_fulda_document",
            {
                "year": 2026,
                "drucksache": "21/5855",
                "document_date": "2026-06-03",
                "answer_status": "TEILWEISE",
                "note": "Fragen 2, 4, 5, 9, 10: abhängig vom Haushalt 2027",
            },
        )
    )


def test_full_flow(mcp_client, admin_token, db_session):
    _, pfa, hamburg = _seed(db_session)
    doc = _document(mcp_client, admin_token)
    assert doc["year"] == 2026 and doc["total"] == 0

    # Same Drucksache twice → refused with a pointer to the existing id.
    again = _call(
        mcp_client,
        admin_token,
        "create_fulda_document",
        {"year": 2026, "drucksache": "21/5855", "document_date": "2026-06-03"},
    )
    assert again["isError"] is True
    assert str(doc["id"]) in again["content"][0]["text"]

    added = _payload(
        _call(
            mcp_client,
            admin_token,
            "add_fulda_entries",
            {
                "document_id": doc["id"],
                "entries": [
                    {
                        "raw_name": "ABS Köln – Düsseldorf – Dortmund / Münster",
                        "abschnitt": "RRX: PFA 2.0",
                        "category": "IN_LPH_3_4",
                        "raw_text": "ABS Köln – Düsseldorf – Dortmund / Münster | RRX: PFA 2.0, PFA 3.1 bis 3.2a",
                        "question_ref": "Frage 6",
                        "page": 5,
                        "attributed_to": "BMV",
                    },
                    {
                        "raw_name": "ABS Köln – Düsseldorf – Dortmund / Münster (RRX)",
                        "abschnitt": "PFA 2.0",
                        "category": "COMPLETES_LPH_3_4",
                        "raw_text": "ABS Köln – Düsseldorf – Dortmund / Münster (RRX): PFA 2.0",
                        "question_ref": "Frage 7",
                        "page": 7,
                        "expected_date": "2026-12-31",
                        "attributed_to": "DB",
                    },
                    {
                        "raw_name": "Großknoten Hamburg",
                        "abschnitt": "Kreuzungsbauwerk Wilhelmsburg",
                        "category": "COMPLETES_LPH_1",
                        "raw_text": "Großknoten Hamburg | Kreuzungsbauwerk Wilhelmsburg, …",
                        "question_ref": "Frage 3",
                    },
                ],
            },
        )
    )
    entries = added["entries"]
    assert [e["statement_kind"] for e in entries] == ["IST", "PROGNOSE", "PROGNOSE"]
    assert entries[1]["phase"] == "BAU"

    for entry in entries[:2]:
        _payload(
            _call(
                mcp_client,
                admin_token,
                "assign_fulda_entry",
                {"entry_id": entry["id"], "project_ids": [pfa.id], "note": "Teilprojekt RRX PFA 2.0"},
            )
        )
    _payload(
        _call(
            mcp_client,
            admin_token,
            "assign_fulda_entry",
            {"entry_id": entries[2]["id"], "project_ids": [hamburg.id], "note": "Oberprojekt"},
        )
    )

    open_entries = _payload(
        _call(mcp_client, admin_token, "list_fulda_entries", {"document_id": doc["id"], "only_open": True})
    )["entries"]
    assert len(open_entries) == 3
    assert open_entries[0]["assignment_note"] == "Teilprojekt RRX PFA 2.0"

    confirmed = _payload(
        _call(mcp_client, admin_token, "confirm_fulda_document", {"document_id": doc["id"]})
    )
    assert confirmed["confirmed_now"] == 3
    assert confirmed["document"]["confirmed"] == 3

    observations = (
        db_session.query(ProgressObservation)
        .filter(ProgressObservation.project_id == pfa.id, ProgressObservation.is_derived.is_(True))
        .order_by(ProgressObservation.is_expected)
        .all()
    )
    assert [(o.source_type, o.asserted_state, str(o.observed_date), o.is_expected) for o in observations] == [
        ("FULDA_RUNDE", "GENEHMIGUNGSPLANUNG", "2026-06-03", False),
        ("FULDA_RUNDE", "BAU", "2026-12-31", True),
    ]
    # The hint-only line (Lph 1) materialises nothing.
    assert (
        db_session.query(ProgressObservation)
        .filter(ProgressObservation.project_id == hamburg.id, ProgressObservation.is_derived.is_(True))
        .count()
        == 0
    )

    # The prognosis does not raise the phase but shows up in the forecast.
    view = progress_crud.get_progress_view(db_session, pfa.id)
    assert view["effective_phase"] == "GENEHMIGUNGSPLANUNG"
    bau = next(s for s in view["forecast"]["next_steps"] if s["phase"] == "BAU")
    assert (str(bau["expected_date"]), bau["source"]) == ("2026-12-31", "Fulda-Runde")


def test_validation_errors(mcp_client, admin_token, db_session):
    doc = _document(mcp_client, admin_token)
    bad = _call(
        mcp_client,
        admin_token,
        "add_fulda_entries",
        {
            "document_id": doc["id"],
            "entries": [{"raw_name": "X", "category": "QUATSCH", "raw_text": "X"}],
        },
    )
    assert bad["isError"] is True
    assert "QUATSCH" in bad["content"][0]["text"]
    no_note = _call(
        mcp_client, admin_token, "assign_fulda_entry", {"entry_id": 1, "project_ids": [], "note": " "}
    )
    assert no_note["isError"] is True


def test_requires_fulda_import(mcp_client, create_user, db_session):
    admin = create_user("admin", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["mcp.access", "progress.edit"])
    result = _call(mcp_client, token, "list_fulda_documents", {})
    assert result["isError"] is True
    assert "fulda.import" in result["content"][0]["text"]


def test_manual_fulda_observation_is_refused(mcp_client, admin_token, db_session):
    _, pfa, _ = _seed(db_session)
    result = _call(
        mcp_client,
        admin_token,
        "add_progress_observation",
        {"project_id": pfa.id, "track": "MAIN", "asserted_state": "BAU", "source_type": "FULDA_RUNDE"},
    )
    assert result["isError"] is True
