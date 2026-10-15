"""Header mapping and value normalisers of the Infraplan import."""

from __future__ import annotations

import pytest

from dashboard_backend.tasks.infraplan import join_cell_lines
from dashboard_backend.tasks.infraplan_columns import (
    UnknownColumnError,
    normalize_gvfg_key,
    parse_cost_ref,
    parse_german_number,
    parse_ibn,
    parse_parl,
    parse_project_numbers,
    parse_state,
    resolve_layout,
)

BP_HEADERS = [
    "Laufende Nummer | Projektnummer",
    "Bezeichnung",
    "Maßnahme",
    "Land",
    "Realisierungsstand / Lph",
    "Geplante Inbetriebnahme",
    "GWU in Mio. €",
    "Parlamentarische Befassung",
]
GVFG_HEADERS = [
    "Laufende Nummer | Projektnummer",
    "Maßnahme",
    "Land",
    "Realisierungsstand / Lph",
    "Geplante oder tatsächliche Inbetriebnahme",
    "Gesamtkosten in Mio. €",
]


def test_bedarfsplan_header_maps_all_fields():
    layout = resolve_layout(list(range(8)), BP_HEADERS)
    assert layout.fields == (
        "lfd_projekt", "bezeichnung", "massnahme", "land", "state", "ibn", "cost", "parl",
    )
    assert layout.cost_kind == "GWU"


def test_gvfg_header_has_gesamtkosten():
    layout = resolve_layout(list(range(6)), GVFG_HEADERS)
    assert layout.fields == ("lfd_projekt", "massnahme", "land", "state", "ibn", "cost")
    assert layout.cost_kind == "GESAMTKOSTEN"


def test_unknown_header_is_an_error_not_a_guess():
    with pytest.raises(UnknownColumnError):
        resolve_layout(list(range(3)), ["Laufende Nummer | Projektnummer", "Maßnahme", "Bemerkung"])


def test_missing_required_column_is_an_error():
    with pytest.raises(UnknownColumnError):
        resolve_layout(list(range(2)), ["Laufende Nummer | Projektnummer", "Maßnahme"])


def test_column_of_uses_left_edges():
    layout = resolve_layout([80.0, 150.0, 200.0], ["Laufende Nummer | Projektnummer", "Maßnahme", "GWU in Mio. €"])
    assert layout.column_of(83.6) == 0
    assert layout.column_of(149.5) == 1  # one point of tolerance
    assert layout.column_of(430.0) == 2


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2030", (2030, None)),
        ("offen", (None, "OFFEN")),
        ("bis 2035", (2035, "BIS")),
        ("2029/2030", (2030, "SPANNE")),
        ("2023/2024", (2024, "SPANNE")),
        ("2022 - 2029", (2029, "SPANNE")),
        ("2022–2029", (2029, "SPANNE")),
        ("mehrere", (None, None)),
        (None, (None, None)),
    ],
)
def test_parse_ibn(raw, expected):
    assert parse_ibn(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1.720,48", 1720.48),
        ("44,58", 44.58),
        ("11.364,00", 11364.0),
        ("0,33", 0.33),
        ("offen", None),
        ("Ref. Teil B 20 | E.1637290100", None),
        (None, None),
    ],
)
def test_parse_german_number(raw, expected):
    assert parse_german_number(raw) == expected


def test_parse_cost_ref():
    assert parse_cost_ref("Ref. Teil B 20 | E.1637290100") == ("BP_B", 20)
    assert parse_cost_ref("Ref. Teil A 3 | E. 1631230009") == ("BP_A", 3)
    assert parse_cost_ref("1.720,48") is None


def test_parse_state():
    bau = parse_state("Bau")
    assert bau.under_construction and bau.lph_from is None
    baurecht = parse_state("Lph 4 abgeschlossen – durchgängiges Baurecht vorliegend")
    assert baurecht.baurecht and (baurecht.lph_from, baurecht.lph_to) == (4, 4)
    assert (parse_state("Lph 3-4").lph_from, parse_state("Lph 3-4").lph_to) == (3, 4)
    assert (parse_state("Lph 5 - 9").lph_from, parse_state("Lph 5 - 9").lph_to) == (5, 9)
    assert (parse_state("Lph 8 / 9").lph_from, parse_state("Lph 8 / 9").lph_to) == (8, 9)
    assert parse_state("offen").lph_from is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("abgeschlossen – Entschließung BT liegt vor", "ABGESCHLOSSEN"),
        ("abgeschlossen - Entschließung BT liegt vor", "ABGESCHLOSSEN"),
        ("Übergabe seitens DB InfraGO AG erfolgt – Verfahren läuft", "LAEUFT"),
        ("vorgesehen", "VORGESEHEN"),
        ("nicht vereinbart", "NICHT_VEREINBART"),
        (None, None),
    ],
)
def test_parse_parl(raw, expected):
    assert parse_parl(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("07 D 2825_A", "07D2825_A"),
        ("7 D 2825 _A", "07D2825_A"),
        ("09 G 5051_A", "09G5051_A"),
        ("ohne Schlüssel", None),
    ],
)
def test_normalize_gvfg_key(raw, expected):
    assert normalize_gvfg_key(raw) == expected


def test_parse_project_numbers_per_section():
    assert parse_project_numbers("E.1637230040 // X.016030472300201", "BP_A") == [
        "E.1637230040",
        "X.016030472300201",
    ]
    assert parse_project_numbers("E.1637350003// T.016076026", "BP_A") == [
        "E.1637350003",
        "T.016076026",
    ]
    assert parse_project_numbers("/", "BP_D") == []
    assert parse_project_numbers("12 D 1210_S", "GVFG_A") == ["12D1210_S"]
    assert parse_project_numbers("19)", "INVKG") == ["InvKG Nr. 19"]


def test_join_cell_lines_undoes_hyphenation():
    assert join_cell_lines(["Berlin (Lehr-", "ter Stamm-", "bahn)"]) == "Berlin (Lehrter Stammbahn)"
    assert join_cell_lines(["Brandenburg/", "Sachsen-", "Anhalt"]) == "Brandenburg/Sachsen-Anhalt"
    assert join_cell_lines(["Neumarkt (Opf.) -", "Regensburg"]) == "Neumarkt (Opf.) - Regensburg"
