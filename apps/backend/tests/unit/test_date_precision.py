"""Date qualification (docs/features/feature-project-progress.md → „Datumsqualifikation“)."""

from __future__ import annotations

from datetime import date

import pytest

from dashboard_backend.models.projects.progress_enums import DatePrecision as P
from dashboard_backend.services.date_precision import (
    add_months,
    date_text,
    derived_precision,
    format_date,
    in_period,
    normalize_sort_date,
)
from dashboard_backend.services.progress_dates import (
    parse_flexible_date,
    parse_flexible_date_with_precision,
)


@pytest.mark.parametrize(
    ("value", "precision", "expected"),
    [
        (date(2026, 2, 6), P.EXACT, "06.02.2026"),
        (date(2027, 2, 1), P.MONTH, "02/2027"),
        (date(2028, 1, 1), P.YEAR, "2028"),
        (date(2032, 1, 1), P.NOT_BEFORE, "nach 2031"),
        (date(2032, 7, 1), P.NOT_BEFORE, "frühestens 07/2032"),
        (date(2028, 7, 1), P.ASSUMED, "ca. 07/2028 (Annahme)"),
        (date(2026, 2, 6), None, "06.02.2026"),
        (date(2026, 2, 6), "UNBEKANNT", "06.02.2026"),
    ],
)
def test_format_date(value, precision, expected):
    assert format_date(value, precision) == expected


def test_date_text_appends_label():
    assert date_text(date(2032, 1, 1), "NOT_BEFORE", "Priorisierung 2027 offen") == (
        "nach 2031 – Priorisierung 2027 offen"
    )
    assert date_text(None, "EXACT", "offen") == "offen"
    assert date_text(None, "EXACT") is None
    assert date_text(date(2028, 1, 1), "YEAR", "  ") == "2028"


def test_normalize_sort_date():
    assert normalize_sort_date(date(2027, 2, 17), P.MONTH) == date(2027, 2, 1)
    assert normalize_sort_date(date(2028, 9, 17), P.YEAR) == date(2028, 1, 1)
    for precision in (P.EXACT, P.NOT_BEFORE, P.ASSUMED):
        assert normalize_sort_date(date(2032, 7, 3), precision) == date(2032, 7, 3)
    assert normalize_sort_date(None, P.YEAR) is None


def test_derived_precision_keeps_lower_bound():
    assert derived_precision(P.NOT_BEFORE) is P.NOT_BEFORE
    for base in (P.EXACT, P.MONTH, P.YEAR, P.ASSUMED):
        assert derived_precision(base) is P.ASSUMED


def test_add_months_clamps_the_day():
    assert add_months(date(2028, 1, 1), 6) == date(2028, 7, 1)
    assert add_months(date(2028, 8, 31), 6) == date(2029, 2, 28)
    assert add_months(date(2031, 12, 15), 1) == date(2032, 1, 15)


@pytest.mark.parametrize(
    ("value", "precision", "expected"),
    [
        (date(2029, 5, 1), P.EXACT, True),
        (date(2031, 1, 2), P.EXACT, False),
        (date(2027, 12, 31), P.ASSUMED, False),
        # A year-only date overlaps the period with its whole year.
        (date(2028, 1, 1), P.YEAR, True),
        (date(2027, 12, 31), P.YEAR, False),
        (date(2030, 12, 31), P.YEAR, True),
        (date(2027, 12, 1), P.MONTH, False),
        # A lower bound is no date: never a hit, even inside the period.
        (date(2029, 1, 1), P.NOT_BEFORE, False),
    ],
)
def test_in_period_2028_to_2030(value, precision, expected):
    assert in_period(value, precision, date(2028, 3, 1), date(2030, 12, 31)) is expected


def test_in_period_open_ends():
    assert in_period(date(2040, 1, 1), P.EXACT, date(2028, 1, 1), None)
    assert in_period(date(2020, 1, 1), P.YEAR, None, date(2020, 6, 30))
    assert not in_period(None, P.EXACT, None, None)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("01.03.2024", (date(2024, 3, 1), P.EXACT)),
        ("2024-03-15", (date(2024, 3, 15), P.EXACT)),
        ("12/2024", (date(2024, 12, 15), P.MONTH)),
        ("März 2024", (date(2024, 3, 15), P.MONTH)),
        ("2. Quartal 2025", (date(2025, 5, 15), P.YEAR)),
        ("Ende 2027", (date(2027, 12, 15), P.YEAR)),
        ("voraussichtlich 2025", (date(2025, 7, 1), P.YEAR)),
        ("nach 2031", (date(2032, 1, 1), P.NOT_BEFORE)),
        (">2031", (date(2032, 1, 1), P.NOT_BEFORE)),
        ("frühestens 2032", (date(2032, 1, 1), P.NOT_BEFORE)),
        ("ab 2032", (date(2032, 1, 1), P.NOT_BEFORE)),
        ("2024-2026", (date(2024, 7, 1), P.YEAR)),
        ("-", (None, P.EXACT)),
        (None, (None, P.EXACT)),
    ],
)
def test_parse_with_precision(text, expected):
    assert parse_flexible_date_with_precision(text) == expected


def test_plain_parse_is_unchanged():
    # parse_flexible_date keeps its reading of lower bounds (the year itself).
    assert parse_flexible_date(">2024") == date(2024, 7, 1)
    assert parse_flexible_date("12/2024") == date(2024, 12, 15)
