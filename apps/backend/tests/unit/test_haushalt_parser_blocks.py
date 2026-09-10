"""Pin the outputs of the repeated haushalt.py parser blocks (#90).

Synthetic pdfplumber-style rows exercise the three blocks the refactor
extracts (inline Titel mapping, nachrichtlich mapping, old-format Titel
sub-row) — outputs must be identical before and after. The full-PDF golden
run (`scripts/dump_parse_result.py` on a reference PDF) is a deferred manual
test; see docs/manual-tests-backlog.md.
"""

from __future__ import annotations

from dashboard_backend.tasks.haushalt import (
    _build_titel_entry,
    _extract_inline_titel_entries,
    _extract_nachrichtlich_entries,
)
from dashboard_backend.tasks.haushalt_columns import LEGACY_COLUMN_MAP, ColumnMap

# The blocks now read their columns through a ColumnMap; the legacy map is the
# fixed 2026 layout these synthetic rows are written in.
CMAP = ColumnMap(indices=dict(LEGACY_COLUMN_MAP), source="fallback")

# Columns: 0 lfd, 1 finve, 2 bedarfsplan, 3 name, 4 start year, 5 cost orig,
# 6 cost last year, 7 cost actual, 8 delta abs, 9 delta rel, 10 reasons,
# 11 spent-2y, 12 allowed prev, 13 ausgabereste, 14 planned, 15 next years


def _row(name_cell: str, **numeric) -> list:
    cells = ["B0080 275 N19", None, None, name_cell, "2019", "1.500"] + [None] * 10
    for col, val in numeric.items():
        cells[int(col.split("_")[1])] = val
    return cells


def test_inline_titel_entries_snapshot():
    # 2026+ format: project total on line 0, per-Kap values on lines 1..n
    cells = _row(
        "ABS Hanau–Würzburg\ndavon:\nKap. 1202, Titel 891 01\nKap. 1202, Titel 891 02",
        c_6="1.000\n600\n400",
        c_7="1.100\n650\n450",
        c_11="300\n200\n100",
        c_12="120\n80\n40",
        c_13="10\n6\n4",
        c_14="90\n50\n40",
        c_15="980\n500\n480",
    )
    entries = _extract_inline_titel_entries(cells, CMAP)
    assert [e.model_dump() for e in entries] == [
        {
            "titel_key": "891_01", "kapitel": "1202", "titel_nr": "891 01",
            "label": "Kap. 1202, Titel 891 01", "is_nachrichtlich": False,
            "cost_estimate_last_year": 600, "cost_estimate_aktuell": 650,
            "verausgabt_bis": 200, "bewilligt": 80,
            "ausgabereste_transferred": 6, "veranschlagt": 50, "vorhalten_future": 500,
        },
        {
            "titel_key": "891_02", "kapitel": "1202", "titel_nr": "891 02",
            "label": "Kap. 1202, Titel 891 02", "is_nachrichtlich": False,
            "cost_estimate_last_year": 400, "cost_estimate_aktuell": 450,
            "verausgabt_bis": 100, "bewilligt": 40,
            "ausgabereste_transferred": 4, "veranschlagt": 40, "vorhalten_future": 480,
        },
    ]


def test_inline_titel_entries_without_davon_is_empty():
    assert _extract_inline_titel_entries(_row("ABS Hanau–Würzburg"), CMAP) == []


def test_nachrichtlich_entries_snapshot():
    # nachrichtlich rows map line i of each numeric column to label i (no offset)
    cells = [None, None, None,
             "nachrichtlich: Beteiligung Dritter\nnachrichtlich: Eigenmittel EIU",
             None, None,
             "100\n200", "110\n210", None, None, None,
             "10\n20", "1\n2", "3\n4", "5\n6", "7\n8"]
    entries = _extract_nachrichtlich_entries(cells, CMAP)
    assert [e.model_dump() for e in entries] == [
        {
            "titel_key": "nachrichtlich: Beteiligung Dritter", "kapitel": "", "titel_nr": "",
            "label": "nachrichtlich: Beteiligung Dritter", "is_nachrichtlich": True,
            "cost_estimate_last_year": 100, "cost_estimate_aktuell": 110,
            "verausgabt_bis": 10, "bewilligt": 1,
            "ausgabereste_transferred": 3, "veranschlagt": 5, "vorhalten_future": 7,
        },
        {
            "titel_key": "nachrichtlich: Eigenmittel EIU", "kapitel": "", "titel_nr": "",
            "label": "nachrichtlich: Eigenmittel EIU", "is_nachrichtlich": True,
            "cost_estimate_last_year": 200, "cost_estimate_aktuell": 210,
            "verausgabt_bis": 20, "bewilligt": 2,
            "ausgabereste_transferred": 4, "veranschlagt": 6, "vorhalten_future": 8,
        },
    ]


