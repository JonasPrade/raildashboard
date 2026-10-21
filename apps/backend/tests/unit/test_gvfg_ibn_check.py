"""Unit tests for questioning the commissioning year with the GVFG-Finanzreihe."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from dashboard_backend.services.gvfg_ibn_check import check_ibn_against_gvfg, known_ibn

PERIODS = [
    {"label": "1967–2023", "year_from": 1967, "year_to": 2023, "kind": "ausgezahlt"},
    {"label": "2026", "year_from": 2026, "year_to": 2026, "kind": "geplant"},
    {"label": "2027", "year_from": 2027, "year_to": 2027, "kind": "geplant"},
    {"label": "2028", "year_from": 2028, "year_to": 2028, "kind": "geplant"},
    {"label": "2029", "year_from": 2029, "year_to": 2029, "kind": "geplant"},
    {"label": "ab 2030", "year_from": 2030, "year_to": None, "kind": "rest"},
]
# Siemensbahn, GVFG 2025–2029 (Mio. €)
SIEMENSBAHN = {
    "1967–2023": Decimal("0"),
    "2026": Decimal("49.50"),
    "2027": Decimal("59.67"),
    "2028": Decimal("94.76"),
    "2029": Decimal("75.00"),
    "ab 2030": Decimal("342.76"),
}


def _check(ibn_year, amounts=SIEMENSBAHN):
    return check_ibn_against_gvfg(ibn_year, "Infraplan", "2025–2029", PERIODS, amounts)


def test_relevant_aid_after_commissioning_questions_it():
    doubt = _check(2028)
    assert doubt is not None
    assert (doubt.ibn_year, doubt.ibn_source, doubt.edition) == (2028, "Infraplan", "2025–2029")
    assert doubt.aid_after == Decimal("417.76")
    assert doubt.aid_total == Decimal("621.69")
    assert [label for label, _ in doubt.periods] == ["2029", "ab 2030"]


def test_rest_column_starting_in_the_commissioning_year_is_not_after():
    assert _check(2030) is None


def test_small_final_payment_is_no_doubt():
    amounts = {"2026": Decimal("40"), "2027": Decimal("50"), "2028": Decimal("5")}
    assert _check(2027, amounts) is None  # 5 of 95 Mio. € < 15 %


def test_tiny_amounts_are_no_doubt_even_as_a_large_share():
    amounts = {"2026": Decimal("0.5"), "2028": Decimal("0.5")}
    assert _check(2027, amounts) is None  # < 1 Mio. €


def test_no_amounts_no_doubt():
    assert _check(2026, {}) is None


GVFG_2025 = (date(2025, 7, 18), 2029, "2025–2029")


def test_known_ibn_more_recent_source_wins():
    assert known_ibn(GVFG_2025, (date(2026, 3, 1), 2031)) == (2031, "Infraplan")
    assert known_ibn(GVFG_2025, (date(2024, 3, 1), 2027)) == (2029, "GVFG 2025–2029")


def test_known_ibn_same_date_prefers_infraplan():
    assert known_ibn(GVFG_2025, (date(2025, 7, 18), 2030)) == (2030, "Infraplan")


def test_known_ibn_single_source_or_none():
    assert known_ibn(GVFG_2025, None) == (2029, "GVFG 2025–2029")
    assert known_ibn(None, (date(2026, 3, 1), 2031)) == (2031, "Infraplan")
    assert known_ibn(None, None) is None
