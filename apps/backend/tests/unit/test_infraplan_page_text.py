"""Page text with layout and KPI value suggestions (services/infraplan_page_text.py)
against the KPI pages of the Infraplan 2026."""

from __future__ import annotations

import json
from pathlib import Path

from dashboard_backend.services.infraplan_page_text import layout_text, parse_number, suggest_chart_values

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "infraplan_2026_kpi_pages.json"


def _page(number: int) -> list[dict]:
    pages = json.loads(FIXTURE.read_text())["pages"]
    return next(p for p in pages if p["number"] == number)["words"]


def test_layout_lines_carry_positions():
    lines = layout_text(_page(60))

    assert "500: 2020@100 2021@142 2022@184 2023@225 2024@267 2025@309 2026@351 2027@392 2028@434 2029@476 2030@517" in lines
    assert not any("(cid:" in line for line in lines)


def test_new_track_km_values_by_year():
    (chart,) = suggest_chart_values(_page(60), plan_year=2026)

    values = {v["year"]: (v["value"], v["kind_guess"]) for v in chart["values"]}
    assert values == {
        2021: (1.0, "IST"),
        2022: (127.0, "IST"),
        2023: (6.0, "IST"),
        2024: (65.0, "IST"),
        2025: (67.0, "IST"),
        2026: (64.0, "ZIEL"),
        2027: (57.0, "ZIEL"),
        2028: (16.0, "ZIEL"),
        2030: (18.0, "ZIEL"),
    }
    # Zeros carry no label: 2020 and 2029 are left to the reader.
    assert chart["missing"] == [2020, 2029]
    assert chart["stacked"] == []
    # In sum 266 Gleis-km 2020–2025, as the text says.
    assert sum(v for year, (v, _) in values.items() if year <= 2025) == 266


def test_a_footnote_with_years_is_no_axis():
    assert suggest_chart_values(_page(66), plan_year=2026) == []


def test_parse_number():
    assert parse_number("1.234") == 1234
    assert parse_number("12,5") == 12.5
    assert parse_number("84%") == 84
    assert parse_number("2020a") is None