def test_build_titel_entry_old_format_snapshot():
    # Old format: separate sub-row, first line of each numeric column
    cells = [None, None, None, "Kap. 1202 Titel 891 01", None, None,
             "600\nrest", "650", None, None, None,
             "200", "80", "6", "50", "500"]
    entry = _build_titel_entry(cells, CMAP)
    # titel_nr "891 01 600": the joined-cells regex greedily includes the first
    # numeric cell — long-standing behavior, pinned as-is (not worth changing).
    assert entry.model_dump() == {
        "titel_key": "891_01", "kapitel": "1202", "titel_nr": "891 01 600",
        "label": "Kap. 1202 Titel 891 01", "is_nachrichtlich": False,
        "cost_estimate_last_year": 600, "cost_estimate_aktuell": 650,
        "verausgabt_bis": 200, "bewilligt": 80,
        "ausgabereste_transferred": 6, "veranschlagt": 50, "vorhalten_future": 500,
    }


# ---------------------------------------------------------------------------
# Mittelherkunft: the value belongs to the Titel it is printed beside
# ---------------------------------------------------------------------------
#
# Taken from B0092 of the 2027 report, where the pairing by line index goes
# wrong: "Bewilligt 2026" is printed on the measure's own line and again on the
# Kap.-6002 line, and nowhere else. The cell keeps the non-empty lines only, so
# it arrives as a single "7.077" — indistinguishable from a measure whose two
# Titel simply have no value.

_B0092_NAME = (
    "Mitteldeutsches Revier:\ndavon:\n"
    "Kap. 1210, Titel 891 14\nKap. 6002, Titel 893 45"
)


def _b0092_cells() -> list:
    cells = [None] * 16
    cells[0] = "B0092"
    cells[3] = _B0092_NAME
    cells[7] = "253.333\n9.203\n244.130"   # cost actual: on all three lines
    cells[11] = "9.203\n9.203"             # verausgabt: measure + Kap. 1210
    cells[12] = "7.077"                    # bewilligt: measure + Kap. 6002 only
    return cells


def _b0092_printed_lines() -> list[list]:
    def line(name, cost_actual=None, verausgabt=None, bewilligt=None):
        cells = [None] * 16
        cells[3] = name
        cells[7], cells[11], cells[12] = cost_actual, verausgabt, bewilligt
        return cells

    return [
        line("Mitteldeutsches Revier:", "253.333", "9.203", "7.077"),
        line("davon:"),
        line("Kap. 1210, Titel 891 14", "9.203", "9.203"),
        line("Kap. 6002, Titel 893 45", "244.130", None, "7.077"),
    ]


def test_inline_titel_entries_take_the_values_printed_beside_them():
    entries = _extract_inline_titel_entries(_b0092_cells(), CMAP, _b0092_printed_lines())
    assert [(e.label, e.cost_estimate_aktuell, e.verausgabt_bis, e.bewilligt) for e in entries] == [
        ("Kap. 1210, Titel 891 14", 9203, 9203, None),
        ("Kap. 6002, Titel 893 45", 244130, None, 7077),
    ]


def test_inline_titel_entries_without_printed_lines_pair_by_line_index():
    """The fallback for a source that carries no coordinates (the OCR path).

    It is wrong here, and that is the point: 7.077 funds Kap. 6002, but as the
    only line of its cell it counts as the measure's own line and reaches no
    Titel at all. Only the printed lines can tell the two apart.
    """
    entries = _extract_inline_titel_entries(_b0092_cells(), CMAP)
    assert [(e.label, e.cost_estimate_aktuell, e.verausgabt_bis, e.bewilligt) for e in entries] == [
        ("Kap. 1210, Titel 891 14", 9203, 9203, None),
        ("Kap. 6002, Titel 893 45", 244130, None, None),
    ]


def test_nachrichtlich_entries_take_the_values_printed_beside_them():
    cells = [None] * 16
    cells[3] = "nachrichtlich: Beteiligung Dritter\nnachrichtlich: Eigenmittel EIU"
    cells[12] = "3.479"          # printed only on the second of the two lines

    def line(name, bewilligt=None):
        row = [None] * 16
        row[3], row[12] = name, bewilligt
        return row

    lines = [
        line("nachrichtlich: Beteiligung Dritter"),
        line("nachrichtlich: Eigenmittel EIU", "3.479"),
    ]
    entries = _extract_nachrichtlich_entries(cells, CMAP, lines)
    assert [(e.label, e.bewilligt) for e in entries] == [
        ("nachrichtlich: Beteiligung Dritter", None),
        ("nachrichtlich: Eigenmittel EIU", 3479),
    ]
