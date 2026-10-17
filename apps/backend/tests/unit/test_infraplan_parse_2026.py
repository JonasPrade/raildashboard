"""Parser of the Infraplan measure tables against the Infraplan 2026.

The fixture holds stage 1 of the parser (words with position and font size
plus the header tables) for pages 33–56 of the Infraplan 2026, written by
``scripts/dump_infraplan_pages.py``. The PDF itself is not in the repository.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from dashboard_backend.tasks.infraplan import PageData, parse_pages

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "infraplan_2026_pages.json"

# Row counts as printed in the Infraplan 2026 (running numbers 1..n).
EXPECTED_ROWS = {
    "BP_A": 38,
    "BP_B": 40,
    "BP_C": 71,
    "BP_D": 34,
    "GVFG_A": 42,
    "GVFG_C": 41,
    "INVKG": 5,
}


@pytest.fixture(scope="module")
def raw_pages() -> list[dict]:
    return json.loads(FIXTURE.read_text())["pages"]


@pytest.fixture(scope="module")
def parsed(raw_pages):
    return parse_pages([PageData.from_dict(p) for p in raw_pages])


@pytest.fixture(scope="module")
def rows(parsed):
    return {row.row_key: row for row in parsed.output.rows}


def test_row_counts_per_section_without_warnings(parsed):
    counts = {s.key: s.row_count for s in parsed.output.sections}
    assert counts == EXPECTED_ROWS
    assert len(parsed.output.rows) == sum(EXPECTED_ROWS.values())
    assert parsed.warnings == []


def test_running_numbers_are_complete(parsed):
    for section, count in EXPECTED_ROWS.items():
        numbers = [r.lfd_nr for r in parsed.output.rows if r.section == section]
        assert numbers == list(range(1, count + 1)), section


def test_example_row_teil_a_20(rows):
    row = rows["BP_A-20"]
    assert row.page == 34
    assert row.primary_number == "E.1637290101"
    assert row.bezeichnung == "PB 03: ABS Magdeburg – Stendal – Uelzen (Ostkorridor Nord)"
    assert row.massnahme == (
        "2gl. Einbindung Bf Stendal und Ausbau Str. bis Hohenwulsch und Salzwedel – Uelzen"
    )
    assert row.laender == "Niedersachsen/Sachsen-Anhalt"
    assert row.under_construction is True
    assert row.ibn_year == 2030 and row.ibn_qualifier is None
    assert row.parl_state == "NICHT_VEREINBART"


def test_superscript_footnote_is_split_off(rows):
    row = rows["BP_A-20"]
    # Printed as "1.720,48¹⁴" — the marker must not end up in the number.
    assert row.cost_raw == "1.720,48"
    assert row.cost_mio == 1720.48
    assert row.cost_kind == "GWU"
    assert row.footnote_refs == [14]
    assert row.footnotes["14"].startswith("Der GWU-Wert in Höhe von 1.720,48 Mio. €")
    assert "Teil A 33" in row.footnotes["14"]


def test_cost_reference_is_resolved(rows):
    row = rows["BP_A-10"]
    assert row.cost_mio is None
    assert row.cost_ref_raw == "Ref. Teil B 20 | E.1637290100"
    assert row.cost_ref is not None
    assert (row.cost_ref.section, row.cost_ref.lfd_nr) == ("BP_B", 20)
    assert row.cost_ref.resolved is True
    assert row.cost_ref.cost_mio == rows["BP_B-20"].cost_mio == 876.15
    # The reference inside the same section and a superscript after the number.
    assert rows["BP_A-33"].cost_ref.cost_mio == 1720.48
    assert rows["BP_A-22"].footnote_refs == [15]


def test_ibn_is_normalised(rows):
    assert (rows["BP_B-5"].ibn_raw, rows["BP_B-5"].ibn_year, rows["BP_B-5"].ibn_qualifier) == (
        "bis 2035", 2035, "BIS",
    )
    assert (rows["BP_A-3"].ibn_year, rows["BP_A-3"].ibn_qualifier) == (None, "OFFEN")
    assert (rows["GVFG_A-7"].ibn_year, rows["GVFG_A-7"].ibn_qualifier) == (2024, "SPANNE")
    assert (rows["GVFG_C-20"].ibn_year, rows["GVFG_C-20"].ibn_qualifier) == (2029, "SPANNE")


def test_state_and_befassung(rows):
    assert rows["BP_A-34"].baurecht is True and rows["BP_A-34"].lph_to == 4
    assert (rows["BP_B-1"].lph_from, rows["BP_B-1"].lph_to) == (3, 4)
    assert rows["BP_B-1"].parl_state == "ABGESCHLOSSEN"
    assert rows["BP_B-6"].parl_state == "LAEUFT"
    assert rows["BP_C-8"].parl_state == "VORGESEHEN"
    assert rows["BP_D-1"].state_raw is None and rows["BP_D-1"].ibn_qualifier == "OFFEN"


def test_project_numbers(rows):
    assert rows["BP_A-12"].project_numbers == ["E.1637230040", "X.016030472300201"]
    assert rows["BP_A-12"].primary_number == "E.1637230040"
    assert rows["BP_D-1"].project_numbers == []
    assert rows["GVFG_A-8"].primary_number == "07 D 2825_A"
    assert rows["GVFG_A-8"].cost_kind == "GESAMTKOSTEN"
    assert rows["INVKG-1"].primary_number == "InvKG Nr. 6"


def test_hyphenation_across_lines(rows):
    assert rows["BP_A-10"].bezeichnung == "PB 08: ABS Hannover – Berlin (Lehrter Stammbahn)"
    assert rows["BP_A-10"].laender == "Brandenburg/Sachsen-Anhalt"


def test_gvfg_superscript_after_cost(rows):
    # "10,01²⁴" on page 52
    assert rows["GVFG_A-11"].cost_mio == 10.01
    assert rows["GVFG_A-11"].footnote_refs == [24]


def test_sections_change_mid_page(rows):
    # Page 47 ends Teil C and starts Teil D, page 53 ends Kat. A and starts Kat. C.
    assert rows["BP_C-71"].page == 47 and rows["BP_D-1"].page == 47
    assert rows["GVFG_A-42"].page == 53 and rows["GVFG_C-1"].page == 53


def test_page_without_header_reuses_last_layout(raw_pages, parsed):
    """Follow-up pages of Teil D and GVFG Kat. A without a header row."""
    pages = copy.deepcopy(raw_pages)
    for page in pages:
        if page["number"] in (48, 49, 50, 52):
            header = page["tables"][0]["bbox"]
            page["tables"] = []
            # Drop the header words too, as on a page that prints none.
            page["words"] = [
                w for w in page["words"] if not (header[1] - 1 <= w["top"] <= header[3] + 1)
            ]
    reparsed = parse_pages([PageData.from_dict(p) for p in pages])
    assert {s.key: s.row_count for s in reparsed.output.sections} == EXPECTED_ROWS
    assert reparsed.warnings == []
    before = {r.row_key: r.model_dump() for r in parsed.output.rows}
    after = {r.row_key: r.model_dump() for r in reparsed.output.rows}
    assert after == before


def test_gap_and_duplicate_are_reported(raw_pages):
    pages = copy.deepcopy(raw_pages)
    page = next(p for p in pages if p["number"] == 52)
    for word in page["words"]:
        if word["text"] == "11" and word["x0"] < 90:
            word["text"] = "12"  # GVFG A: 11 missing, 12 twice
            break
    result = parse_pages([PageData.from_dict(p) for p in pages])
    kinds = {(w.kind, w.section, w.lfd_nr) for w in result.warnings}
    assert ("GAP", "GVFG_A", 11) in kinds
    assert ("DUPLICATE", "GVFG_A", 12) in kinds


def test_unresolved_reference_is_reported(raw_pages):
    pages = copy.deepcopy(raw_pages)
    page = next(p for p in pages if p["number"] == 34)
    for word in page["words"]:
        if word["text"] == "20" and 455 < word["x0"] < 470:
            word["text"] = "99"  # "Ref. Teil B 99" points nowhere
            break
    result = parse_pages([PageData.from_dict(p) for p in pages])
    assert [(w.kind, w.section, w.lfd_nr) for w in result.warnings] == [("UNRESOLVED_REF", "BP_A", 10)]


KPI_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "infraplan_2026_kpi_pages.json"


def test_kpi_chart_pages_are_detected():
    """Pages 57, 60–62, 66–68 (chapter 3), 85, 93–94 (appendix I) and 102
    (appendix II, a list of measures under a KPI heading, no chart)."""
    pages = [PageData.from_dict(p) for p in json.loads(KPI_FIXTURE.read_text())["pages"]]
    result = parse_pages(pages)
    assert [(p.page, p.kind, p.title) for p in result.kpi_pages] == [
        (60, "STEUERUNG", "Neu gebaute Gleiskilometer"),
        # Heading on page 61, chart on 62; chart text overlays the caption.
        (62, "STEUERUNG", "Umsetzung Kleiner und Mittlerer Maßnahmen (KMM)"),
        # Heading on 66, chart on 67 above the next heading (right column).
        (67, "STEUERUNG", "Lärmsanierte Streckenkilometer"),
        (68, "STEUERUNG", "Bahnhöfe nach abgestimmtem Zielbild (Bau- und Ausstattungsstandards)"),
        # Two headings side by side on 93; only the second has a chart (94).
        (
            94,
            "INFORMATION",
            "Trassenstornierungen außerhalb des Verantwortungsbereichs der "
            "Eisenbahnverkehrsunternehmen",
        ),
    ]
    assert result.output.rows == []


def test_kpi_pages_do_not_disturb_the_tables(raw_pages):
    kpi_pages = json.loads(KPI_FIXTURE.read_text())["pages"]
    result = parse_pages([PageData.from_dict(p) for p in raw_pages + kpi_pages])
    assert {s.key: s.row_count for s in result.output.sections} == EXPECTED_ROWS
    assert len(result.kpi_pages) == 5
