from dashboard_backend.services.sammel_years import (
    format_years,
    listing_label,
    sammel_year_diffs,
)


def test_diffs_mark_added_kept_removed_against_previous_edition():
    diffs = sammel_year_diffs({2025, 2026, 2027}, {2025: {1, 2}, 2026: {2, 3}, 2027: {3}})
    assert [d.year for d in diffs] == [2025, 2026, 2027]
    first, second, third = diffs
    # Earliest edition: unknown whether new → everything kept.
    assert first.previous_year is None
    assert first.kept == [1, 2] and first.added == [] and first.removed == []
    assert second.previous_year == 2025
    assert second.added == [3] and second.kept == [2] and second.removed == [1]
    assert third.added == [] and third.kept == [3] and third.removed == [2]


def test_edition_without_links_drops_everything():
    diffs = sammel_year_diffs([2025, 2026], {2025: {1}})
    assert diffs[1].removed == [1]
    assert diffs[1].kept == []


def test_format_years_collapses_runs():
    assert format_years([2027, 2025, 2026, 2029]) == "2025–2027, 2029"
    assert format_years([2026]) == "2026"


def test_listing_label():
    assert listing_label([], 2025) is None
    assert listing_label([2026, 2027], 2025) == "Haushalt 2026–2027"
    assert listing_label([2025], 2025).startswith("Haushalt 2025 (erster eingelesener Jahrgang")
