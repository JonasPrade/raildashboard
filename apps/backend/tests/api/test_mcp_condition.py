"""InfraGO-Zustandsbericht: MCP import with checks, release, public reads
(feature-zustandsbericht.md)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    admin_token,
    mcp_client,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "zustandsbericht_2025.json"
IMPORT = "/api/v1/import/condition"
PUBLIC = "/api/v1/condition"
STELLWERKE_REASON = "Tab. 5 S. 52: Stellwerke Mengen je Note 3.461, bewertet 3.686 — so gedruckt."


@pytest.fixture()
def editor(create_user):
    create_user("editor-zb", "pass123", UserRole.editor)
    return basic_auth_header("editor-zb", "pass123")


def _import_2025(client, token):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    _payload(_call(client, token, "create_condition_report", {
        "year": 2025, "title": data["title"], "source_url": data["source_url"],
        "price_basis": data["price_basis"],
    }))
    for table in data["tables"]:
        args = {"year": 2025, "domain": table["domain"], "scope": table["scope"],
                "region": table["region"], "values": table["values"]}
        if table["domain"] == "FAHRWEG" and table["scope"] == "GESAMT":
            args["override_reason"] = STELLWERKE_REASON
        _payload(_call(client, token, "set_condition_values", args))
    return data


def test_full_import_release_and_public_page(mcp_client, admin_token, editor):
    data = _import_2025(mcp_client, admin_token)

    check = _payload(_call(mcp_client, admin_token, "check_condition_report", {"year": 2025}))
    total = sum(len(t["values"]) for t in data["tables"])
    assert check["values"] == total and check["unchecked"] == total
    # The accepted mismatch is still reported, with its reason.
    assert [e["table"] for e in check["errors"]] == ["FAHRWEG GESAMT"]
    assert check["accepted_mismatches"][0]["reason"] == STELLWERKE_REASON
    assert check["gaps"] == []

    # Not public before the release.
    assert mcp_client.get(f"{PUBLIC}/reports").json() == []
    assert mcp_client.get(f"{PUBLIC}/reports/2025").status_code == 404

    released = mcp_client.post(f"{IMPORT}/reports/2025/release", headers=editor)
    assert released.status_code == 200 and released.json()["released"] == total

    reports = mcp_client.get(f"{PUBLIC}/reports").json()
    assert [r["year"] for r in reports] == [2025]
    year = mcp_client.get(f"{PUBLIC}/reports/2025").json()
    assert len(year["values"]) == total
    stellwerke = next(
        v for v in year["values"]
        if v["class_key"] == "fw_stellwerke" and v["scope"] == "GESAMT" and v["metric"] == "NOTE"
    )
    assert stellwerke["value"] == 4.02 and stellwerke["source_ref"] == "Tab. 5"
    assert any(c["key"] == "pb_empfangsgebaeude" for c in year["classes"])

    series = mcp_client.get(f"{PUBLIC}/series").json()
    notes = sorted(
        (v["reference_year"], v["value"]) for v in series
        if v["domain"] == "FAHRWEG" and v["scope"] == "GESAMT" and v["class_key"] is None
        and v["metric"] == "NOTE"
    )
    assert notes == [(2021, 2.93), (2022, 3.01), (2023, 3.03), (2024, 3.0), (2025, 3.0)]

    # A released year takes no more agent writes.
    refused = _call(mcp_client, admin_token, "set_condition_values", {
        "year": 2025, "domain": "FAHRWEG", "scope": "GESAMT",
        "values": [{"metric": "NOTE", "value": 3.1}],
    })
    assert refused["isError"] is True and "freigegeben" in refused["content"][0]["text"]


def test_misread_value_is_refused_and_nothing_written(mcp_client, admin_token):
    _payload(_call(mcp_client, admin_token, "create_condition_report", {"year": 2025}))
    dist = [18.7, 33.3, 23.1, 13.6, 2.3, 0.0]  # 32,1 misread as 23,1
    result = _call(mcp_client, admin_token, "set_condition_values", {
        "year": 2025, "domain": "FAHRWEG", "scope": "GESAMT",
        "values": [{"class_key": "fw_gleise", "metric": "VERTEILUNG_WBW", "grade": g, "value": v}
                   for g, v in enumerate(dist, start=1)],
    })
    assert result["isError"] is True
    assert "Gleise: Notenverteilung ergibt 91 % statt 100 %" in result["content"][0]["text"]
    stored = _payload(_call(mcp_client, admin_token, "get_condition_values", {"year": 2025}))
    assert stored["values"] == []


def test_table_is_checked_together_with_stored_values(mcp_client, admin_token):
    _payload(_call(mcp_client, admin_token, "create_condition_report", {"year": 2025}))
    write = {"year": 2025, "domain": "PERSONENBAHNHOF", "scope": "GESAMT"}
    _payload(_call(mcp_client, admin_token, "set_condition_values", {**write, "values": [
        {"metric": "WBW_BEWERTET", "value": 80.22},
        {"class_key": "pb_bahnsteige", "metric": "WBW_BEWERTET", "value": 25.22},
    ]}))
    # A second class pushes the classes past the total → refused.
    result = _call(mcp_client, admin_token, "set_condition_values", {**write, "values": [
        {"class_key": "pb_fahrtreppen", "metric": "WBW_BEWERTET", "value": 60},
    ]})
    assert result["isError"] is True and "Anlagenklassen ergeben" in result["content"][0]["text"]


def test_validation_of_table_and_classes(mcp_client, admin_token):
    _payload(_call(mcp_client, admin_token, "create_condition_report", {"year": 2025}))
    again = _call(mcp_client, admin_token, "create_condition_report", {"year": 2025})
    assert again["isError"] is True and "gibt es schon" in again["content"][0]["text"]

    cases = [
        ({"domain": "PERSONENBAHNHOF", "scope": "HLN"}, "nur beim Fahrweg"),
        ({"domain": "FAHRWEG", "scope": "LAND"}, "Länderkürzel"),
        ({"domain": "FAHRWEG", "scope": "GESAMT", "region": "BY"}, "nur mit scope LAND"),
    ]
    for table, message in cases:
        result = _call(mcp_client, admin_token, "set_condition_values", {
            "year": 2025, **table, "values": [{"metric": "NOTE", "value": 3}],
        })
        assert result["isError"] is True and message in result["content"][0]["text"], table
    wrong_domain = _call(mcp_client, admin_token, "set_condition_values", {
        "year": 2025, "domain": "FAHRWEG", "scope": "GESAMT",
        "values": [{"class_key": "pb_bahnsteige", "metric": "NOTE", "value": 3}],
    })
    assert wrong_domain["isError"] is True

    created = _payload(_call(mcp_client, admin_token, "create_condition_class", {
        "key": "fw_signale", "domain": "FAHRWEG", "name": "Signale", "unit": "Stk.",
        "trade": "LST", "reason": "Neu im Bericht 2026, Tab. 5",
    }))
    assert created["key"] == "fw_signale"
    classes = _payload(_call(mcp_client, admin_token, "list_condition_classes", {"domain": "FAHRWEG"}))
    assert classes["classes"][-1]["key"] == "fw_signale"
    assert classes["laender"]["BY"] == "Bayern"


def test_newer_report_wins_for_the_same_year(mcp_client, admin_token, editor):
    for year, note_2024 in ((2024, 3.10), (2025, 3.00)):
        _payload(_call(mcp_client, admin_token, "create_condition_report", {"year": year}))
        _payload(_call(mcp_client, admin_token, "set_condition_values", {
            "year": year, "domain": "FAHRWEG", "scope": "GESAMT",
            "values": [{"metric": "NOTE", "reference_year": 2024, "value": note_2024}],
        }))
        assert mcp_client.post(f"{IMPORT}/reports/{year}/release", headers=editor).status_code == 200
    series = mcp_client.get(f"{PUBLIC}/series").json()
    assert [(v["reference_year"], v["value"], v["report_year"]) for v in series] == [(2024, 3.0, 2025)]


def test_correct_value_and_delete_report(mcp_client, admin_token, editor):
    _payload(_call(mcp_client, admin_token, "create_condition_report", {"year": 2025}))
    _payload(_call(mcp_client, admin_token, "set_condition_values", {
        "year": 2025, "domain": "FAHRWEG", "scope": "HLN", "values": [
            {"metric": "WBW_BEWERTET", "value": 10},
            {"class_key": "fw_gleise", "metric": "WBW_BEWERTET", "value": 6},
            {"class_key": "fw_weichen", "metric": "WBW_BEWERTET", "value": 4},
        ],
    }))
    values = mcp_client.get(f"{IMPORT}/reports/2025/values", headers=editor).json()
    weichen = next(v for v in values if v["class_key"] == "fw_weichen")
    corrected = mcp_client.patch(f"{IMPORT}/values/{weichen['id']}", json={"value": 5}, headers=editor)
    assert corrected.status_code == 200
    body = corrected.json()
    assert body["value"]["status"] == "GEPRUEFT"
    assert body["warnings"] and "Anlagenklassen ergeben 11" in body["warnings"][0]

    assert mcp_client.delete(f"{IMPORT}/reports/2025", headers=editor).status_code == 204
    assert mcp_client.get(f"{IMPORT}/reports", headers=editor).json() == []


def test_pdf_upload_page_text_and_image(mcp_client, admin_token, editor):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Netzzustandsnote 3,00")
    pdf = doc.tobytes()
    doc.close()

    created = mcp_client.post(f"{IMPORT}/reports", json={"year": 2025}, headers=editor)
    assert created.status_code == 201 and created.json()["has_pdf"] is False
    no_pdf = _call(mcp_client, admin_token, "get_condition_page_text", {"year": 2025, "page": 1})
    assert no_pdf["isError"] is True and "kein PDF" in no_pdf["content"][0]["text"]

    uploaded = mcp_client.post(
        f"{IMPORT}/reports/2025/pdf",
        files={"pdf": ("zb.pdf", pdf, "application/pdf")},
        headers=editor,
    )
    assert uploaded.status_code == 200 and uploaded.json()["has_pdf"] is True

    text = _payload(_call(mcp_client, admin_token, "get_condition_page_text", {"year": 2025, "page": 1}))
    assert any("Netzzustandsnote" in line for line in text["lines"])
    image = _call(mcp_client, admin_token, "get_condition_page_image", {"year": 2025, "page": 1})
    assert image["isError"] is False and image["content"][0]["type"] == "image"
    png = mcp_client.get(f"{IMPORT}/reports/2025/page/1.png", headers=editor)
    assert png.status_code == 200 and png.content.startswith(b"\x89PNG")
    missing = _call(mcp_client, admin_token, "get_condition_page_text", {"year": 2025, "page": 9})
    assert missing["isError"] is True


def test_requires_condition_import(mcp_client, create_user, db_session):
    admin = create_user("admin", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["mcp.access", "progress.edit"])
    result = _call(mcp_client, token, "list_condition_reports", {})
    assert result["isError"] is True and "condition.import" in result["content"][0]["text"]

    create_user("viewer-zb", "pass123", UserRole.viewer)
    viewer = basic_auth_header("viewer-zb", "pass123")
    assert mcp_client.get(f"{IMPORT}/reports", headers=viewer).status_code == 403
    assert mcp_client.post(f"{IMPORT}/reports", json={"year": 2025}, headers=viewer).status_code == 403


def test_update_condition_report_changes_only_passed_fields(mcp_client, admin_token):
    created = _payload(_call(mcp_client, admin_token, "create_condition_report", {
        "year": 2025, "title": "Zustandsbericht 2025", "source_url": "https://example.org/zb.pdf",
        "note": "erster Lauf",
    }))
    updated = _payload(_call(mcp_client, admin_token, "update_condition_report", {
        "year": 2025, "price_basis": "Preisstand 2024", "published_on": "2026-05-12",
    }))
    assert updated["id"] == created["id"]
    assert updated["price_basis"] == "Preisstand 2024"
    assert updated["published_on"] == "2026-05-12"
    # Fields not passed keep their value.
    assert updated["title"] == "Zustandsbericht 2025"
    assert updated["source_url"] == "https://example.org/zb.pdf"
    assert updated["note"] == "erster Lauf"
    listed = _payload(_call(mcp_client, admin_token, "list_condition_reports", {}))["reports"]
    assert listed[0]["price_basis"] == "Preisstand 2024"

    empty = _call(mcp_client, admin_token, "update_condition_report", {"year": 2025})
    assert empty["isError"] is True and "Keine Änderung" in empty["content"][0]["text"]


def test_update_condition_report_unknown_year(mcp_client, admin_token):
    result = _call(mcp_client, admin_token, "update_condition_report", {
        "year": 1999, "price_basis": "Preisstand 2024",
    })
    assert result["isError"] is True and "1999 gibt es nicht" in result["content"][0]["text"]


def test_update_condition_report_refuses_released_year(mcp_client, admin_token, editor):
    _payload(_call(mcp_client, admin_token, "create_condition_report", {"year": 2025}))
    assert mcp_client.post(f"{IMPORT}/reports/2025/release", headers=editor).status_code == 200
    result = _call(mcp_client, admin_token, "update_condition_report", {
        "year": 2025, "price_basis": "Preisstand 2024",
    })
    assert result["isError"] is True and "freigegeben" in result["content"][0]["text"]
    report = _payload(_call(mcp_client, admin_token, "list_condition_reports", {}))["reports"][0]
    assert report["price_basis"] is None


def test_update_condition_report_requires_condition_import(mcp_client, create_user, db_session):
    admin = create_user("admin", "adminpass", UserRole.admin)
    token = _key_for(db_session, admin, scopes=["mcp.access", "progress.edit"])
    result = _call(mcp_client, token, "update_condition_report", {
        "year": 2025, "price_basis": "Preisstand 2024",
    })
    assert result["isError"] is True and "condition.import" in result["content"][0]["text"]
