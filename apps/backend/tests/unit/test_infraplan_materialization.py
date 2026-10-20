"""Infraplan rows → derived observations (services/progress_materialization.py)
and the Infraplan date in the forecast (services/progress_forecast.py)."""

from __future__ import annotations

from datetime import date

import pytest

from dashboard_backend.models.projects.progress_enums import (
    MainPhase,
    ObservationTrack,
    ParallelState,
    SourceType,
)
from dashboard_backend.services.progress_forecast import ExpectedDate, concrete_milestone_dates
from dashboard_backend.services.progress_materialization import (
    infraplan_entry_to_specs,
    infraplan_main_phase,
    infraplan_parl_relevant,
)

PUBLISHED = date(2026, 10, 6)


@pytest.mark.parametrize(
    ("section", "lph_from", "lph_to", "bau", "baurecht", "expected"),
    [
        ("BP_A", None, None, True, False, MainPhase.BAU),
        ("BP_A", 4, 4, False, True, MainPhase.GENEHMIGUNGSPLANUNG),
        ("BP_B", 3, 4, False, False, MainPhase.GENEHMIGUNGSPLANUNG),
        ("BP_C", 1, 1, False, False, MainPhase.VORPLANUNG),
        ("BP_C", 1, 2, False, False, MainPhase.VORPLANUNG),
        ("BP_D", None, None, False, False, MainPhase.NICHT_GESTARTET),
        ("INVKG", None, None, True, False, MainPhase.BAU),
        ("GVFG_A", 5, 9, False, False, MainPhase.BAU),
        ("GVFG_A", 5, 7, False, False, MainPhase.BAU),
        ("GVFG_A", 3, 4, False, False, MainPhase.GENEHMIGUNGSPLANUNG),
        ("GVFG_A", 4, 4, False, False, MainPhase.GENEHMIGUNGSPLANUNG),
        ("GVFG_C", 1, 2, False, False, MainPhase.VORPLANUNG),
        ("GVFG_C", 1, 4, False, False, None),
        ("GVFG_C", 1, 9, False, False, None),
        ("GVFG_C", None, None, False, False, None),  # "offen"
    ],
)
def test_main_phase_table(section, lph_from, lph_to, bau, baurecht, expected):
    assert (
        infraplan_main_phase(
            section=section, lph_from=lph_from, lph_to=lph_to, under_construction=bau, baurecht=baurecht
        )
        is expected
    )


def _specs(**overrides):
    values = {
        "infraplan_entry_id": 7,
        "section": "BP_A",
        "report_year": 2026,
        "observed_date": PUBLISHED,
        "lph_from": None,
        "lph_to": None,
        "under_construction": True,
        "baurecht": False,
        "ibn_year": 2030,
        "ibn_qualifier": None,
        "parl_state": None,
    }
    values.update(overrides)
    return infraplan_entry_to_specs(**values)


def test_bau_row_gives_phase_and_expected_commissioning():
    specs = _specs()

    main = [s for s in specs if s.track is ObservationTrack.MAIN and not s.is_expected]
    expected = [s for s in specs if s.is_expected]
    assert [(s.asserted_state, s.observed_date, s.confidence) for s in main] == [
        (MainPhase.BAU.value, PUBLISHED, None)
    ]
    assert [(s.asserted_state, s.observed_date) for s in expected] == [
        (MainPhase.IN_BETRIEB.value, date(2030, 12, 31))
    ]
    assert all(s.source_type is SourceType.INFRAPLAN and s.infraplan_entry_id == 7 for s in specs)


def test_baurecht_completes_pf_track():
    specs = _specs(under_construction=False, baurecht=True, lph_from=4, lph_to=4)

    pf = [s for s in specs if s.track is ObservationTrack.PF]
    assert [s.asserted_state for s in pf] == [ParallelState.ABGESCHLOSSEN.value]


@pytest.mark.parametrize(
    ("parl_state", "expected"),
    [("ABGESCHLOSSEN", "ABGESCHLOSSEN"), ("LAEUFT", "LAEUFT"), ("VORGESEHEN", None), ("NICHT_VEREINBART", None)],
)
def test_parl_track(parl_state, expected):
    parl = [s.asserted_state for s in _specs(parl_state=parl_state) if s.track is ObservationTrack.PARL]
    assert parl == ([expected] if expected else [])


@pytest.mark.parametrize(
    ("ibn_year", "qualifier", "has_date"),
    [(2030, None, True), (2035, "BIS", True), (None, "OFFEN", False), (2019, None, False)],
)
def test_expected_commissioning_rules(ibn_year, qualifier, has_date):
    specs = _specs(ibn_year=ibn_year, ibn_qualifier=qualifier)
    assert any(s.is_expected for s in specs) is has_date


def test_gvfg_row_lower_trust_and_suppressed_by_newer_edition():
    specs = _specs(section="GVFG_A", under_construction=False, lph_from=5, lph_to=9)
    assert {s.confidence for s in specs} == {0.75}

    assert _specs(section="GVFG_A", lph_from=5, lph_to=9, include_phase_and_date=False) == []


def test_parl_relevance_levels():
    assert infraplan_parl_relevant("NICHT_VEREINBART") is False
    assert infraplan_parl_relevant("VORGESEHEN") is True
    assert infraplan_parl_relevant(None) is None


def test_infraplan_date_competes_with_fulda_by_weight():
    today = date(2026, 11, 1)
    fulda = [ExpectedDate(MainPhase.IN_BETRIEB, date(2029, 12, 31), date(2026, 6, 1))]
    infraplan = [ExpectedDate(MainPhase.IN_BETRIEB, date(2030, 12, 31), PUBLISHED)]

    concrete = concrete_milestone_dates(
        pfas=[], fulda=fulda, infraplan=infraplan, manual_expected=[], today=today
    )
    assert concrete[MainPhase.IN_BETRIEB] == (date(2030, 12, 31), "Infraplan")

    manual = concrete_milestone_dates(
        pfas=[],
        fulda=fulda,
        infraplan=infraplan,
        manual_expected=[(MainPhase.IN_BETRIEB, date(2032, 1, 1))],
        today=today,
    )
    assert manual[MainPhase.IN_BETRIEB] == (date(2032, 1, 1), "Manuell")


def test_several_infraplan_rows_take_latest_year():
    concrete = concrete_milestone_dates(
        pfas=[],
        fulda=[],
        infraplan=[
            ExpectedDate(MainPhase.IN_BETRIEB, date(2028, 12, 31), PUBLISHED),
            ExpectedDate(MainPhase.IN_BETRIEB, date(2031, 12, 31), PUBLISHED),
        ],
        manual_expected=[],
        today=date(2026, 11, 1),
    )
    assert concrete[MainPhase.IN_BETRIEB] == (date(2031, 12, 31), "Infraplan")
