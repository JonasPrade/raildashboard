"""Golden run of the Haushalt parser against the EP 12, Teil B report 2027.

The fixture is the recorded pdfplumber output (page text + table rows) of nine
representative pages of the HH-Entwurf-2027 report, covering all five tables of
Teil B: the first Bedarfsplan page, the Sammelvereinbarungen and the
TABELLENSUMMEN page of Tabelle 1, and the first pages of Lärmsanierung, ERTMS,
Kleine und Mittlere Maßnahmen and InvKG — including the ERTMS and KMM pages
whose rows pdfplumber merges and the importer has to rebuild.  Recording the
extraction instead of committing the PDF keeps the fixture at kilobytes while
still exercising the real column layout, the table split, the identity of
measures without a FinVe number and the SV page-break recovery.

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


def _row(result, row_key: str):
    return next(r for r in result.rows if r.row_key == row_key)


def _rows_of(result, table_number: int):
    return [r for r in result.rows if r.table_number == table_number]


# ---------------------------------------------------------------------------
# Segmentation — every table of Teil B is read, and kept apart
# ---------------------------------------------------------------------------

def test_reads_every_table_of_teil_b(result):
    assert [(s.number, s.title, s.imported) for s in result.sections] == [
        (1, "Bedarfsplanmaßnahmen", True),
        (2, "Lärmsanierung", True),
        (3, "ERTMS", True),
        (4, "Kleine und Mittlere Maßnahmen der Bundesschienenwege", True),
        (5, "Maßnahmen nach InvKG", True),
    ]


def test_every_row_carries_the_table_it_came_from(result):
    assert all(row.table_number is not None for row in result.rows)
    assert {s.number: s.row_count for s in result.sections} == {
        number: len(_rows_of(result, number)) for number in (1, 2, 3, 4, 5)
    }


def test_rows_of_one_table_do_not_bleed_into_another(result):
    """Before the split, the rows of Tabellen 2–5 were appended to the last
    Sammel-FinVe of Tabelle 1 as Titel and Erläuterung sub-entries."""
    sv_rest_2025 = _row(result, "452")
    assert sv_rest_2025.name == "SV Rest 2025"
    assert sv_rest_2025.erlaeuterung_projects == ["VDE 8.1 ABS Nürnberg- Fürth"]
    assert [t.label for t in sv_rest_2025.proposed_titel_entries] == [
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


def test_every_table_maps_its_columns_from_its_own_header(result):
    assert all(s.column_map_source == "header" for s in result.sections)


# ---------------------------------------------------------------------------
# Tabelle 1 — values asserted against the printed report
# ---------------------------------------------------------------------------

def test_bedarfsplan_row_values(result):
    row = _row(result, "275")  # B0080, ABS Angermünde – Grenze D/PL
    assert row.finve_number == 275
    assert row.finve_key is None
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


def test_titel_breakdown_of_a_bedarfsplan_row(result):
    row = _row(result, "275")
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
    row = _row(result, "451")  # YYY 451, SV Rest 2009
    assert row.is_sammel_finve is True
    assert row.proposed_budget.lfd_nr == "YYY"
    assert row.proposed_budget.cost_estimate_actual == 241_634
    assert row.proposed_budget.year_planned == 12_745
    assert row.erlaeuterung_projects[0] == "VDE 8.3"
    assert len(row.erlaeuterung_projects) == 9


def test_bedarfsplan_row_without_a_finve_number_becomes_unmatched(result):
    """Tabelle 1 lists projects that have no FinVe number *yet* — they keep the
    established unmatched flow rather than getting a synthetic identity."""
    assert result.unmatched_rows == [
        {
            "raw_lfd_nr": "B0140",
            "raw_finve_number": None,
            "raw_bedarfsplan": "L 03",
            "raw_name": "ABS Berlin - Dresden, 2. Baustufe, Vorabmaßnahmen",
            "table_number": 1,
        }
    ]


# ---------------------------------------------------------------------------
# Tabellen 2–5 — measures identified by a key instead of a FinVe number
# ---------------------------------------------------------------------------

def test_laermsanierung_measure(result):
    row = _row(result, "t2:SV 52/2017")
    assert row.table_number == 2
    assert row.finve_number is None
    assert row.proposed_finve.temporary_finve_number is True
    budget = row.proposed_budget
    assert budget.fin_ve is None  # assigned on confirm from the Finve row
    assert budget.cost_estimate_original == 53_301
    assert budget.cost_estimate_actual == 91_369
    assert budget.spent_two_years_previous == 66_383
    assert budget.allowed_previous_year == 24_986
    assert budget.year_planned is None  # printed as "-"
    assert [t.label for t in row.proposed_titel_entries] == ["Kap. 1202, Titel 891 05"]


def test_measure_without_an_identifier_is_keyed_by_name_and_year(result):
    row = _row(result, "t2:foerderrichtlinie-laermsanierung-an-bestehenden-schienenwege-1999")
    assert row.name.startswith("Förderrichtlinie Lärmsanierung")
    assert row.proposed_finve.starting_year == 1999
    assert row.proposed_budget.cost_estimate_actual == 1_786_452
    assert row.proposed_budget.year_planned == 9_194
    # The Förderrichtlinie breaks down into named positions instead of Kap./Titel
    labels = [t.label for t in row.proposed_titel_entries]
    assert "Dortmund Knoten 1 - Z1108" in labels
    assert "A -Sammelposition:" in labels


def test_ertms_measure_on_a_page_whose_rows_had_to_be_rebuilt(result):
    """pdfplumber collapses the ERTMS pages into one cell per section; the
    rebuilt rows must carry the printed values, not a shifted column."""
    row = _row(result, "t3:F08Q0770")
    assert row.table_number == 3
    assert row.name == "Baustufen I + II des Digitalen Knotens Stuttgart -Planung und Bau -"
    budget = row.proposed_budget
    assert budget.cost_estimate_original == 216_050
    assert budget.cost_estimate_last_year == 482_442
    assert budget.cost_estimate_actual == 383_234
    assert budget.spent_two_years_previous == 222_377
    assert budget.allowed_previous_year == 79_422
    assert budget.spending_residues is None  # printed as "-"
    # Veranschlagt is 33.186, not -33.186: the "-" of the Ausgabereste column
    # overhangs its rule and must not be read as the sign of the next column.
    assert budget.year_planned == 33_186
    assert budget.next_years == 48_249


def test_ertms_measure_takes_its_identifier_from_the_finve_column(result):
    """On the rebuilt pages the "YYY" marker and the F-number sit in separate
    columns, so the identity has to come from the FinVe column."""
    keys = {r.row_key for r in _rows_of(result, 3)}
    assert "t3:F08Q0770" in keys
    assert "t3:F21Q0774 F21Q0790" in keys


def test_kleine_und_mittlere_massnahmen_measure(result):
    row = _row(result, "t4:SV 68/2022")
    budget = row.proposed_budget
    assert budget.cost_estimate_original == 14_880
    assert budget.cost_estimate_last_year == 348_666
    assert budget.cost_estimate_actual == 383_187
    assert budget.spent_two_years_previous == 58_008
    assert budget.allowed_previous_year == 174_972
    assert budget.spending_residues == 27_302
    assert budget.year_planned == 89_821
    assert budget.next_years == 33_084


def test_repeated_identifier_gets_a_distinct_key(result):
    """The report lists "F 03 E 0793" twice — the original agreement and its
    amendment. Both must survive as separate measures."""
    first = _row(result, "t4:F 03 E 0793")
    second = _row(result, "t4:F 03 E 0793#2")
    assert first.proposed_budget.cost_estimate_actual == 17_025
    assert second.proposed_budget.cost_estimate_actual == 2_489
    assert first.finve_key != second.finve_key


def test_invkg_measure_is_keyed_by_its_running_number(result):
    row = _row(result, "t5:B0094")
    assert row.table_number == 5
    assert row.name.startswith("Mitteldeutsches Revier:")
    assert row.proposed_finve.starting_year == 2021
    budget = row.proposed_budget
    assert budget.cost_estimate_original == 6_861
    assert budget.cost_estimate_last_year == 21_983
    assert budget.cost_estimate_actual == 21_983
    assert budget.spent_two_years_previous == 8_406
    assert budget.allowed_previous_year == 3_878
    assert budget.year_planned == 3_186
    assert budget.next_years == 6_513
    assert [(t.titel_key, t.cost_estimate_aktuell) for t in row.proposed_titel_entries] == [
        ("891_01", 760),
        ("891_13", 7_646),
        ("893_45", 13_577),
    ]


def test_keyed_measures_never_claim_a_finve_number(result):
    keyed = [r for r in result.rows if r.finve_key is not None]
    assert keyed, "expected measures without a FinVe number"
    assert all(r.proposed_finve.id is None for r in keyed)
    assert all(r.proposed_finve.temporary_finve_number for r in keyed)
    assert all(r.row_key == r.finve_key for r in keyed)


def test_row_keys_are_unique(result):
    keys = [r.row_key for r in result.rows]
    assert len(keys) == len(set(keys))
