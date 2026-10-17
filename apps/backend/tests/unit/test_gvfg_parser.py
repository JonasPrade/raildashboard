"""GVFG programme parser (services/gvfg_parser.py) on synthetic PDFs."""

from __future__ import annotations

import io
from decimal import Decimal

import pytest

from dashboard_backend.services.gvfg_parser import (
    CATEGORY_SUM,
    GvfgParseError,
    normalize_key,
    parse_decimal,
    parse_gvfg_pdf,
)
from tests.gvfg_pdf_factory import Row, build_pdf


def _meta(nr, key, name, **extra):
    meta = {
        "Nr.": nr,
        "Schlüssel": key,
        "Stadt/Region": "Hamburg",
        "Bezeichnung/ Beschreibung": name,
        "Lph": "5 - 9",
        "Fördertatbestand": "Bau und Ausbau",
        "Fördersatz": "75%",
        "Beginn- jahr Mittel- abfluss": "2021",
        "Bau- beginn": "2020",
        "Inbetrieb- nahme gepl.": "2027",
    }
    meta.update(extra)
    return meta


def _financial_page(**overrides):
    page = {
        "land": "Hamburg",
        "kind": "kommunale Vorhaben",
        "rows": [
            Row(
                _meta("1", "02 G 509_A", "Hochbahn, Verlängerung der U4"),
                [
                    ("∑", ["546,00", "371,56", "278,67", "110,75", "62,40", "39,20", "66,32"]),
                    ("A", ["450,00", "283,14", "212,36", "110,75", "62,40", "39,20", "0,00"]),
                    ("C", ["96,00", "88,42", "66,32", "", "", "", "66,32"]),
                ],
            ),
            Row(
                # Two C lines (announced extra costs) and a key with spaces.
                _meta("2", "02 G 4518 _ A", "Teilautomatisierung U2/U4", **{"Lph": "3 - 4"}),
                [
                    ("∑", ["95,00", "74,00", "44,40", "0,00", "0,00", "1,50", "13,50"]),
                    ("A", ["", "", "0,00", "", "", "", ""]),
                    ("C", ["90,00", "70,00", "42,00", "", "", "1,00", "13,00"]),
                    ("C", ["5,00", "4,00", "2,40", "", "", "0,50", "0,50"]),
                ],
            ),
        ],
        "total": [
            ("∑", ["641,00", "445,56", "323,07"]),
            ("A", ["450,00", "283,14", "212,36"]),
            ("C", ["191,00", "162,42", "110,72"]),
        ],
    }
    page.update(overrides)
    return page


def test_helpers():
    assert normalize_key("Projektschlüssel 5 G 7007_A") == "05 G 7007_A"
    assert normalize_key("01 G 540 _ A") == "01 G 540_A"
    assert normalize_key("Bau und Ausbau") is None
    assert parse_decimal("1.662,00") == Decimal("1662.00")
    assert parse_decimal("") is None


def test_financial_part():
    result = parse_gvfg_pdf(io.BytesIO(build_pdf([_financial_page()])))
    assert (result.year_from, result.year_to, result.stand) == (2025, 2029, "18.07.2025")
    assert [p.label for p in result.periods] == ["1967–2023", "2024", "2025", "ab 2030"]
    assert [p.kind for p in result.periods] == ["ausgezahlt", "ausgezahlt", "geplant", "rest"]
    assert result.warnings == []

    first, second = result.entries
    assert first.key == "02 G 509_A"
    assert (first.land, first.kind, first.part) == ("Hamburg", "kommunal", "finanzrelevant")
    assert first.name == "Hochbahn, Verlängerung der U4"
    assert (first.lph, first.funding_type, first.funding_rate) == ("5 - 9", "Bau und Ausbau", 75)
    assert (first.start_year, first.construction_start, first.commissioning_planned) == (2021, 2020, 2027)
    assert [a.category for a in first.amounts] == [CATEGORY_SUM, "A", "C"]
    total, part_a, part_c = first.amounts
    assert total.aid_total == Decimal("278.67")
    assert total.periods == {
        "1967–2023": Decimal("110.75"),
        "2024": Decimal("62.40"),
        "2025": Decimal("39.20"),
        "ab 2030": Decimal("66.32"),
    }
    assert part_c.periods == {"ab 2030": Decimal("66.32")}
    assert part_c.cost_total == Decimal("96.00")

    assert second.key == "02 G 4518_A"
    assert second.key_raw == "02 G 4518 _ A"
    assert [a.category for a in second.amounts] == [CATEGORY_SUM, "A", "C", "C"]
    assert second.amounts[3].aid_total == Decimal("2.40")


def test_sum_mismatch_is_reported():
    page = _financial_page(total=[("∑", ["600,00", "445,56", "323,07"])])
    result = parse_gvfg_pdf(io.BytesIO(build_pdf([page])))
    assert len(result.warnings) == 1
    assert "Gesamtkosten laut PDF 600.00" in result.warnings[0]


def test_missing_sum_line_is_computed():
    row = Row(
        _meta("1", "15 G 17_T", "Stadtbahnprojekt Halle"),
        [("A", ["201,78", "150,00", "97,06", "50,13", "", "", ""]), ("B", ["122,12", "90,00", "57,82", "", "", "", ""])],
    )
    page = _financial_page(rows=[row], total=[], land="Sachsen-Anhalt")
    [entry] = parse_gvfg_pdf(io.BytesIO(build_pdf([page]))).entries
    total = entry.amounts[0]
    assert total.category == CATEGORY_SUM and total.computed is True
    assert total.cost_total == Decimal("323.90")
    assert total.periods == {"1967–2023": Decimal("50.13")}


def test_informational_part():
    row = Row(_meta("1", "01 G 528_A", "Ausbau Niebüll - Dagebüll", **{"Lph": "3 - 4"}), [("", ["35,00", "35,00", "26,25"])])
    page = {"land": "Schleswig-Holstein", "kind": "DB-Vorhaben", "informational": True, "rows": [row], "total": []}
    [entry] = parse_gvfg_pdf(io.BytesIO(build_pdf([page]))).entries
    assert (entry.part, entry.kind) == ("nachrichtlich", "db")
    [line] = entry.amounts
    assert (line.category, line.cost_total, line.aid_total) == (CATEGORY_SUM, Decimal("35.00"), Decimal("26.25"))
    assert line.periods == {}


def test_not_a_programme():
    page = _financial_page()
    with pytest.raises(GvfgParseError, match="Bundesprogramm"):
        parse_gvfg_pdf(io.BytesIO(build_pdf([page], title="Irgendein anderes Dokument")))
