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
    entries = _extract_inline_titel_entries(cells)
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
    assert _extract_inline_titel_entries(_row("ABS Hanau–Würzburg")) == []


def test_nachrichtlich_entries_snapshot():
    # nachrichtlich rows map line i of each numeric column to label i (no offset)
    cells = [None, None, None,
             "nachrichtlich: Beteiligung Dritter\nnachrichtlich: Eigenmittel EIU",
             None, None,
             "100\n200", "110\n210", None, None, None,
             "10\n20", "1\n2", "3\n4", "5\n6", "7\n8"]
    entries = _extract_nachrichtlich_entries(cells)
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
    entry = _build_titel_entry(cells)
    # titel_nr "891 01 600": the joined-cells regex greedily includes the first
    # numeric cell — long-standing behavior, pinned as-is (not worth changing).
    assert entry.model_dump() == {
        "titel_key": "891_01", "kapitel": "1202", "titel_nr": "891 01 600",
        "label": "Kap. 1202 Titel 891 01", "is_nachrichtlich": False,
        "cost_estimate_last_year": 600, "cost_estimate_aktuell": 650,
        "verausgabt_bis": 200, "bewilligt": 80,
        "ausgabereste_transferred": 6, "veranschlagt": 50, "vorhalten_future": 500,
    }
