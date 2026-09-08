"""Golden run of the Haushalt parser against the EP 12, Teil B report 2027.

The fixture is the recorded pdfplumber output (page text + table rows) of six
representative pages of the HH-Entwurf-2027 report: the first Bedarfsplan page,
the start of the Sammelvereinbarungen, the two pages carrying "SV Rest 2009/
2025", the TABELLENSUMMEN page, and the first page of Tabelle 2 and Tabelle 5.
Recording the extraction instead of committing the PDF keeps the fixture at
kilobytes while still exercising the real column layout, the section split and
the SV page-break recovery.

Values are asserted against the printed report — a wrong number here means a
wrong Budget time series in production.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dashboard_backend.tasks.haushalt import ExtractedPage, _parse_extracted_pages

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "haushalt_ep12_2027_pages.json"


@pytest.fixture(scope="module")
def result():
    pages = [
        ExtractedPage(number=entry["number"], text=entry["text"], rows=entry["rows"])
        for entry in json.loads(FIXTURE.read_text(encoding="utf-8"))
    ]
    return _parse_extracted_pages(pages, 2027, known_finve_ids=set())


def _row(result, finve_number: int):
    return next(r for r in result.rows if r.finve_number == finve_number)


# ---------------------------------------------------------------------------
# Segmentation — the other tables of Teil B must not reach the parser
# ---------------------------------------------------------------------------

def test_detects_the_tables_of_teil_b(result):
    assert [(s.number, s.title, s.imported) for s in result.sections] == [
        (1, "Bedarfsplanmaßnahmen", True),
        (2, "Lärmsanierung", False),
        (5, "Maßnahmen nach InvKG", False),
    ]


def test_only_bedarfsplan_rows_are_parsed(result):
    """Lärmsanierung and InvKG positions have no FinVe number; before the split
    they were appended to the last Sammel-FinVe of Tabelle 1."""
    assert len(result.rows) == 12
    assert _row(result, 452).name == "SV Rest 2025"
    assert _row(result, 452).erlaeuterung_projects == ["VDE 8.1 ABS Nürnberg- Fürth"]
    assert [t.label for t in _row(result, 452).proposed_titel_entries] == [
        "Kap. 1202, Titel 891 01",
        "Kap. 1408, Titel 891 52",
        "nachrichtlich: Eigenmittel der EIU gemäß BUV",
    ]


def test_tabellensummen_row_is_not_imported(result):
    assert all("TABELLENSUMMEN" not in row.name.upper() for row in result.rows)


# ---------------------------------------------------------------------------
# Column mapping
# ---------------------------------------------------------------------------

def test_column_map_comes_from_the_table_header(result):
    assert result.column_map.source == "header"
    assert result.column_map.missing == []
    by_field = {c.field: c for c in result.column_map.columns}
    assert by_field["year_planned"].index == 14
    assert by_field["year_planned"].header == "veranschlagt 2027"
    assert by_field["next_years"].header == "vorbehalten für 2028 ff."


# ---------------------------------------------------------------------------
# Values — asserted against the printed report
# ---------------------------------------------------------------------------

def test_regular_row_values(result):
    row = _row(result, 275)  # B0080, ABS Angermünde – Grenze D/PL
    assert row.name == "ABS Angermünde- Grenze D/PL"
    assert row.proposed_finve.starting_year == 2021
    budget = row.proposed_budget
    assert budget.lfd_nr == "B0080"
    assert budget.bedarfsplan_number == "N19"
    assert budget.cost_estimate_original == 379_844
    assert budget.cost_estimate_last_year == 526_942
    assert budget.cost_estimate_actual == 477_871
    assert budget.delta_previous_year == -49_071
    assert budget.delta_previous_year_relativ == -9.0
    assert budget.spent_two_years_previous == 168_091
    assert budget.allowed_previous_year == 83_494
    assert budget.year_planned == 77_859
    assert budget.next_years == 148_427


def test_titel_breakdown_of_a_regular_row(result):
    row = _row(result, 275)
    kap = [t for t in row.proposed_titel_entries if not t.is_nachrichtlich]
    assert [(t.titel_key, t.cost_estimate_aktuell) for t in kap] == [
        ("891_01", 241_852),
        ("891_03", 23_051),
        ("891_52", 212_968),
    ]
    nachrichtlich = [t for t in row.proposed_titel_entries if t.is_nachrichtlich]
    assert [(t.label, t.cost_estimate_aktuell) for t in nachrichtlich] == [
        ("nachrichtlich: Beteiligung Dritter", 76_949),
        ("nachrichtlich: Eigenmittel der EIU gemäß BUV", 87_521),
        ("nachrichtlich: Projektausgaben insgesamt, alle Quellen", 642_341),
    ]


def test_sammel_finve_row(result):
    row = _row(result, 451)  # YYY 451, SV Rest 2009
    assert row.is_sammel_finve is True
    assert row.proposed_budget.lfd_nr == "YYY"
    assert row.proposed_budget.cost_estimate_actual == 241_634
    assert row.proposed_budget.year_planned == 12_745
    # The Erläuterung lists the projects the Sammelvereinbarung funds
    assert row.erlaeuterung_projects[0] == "VDE 8.3"
    assert len(row.erlaeuterung_projects) == 9


def test_row_without_a_finve_number_becomes_unmatched(result):
    assert result.unmatched_rows == [
        {
            "raw_lfd_nr": "B0140",
            "raw_finve_number": None,
            "raw_bedarfsplan": "L 03",
            "raw_name": "ABS Berlin - Dresden, 2. Baustufe, Vorabmaßnahmen",
        }
    ]
