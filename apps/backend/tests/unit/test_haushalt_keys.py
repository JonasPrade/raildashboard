"""Identity of measures the budget report lists without a FinVe number."""

from __future__ import annotations

from dashboard_backend.tasks.haushalt_keys import (
    build_finve_key,
    has_measure_marker,
    measure_identifier,
)


# ---------------------------------------------------------------------------
# Marker detection — what opens a measure
# ---------------------------------------------------------------------------

def test_yyy_and_running_number_open_a_measure():
    assert has_measure_marker("YYY SV 52/2017") is True
    assert has_measure_marker("YYY") is True
    assert has_measure_marker("B0094 5/ Nr.1 F 21/S 0555") is True


def test_stray_text_does_not_open_a_measure():
    """Section headings land in the first column on the pages whose rows had to
    be rebuilt — they must not be mistaken for an identifier."""
    assert has_measure_marker("2.2. ERTMS-Ausrüstung Korridor Skandinavien-Mittelmeer") is False
    assert has_measure_marker("") is False
    assert has_measure_marker(None) is False


# ---------------------------------------------------------------------------
# Identifier
# ---------------------------------------------------------------------------

def test_running_number_wins_over_the_rest_of_the_cell():
    assert measure_identifier("B0094 5/ Nr.1 F 21/S 0555") == "B0094"


def test_identifier_follows_the_yyy_marker():
    assert measure_identifier("YYY SV 52/2017") == "SV 52/2017"
    assert measure_identifier("YYY F 03 E 0793") == "F 03 E 0793"


def test_identifier_falls_back_to_the_finve_column():
    """On the rebuilt pages the marker and the designation sit in separate
    columns."""
    assert measure_identifier("YYY", "F08Q0770") == "F08Q0770"
    assert measure_identifier("YYY", "F21Q0774\nF21Q0790") == "F21Q0774 F21Q0790"


def test_no_identifier_without_a_marker_or_a_designation():
    assert measure_identifier("YYY") is None
    assert measure_identifier("YYY", "") is None
    assert measure_identifier("2.4. Beschleunigungsmaßnahmen", "F21Q0773") is None


# ---------------------------------------------------------------------------
# Key
# ---------------------------------------------------------------------------

def test_key_is_scoped_by_table():
    taken: set[str] = set()
    assert build_finve_key(4, "YYY F 03 E 0793", None, "Bau FinVe", 2024, taken) == "t4:F 03 E 0793"
    assert build_finve_key(5, "B0094 5/ Nr.1", None, "Revier", 2021, taken) == "t5:B0094"


def test_measure_without_an_identifier_is_keyed_by_name_and_year():
    key = build_finve_key(2, "YYY", None, "Förderrichtlinie Lärmsanierung", 1999, set())
    assert key == "t2:foerderrichtlinie-laermsanierung-1999"


def test_umlauts_are_transliterated_rather_than_dropped():
    key = build_finve_key(4, "YYY", None, "Änderungsvereinbarung ÜLS", 2026, set())
    assert key == "t4:aenderungsvereinbarung-uels-2026"


def test_repeated_identifier_is_disambiguated_in_document_order():
    taken: set[str] = set()
    first = build_finve_key(4, "YYY F 03 E 0793", None, "Bau FinVe", 2024, taken)
    second = build_finve_key(4, "YYY F 03 E 0793", None, "Bau FinVe", None, taken)
    third = build_finve_key(4, "YYY F 03 E 0793", None, "Bau FinVe", None, taken)
    assert [first, second, third] == [
        "t4:F 03 E 0793",
        "t4:F 03 E 0793#2",
        "t4:F 03 E 0793#3",
    ]


def test_key_stays_within_the_column_width():
    long_name = "Förderung der ERTMS-Ausrüstung " * 20
    key = build_finve_key(3, "YYY", None, long_name, 2021, set())
    assert len(key) <= 120
