"""Column mapping and table segmentation of the Haushalt importer.

The layout of Anlage VWIB, Teil B shifts from report year to report year — the
parser must read the table's own header instead of assuming 2026's indices, and
must tell the Bedarfsplan table apart from the other tables of Teil B.
"""

from __future__ import annotations

from dashboard_backend.tasks.haushalt import (
    _detect_table_sections,
    _is_bedarfsplan_section,
    _is_table_totals_row,
    _regroup_text_rows,
)
from dashboard_backend.tasks.haushalt_columns import (
    CANONICAL_COLUMNS,
    LEGACY_COLUMN_MAP,
    detect_column_map,
    is_column_number_row,
    is_header_row,
    is_unit_row,
    resolve_column_map,
)

# Header block of the 2027 report (HH-Entwurf 2027, Regierungsentwurf), exactly
# as pdfplumber returns it: three heading rows plus the column-number row.
HEADER_2027: list[list] = [
    [
        "Lfd.\nNr.", "Nr.\nFinVe", "Nr.\nBedarfsplan\nSchiene",
        "Bezeichnung der\nInvestitionsmaßnahme", "voraussichtliche Gesamtausgaben",
        "", "", "", "Gesamtausgabenentwicklung", "", "", "Ausgaben", "", "", "", "",
    ],
    [
        "", "", "", "", "Aufnahme\nin Epl/\nAbschluss\nFinVe", "ursprünglich",
        "Vorjahr", "aktuell", "zum Vorjahr", "", "Gründe\n*", "Verausgabt\nbis 2025",
        "Bewilligt\n2026", "nach 2026\nübertragene\nAusgabereste",
        "Veranschlagt\n2027", "Vorbehalten\nfür 2028 ff.",
    ],
    ["", "", "", "", "Jahr", "€1.000", "", "", "€1.000", "%", "", "€1.000", "", "", "", ""],
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"],
]


# ---------------------------------------------------------------------------
# Header row recognition
# ---------------------------------------------------------------------------

def test_recognises_every_row_of_the_header_block():
    assert [is_header_row(row) for row in HEADER_2027] == [True, True, True, True]


def test_data_row_is_not_a_header_row():
    row = ["B0080 275 N19", None, None, "ABS Angermünde- Grenze D/PL\ndavon:", "2021",
           "379.844", "526.942", "477.871", "- 49.071", "-9%", None,
           "168.091", "83.494", "-", "77.859", "148.427"]
    assert is_header_row(row) is False


def test_column_number_row_detection():
    assert is_column_number_row(HEADER_2027[3]) is True
    assert is_column_number_row(["1", "2", "4"]) is False  # not consecutive
    assert is_column_number_row(["B0080", "275"]) is False


def test_unit_row_detection():
    assert is_unit_row(HEADER_2027[2]) is True
    assert is_unit_row(HEADER_2027[1]) is False


# ---------------------------------------------------------------------------
# Column mapping
# ---------------------------------------------------------------------------

def test_maps_all_sixteen_columns_of_the_2027_header():
    cmap = detect_column_map(HEADER_2027)
    assert cmap.source == "header"
    assert cmap.missing == []
    assert cmap.indices == LEGACY_COLUMN_MAP


def test_previous_year_total_and_delta_do_not_swap():
    """"Vorjahr" is the previous total, "zum Vorjahr" the delta — a swap here
    would move €-values into the delta column unnoticed."""
    cmap = detect_column_map(HEADER_2027)
    assert cmap.index("cost_last_year") == 6
    assert cmap.index("delta_abs") == 8
    assert cmap.index("delta_rel") == 9


def test_maps_a_reordered_layout_by_its_headers():
    """A report year that moves columns around must still map correctly —
    that is the whole point of reading the header instead of fixed indices."""
    reordered = [
        ["Bezeichnung der\nInvestitionsmaßnahme", "Lfd.\nNr.", "Nr.\nFinVe",
         "Nr.\nBedarfsplan\nSchiene", "Aufnahme\nin Epl", "ursprünglich", "Vorjahr",
         "aktuell", "zum Vorjahr", "", "Gründe", "Verausgabt\nbis 2024",
         "Bewilligt\n2025", "übertragene\nAusgabereste", "Veranschlagt\n2026",
         "Vorhalten\nfür 2027 ff."],
        ["", "", "", "", "Jahr", "€1.000", "", "", "€1.000", "%", "", "€1.000", "", "", "", ""],
    ]
    cmap = detect_column_map(reordered)
    assert cmap.index("name") == 0
    assert cmap.index("lfd_nr") == 1
    assert cmap.index("finve_nr") == 2
    assert cmap.index("bedarfsplan") == 3
    # "Vorhalten" (older wording) maps to the same field as "Vorbehalten"
    assert cmap.index("next_years") == 15
    assert cmap.missing == []


