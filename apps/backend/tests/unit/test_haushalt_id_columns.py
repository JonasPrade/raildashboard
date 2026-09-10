"""The identity of a row must not depend on how the PDF merges its first columns.

pdfplumber returns the Lfd. Nr., the FinVe number and the Bedarfsplan number of
the 2026+ layout merged into one cell ("B0080 275 N19"); the OCR stage returns
them as the three separate columns the table header actually declares.  Both are
the same record, so the parser reads all three through the column map and finds
the same FinVe either way.  That also makes the row detection independent of one
PDF generation's cell merging — the condition for reading the older reports.
"""

from __future__ import annotations

from dashboard_backend.tasks.haushalt import ExtractedPage, _parse_extracted_pages

_HEADER = [
    ["Lfd.\nNr.", "Nr.\nFinVe", "Nr.\nBedarfsplan\nSchiene", "Bezeichnung der\nInvestitionsmaßnahme",
     "voraussichtliche Gesamtausgaben", None, None, None, "Gesamtausgabenentwicklung", None, None,
     "Ausgaben", None, None, None, None],
    [None, None, None, None, "Aufnahme\nin Epl/\nAbschluss\nFinVe", "ursprünglich", "Vorjahr",
     "aktuell", "zum Vorjahr", None, "Gründe\n*", "Verausgabt\nbis 2025", "Bewilligt\n2026",
     "nach 2026\nübertragene\nAusgabereste", "Veranschlagt\n2027", "Vorbehalten\nfür 2028 ff."],
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"],
]

_VALUES = ["2021", "379.844", "526.942", "477.871", "- 49.071", "-9%", "",
           "168.091", "83.494", "-", "77.859", "148.427"]

_PAGE_TEXT = "Teil B-\nTabelle 1 - Bedarfsplanmaßnahmen\n"


def _parse(id_cells: list) -> object:
    row = id_cells + ["ABS Angermünde- Grenze D/PL"] + _VALUES
    page = ExtractedPage(number=1, text=_PAGE_TEXT, rows=_HEADER + [row])
    return _parse_extracted_pages([page], 2027, known_finve_ids=set())


def test_merged_and_separate_id_columns_produce_the_same_row():
    merged = _parse(["B0080 275 N19", None, None])
    separate = _parse(["B0080", "275", "N19"])

    assert [r.row_key for r in separate.rows] == [r.row_key for r in merged.rows] == ["275"]
    assert separate.rows[0].proposed_budget.model_dump() == merged.rows[0].proposed_budget.model_dump()
    assert separate.rows[0].proposed_budget.fin_ve == 275
    assert separate.rows[0].proposed_budget.bedarfsplan_number == "N19"
    assert separate.rows[0].proposed_budget.year_planned == 77859


def test_a_dash_in_the_bedarfsplan_column_means_no_bedarfsplan():
    """The report prints a bare dash where a measure has no Bedarfsplan number."""
    result = _parse(["B0080", "275", "-"])
    assert result.rows[0].proposed_budget.bedarfsplan_number is None


def test_a_row_without_a_finve_number_anywhere_stays_unmatched():
    """Reading column 1 must not invent a FinVe for a row that prints none."""
    result = _parse(["B0134", None, "L 06"])
    assert result.rows == []
    assert [u["raw_lfd_nr"] for u in result.unmatched_rows] == ["B0134"]
