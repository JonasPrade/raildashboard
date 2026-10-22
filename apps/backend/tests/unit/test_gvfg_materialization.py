"""GVFG Vorhaben → derived observations (services/progress_materialization.py)
and the GVFG date in the forecast (services/progress_forecast.py)."""

from __future__ import annotations

from datetime import date

import pytest

from dashboard_backend.models.projects.progress_enums import DatePrecision, MainPhase, ObservationTrack, SourceType
from dashboard_backend.services.progress_derivation import SOURCE_TYPE_DEFAULT_TRUST
from dashboard_backend.services.progress_forecast import ExpectedDate, concrete_milestone_dates
from dashboard_backend.services.progress_materialization import (
    gvfg_entry_to_specs,
    gvfg_ibn_year,
    gvfg_lph_main_phase,
)

STAND = date(2025, 7, 18)


@pytest.mark.parametrize(
    ("lph", "expected"),
    [
        ("5 - 9", MainPhase.BAU),
        ("5 - 8", MainPhase.BAU),
        ("8", MainPhase.BAU),
        ("9", MainPhase.IN_BETRIEB),
        ("3 - 4", MainPhase.GENEHMIGUNGSPLANUNG),
        ("3", MainPhase.GENEHMIGUNGSPLANUNG),
        ("1 - 2", MainPhase.VORPLANUNG),
        ("2", MainPhase.VORPLANUNG),
        ("1 - 9", None),
        ("4 - 8", None),
        ("4, 9", None),
        ("1 - 3 / 5 - 9", None),
        (None, None),
        ("", None),
    ],
)
def test_lph_table(lph, expected):
    assert gvfg_lph_main_phase(lph) is expected


def _specs(**overrides):
    values = {
        "gvfg_entry_id": 3,
        "edition": "2025–2029",
        "stand": STAND,
        "lph": None,
        "construction_start": None,
        "commissioning_planned": None,
        "commissioning_actual": None,
    }
    values.update(overrides)
    return gvfg_entry_to_specs(**values)


def _main(specs):
    return [s for s in specs if s.track is ObservationTrack.MAIN and not s.is_expected]


def _expected(specs):
    return [s for s in specs if s.is_expected]


def test_construction_start_alone_means_bau():
    # 08 D 120_S (S60 Böblingen – Renningen): only "Baubeginn 2004" is printed.
    specs = _specs(construction_start=2004)
    assert len(specs) == 1
    spec = specs[0]
    assert (spec.source_type, spec.asserted_state, spec.observed_date) == (
        SourceType.GVFG,
        MainPhase.BAU.value,
        STAND,
    )
    assert spec.confidence is None  # source default
    assert spec.gvfg_entry_id == 3
    assert spec.note == "GVFG 2025–2029: Baubeginn 2004"


def test_future_construction_start_says_nothing():
    assert _specs(construction_start=2027) == []


def test_past_commissioning_means_in_betrieb_without_forecast():
    specs = _specs(lph="5 - 9", construction_start=2010, commissioning_planned=2026, commissioning_actual=2017)
    assert [s.asserted_state for s in _main(specs)] == [MainPhase.IN_BETRIEB.value]
    assert _main(specs)[0].note == "GVFG 2025–2029: Inbetriebnahme 2017, Lph 5 - 9, Baubeginn 2010"
    assert _expected(specs) == []


def test_lph_9_means_in_betrieb():
    specs = _specs(lph="9")
    assert [s.asserted_state for s in specs] == [MainPhase.IN_BETRIEB.value]


def test_strongest_phase_wins():
    specs = _specs(lph="3 - 4", construction_start=2024)
    assert [s.asserted_state for s in _main(specs)] == [MainPhase.BAU.value]


def test_future_actual_is_the_expected_commissioning():
    specs = _specs(lph="5 - 8", commissioning_planned=2026, commissioning_actual=2028)
    assert [s.asserted_state for s in _main(specs)] == [MainPhase.BAU.value]
    (expected,) = _expected(specs)
    assert (expected.asserted_state, expected.observed_date, expected.note) == (
        MainPhase.IN_BETRIEB.value,
        date(2028, 12, 31),
        "GVFG 2025–2029: geplante Inbetriebnahme 2028",
    )


def test_commissioning_in_the_stand_year_is_expected_not_reached():
    specs = _specs(commissioning_planned=2025, commissioning_actual=2025)
    assert _main(specs) == []
    assert [s.observed_date for s in _expected(specs)] == [date(2025, 12, 31)]


def test_planned_counts_only_without_actual():
    assert [s.observed_date for s in _expected(_specs(commissioning_planned=2030))] == [date(2030, 12, 31)]
    # A planned year before the Stand year: Restarbeiten, no forecast.
    assert _specs(commissioning_planned=2019) == []


def test_ibn_year_prefers_actual():
    assert gvfg_ibn_year(2026, 2028) == 2028
    assert gvfg_ibn_year(2026, None) == 2026
    assert gvfg_ibn_year(None, None) is None


def test_gvfg_trust_matches_gvfg_rows_of_the_infraplan():
    assert SOURCE_TYPE_DEFAULT_TRUST[SourceType.GVFG] == 0.75


def test_gvfg_date_in_the_forecast():
    today = date(2026, 1, 1)
    concrete = concrete_milestone_dates(
        pfas=[],
        fulda=[],
        manual_expected=[],
        today=today,
        gvfg=[
            ExpectedDate(MainPhase.IN_BETRIEB, date(2027, 12, 31), STAND),
            ExpectedDate(MainPhase.IN_BETRIEB, date(2028, 12, 31), STAND),
        ],
    )
    assert (concrete[MainPhase.IN_BETRIEB].date, concrete[MainPhase.IN_BETRIEB].source) == (date(2028, 12, 31), "GVFG")

    # A more recent Infraplan beats the older GVFG edition.
    concrete = concrete_milestone_dates(
        pfas=[],
        fulda=[],
        manual_expected=[],
        today=today,
        gvfg=[ExpectedDate(MainPhase.IN_BETRIEB, date(2028, 12, 31), date(2023, 9, 1))],
        infraplan=[ExpectedDate(MainPhase.IN_BETRIEB, date(2030, 12, 31), date(2025, 10, 6))],
    )
    assert (concrete[MainPhase.IN_BETRIEB].date, concrete[MainPhase.IN_BETRIEB].source) == (date(2030, 12, 31), "Infraplan")


def test_expected_commissioning_is_the_timetable_change():
    (expected,) = _expected(_specs(commissioning_planned=2028))
    assert (expected.observed_date, expected.date_precision) == (date(2028, 12, 31), DatePrecision.MONTH)