def test_each_column_is_claimed_by_at_most_one_field():
    cmap = detect_column_map(HEADER_2027)
    indices = list(cmap.indices.values())
    assert len(indices) == len(set(indices))


def test_falls_back_to_the_fixed_layout_without_a_header(monkeypatch):
    """No recoverable header and no LLM configured — the 2026 layout keeps the
    importer working instead of failing the run."""
    monkeypatch.setattr("dashboard_backend.core.config.settings.llm_base_url", "")
    cmap = resolve_column_map([])
    assert cmap.source == "fallback"
    assert cmap.indices == LEGACY_COLUMN_MAP


def test_llm_mapping_is_used_when_the_header_is_unreadable(monkeypatch):
    monkeypatch.setattr("dashboard_backend.core.config.settings.llm_base_url", "http://llm.test")
    monkeypatch.setattr(
        "dashboard_backend.services.llm.call_llm_json",
        lambda system, prompt: {"columns": {name: i for i, name in enumerate(CANONICAL_COLUMNS)}},
    )
    # Headings the deterministic patterns do not know
    unknown = [["Sp. %d" % i for i in range(16)]]
    cmap = resolve_column_map(unknown)
    assert cmap.source == "llm"
    assert cmap.indices == LEGACY_COLUMN_MAP


def test_llm_mapping_ignores_duplicate_and_out_of_range_columns(monkeypatch):
    monkeypatch.setattr("dashboard_backend.core.config.settings.llm_base_url", "http://llm.test")
    monkeypatch.setattr(
        "dashboard_backend.services.llm.call_llm_json",
        lambda system, prompt: {
            "columns": {"lfd_nr": 0, "name": 0, "cost_actual": 99, "year_planned": 1}
        },
    )
    cmap = resolve_column_map([["a", "b"]])
    # name reuses column 0 and cost_actual is out of range → both dropped, so
    # the mapping is incomplete and the fallback takes over
    assert cmap.source == "fallback"


def test_llm_failure_falls_back_instead_of_raising(monkeypatch):
    monkeypatch.setattr("dashboard_backend.core.config.settings.llm_base_url", "http://llm.test")

    def _boom(system, prompt):
        raise RuntimeError("429 rate limit")

    monkeypatch.setattr("dashboard_backend.services.llm.call_llm_json", _boom)
    cmap = resolve_column_map([["Sp. 1", "Sp. 2"]])
    assert cmap.source == "fallback"


def test_column_map_json_lists_every_canonical_field():
    payload = detect_column_map(HEADER_2027).to_json()
    assert [entry["field"] for entry in payload["columns"]] == list(CANONICAL_COLUMNS)
    assert payload["source"] == "header"
    assert all(entry["label"] for entry in payload["columns"])


# ---------------------------------------------------------------------------
# Table segmentation — Teil B is five tables in one PDF
# ---------------------------------------------------------------------------

def _page(table_no: int | None, title: str = "") -> str:
    caption = f"Tabelle {table_no} - {title}" if table_no else ""
    return f"Verkehrswegeinvestitionen des Bundes\nTeil B-\n{caption}\n - 231 -"


def test_groups_pages_by_their_table_caption():
    sections = _detect_table_sections(
        [_page(1, "Bedarfsplanmaßnahmen")] * 3
        + [_page(2, "Lärmsanierung")] * 2
        + [_page(3, "ERTMS")]
    )
    assert [(s.number, s.title, s.pages) for s in sections] == [
        (1, "Bedarfsplanmaßnahmen", [1, 2, 3]),
        (2, "Lärmsanierung", [4, 5]),
        (3, "ERTMS", [6]),
    ]


def test_page_without_caption_stays_with_the_previous_table():
    sections = _detect_table_sections([_page(1, "Bedarfsplanmaßnahmen"), _page(None), _page(2, "Lärmsanierung")])
    assert [(s.number, s.pages) for s in sections] == [(1, [1, 2]), (2, [3])]


def test_only_the_bedarfsplan_table_expects_a_printed_finve_number():
    """Every table is imported, but only Tabelle 1 prints FinVe numbers — the
    others identify their measures by a string key instead."""
    sections = _detect_table_sections(
        [_page(1, "Bedarfsplanmaßnahmen"), _page(2, "Lärmsanierung"), _page(5, "Maßnahmen nach InvKG")]
    )
    assert [_is_bedarfsplan_section(s, sections) for s in sections] == [True, False, False]


def test_document_without_captions_is_one_section_over_all_pages():
    """Pre-2027 reports without "Tabelle N" captions keep the old behaviour of
    treating the whole document as a single table that prints FinVe numbers."""
    sections = _detect_table_sections(["irgendein Text", "noch eine Seite"])
    assert len(sections) == 1
    assert sections[0].number is None
    assert sections[0].pages == [1, 2]
    assert _is_bedarfsplan_section(sections[0], sections) is True


def test_totals_row_is_recognised():
    assert _is_table_totals_row("TABELLENSUMMEN\ndavon:\nKap. 1202, Titel 891 01") is True
    assert _is_table_totals_row("ABS Angermünde- Grenze D/PL") is False
    assert _is_table_totals_row(None) is False


def test_totals_row_is_recognised_by_its_dotted_running_number():
    """On a rebuilt page the "TABELLENSUMMEN" label ends up in another cell; the
    dotted placeholder in the running-number column is what is left of it."""
    assert _is_table_totals_row("Erläuterung: …", ". \n. \n. \n.") is True
    assert _is_table_totals_row("Erläuterung: …", "YYY") is False


# ---------------------------------------------------------------------------
# Rebuilding rows on pages without horizontal rules
# ---------------------------------------------------------------------------

def test_regroup_joins_text_lines_back_into_one_row_per_measure():
    """The ERTMS pages have no rules between measures, so the rows are taken
    from the text lines and regrouped — one row per measure, sub-entries stacked
    inside the cells exactly as the ruling-line extraction produces them."""
    text_rows = [
        ["YYY", "F08Q0770", None, "Baustufen I + II", "2020", "216.050"] + [None] * 10,
        [None, None, None, "davon:", None, None] + [None] * 10,
        [None, None, None, "Kap. 1202, Titel 891 06", None, "222.377"] + [None] * 10,
        [None, None, None, "nachrichtlich: Eigenmittel der EIU", None, "16.000"] + [None] * 10,
        ["YYY", "F21Q0774", None, "Baustufe III", "2022", "1.064.666"] + [None] * 10,
    ]
    rows, row_lines = _regroup_text_rows(text_rows, 16)
    assert len(rows) == 3
    assert rows[0][0] == "YYY"
    assert rows[0][3] == "Baustufen I + II\ndavon:\nKap. 1202, Titel 891 06"
    assert rows[0][5] == "216.050\n222.377"
    # the nachrichtlich block opens a row of its own, as it does on a ruled page
    assert rows[1][3] == "nachrichtlich: Eigenmittel der EIU"
    assert rows[2][3] == "Baustufe III"


def test_regroup_keeps_the_printed_lines_of_every_row():
    """Joining the lines into a cell drops the empty ones — which line a value
    was printed on is what decides which Titel it funds, so the lines come back
    beside the row (`ExtractedPage.row_lines`)."""
    text_rows = [
        ["YYY", "F08Q0770", None, "Baustufen I + II", "2020", "216.050"] + [None] * 10,
        [None, None, None, "davon:", None, None] + [None] * 10,
        [None, None, None, "Kap. 1202, Titel 891 06", None, "222.377"] + [None] * 10,
        ["YYY", "F21Q0774", None, "Baustufe III", "2022", "1.064.666"] + [None] * 10,
    ]
    rows, row_lines = _regroup_text_rows(text_rows, 16)

    assert len(row_lines) == len(rows)
    assert [len(lines) for lines in row_lines] == [3, 1]
    # the third printed line of the first row has no value in column 5's
    # predecessor — the cell lost that, the line keeps it
    assert [line[3] for line in row_lines[0]] == [
        "Baustufen I + II", "davon:", "Kap. 1202, Titel 891 06",
    ]
    assert [line[5] for line in row_lines[0]] == ["216.050", None, "222.377"]
