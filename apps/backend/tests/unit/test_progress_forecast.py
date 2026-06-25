"""Unit tests for the pure planning-state forecast."""

from __future__ import annotations

from datetime import date

from dashboard_backend.models.projects.progress_enums import MainPhase
from dashboard_backend.services.progress_forecast import (
    BvwpDurations,
    PfaForecastInput,
    build_forecast,
)

TODAY = date(2026, 6, 18)


def test_no_inputs_means_no_data():
    r = build_forecast(effective_phase=MainPhase.VORPLANUNG, today=TODAY)
    assert r.has_data is False
    assert r.remaining_text is None
    assert r.estimated_phase_end is None
    # Steps still listed (phases after current), but without dates.
    assert [s.phase for s in r.next_steps] == [
        MainPhase.GENEHMIGUNGSPLANUNG,
        MainPhase.BAU,
        MainPhase.IN_BETRIEB,
    ]
    assert all(s.expected_date is None for s in r.next_steps)


def test_concrete_pfa_dates_drive_next_steps():
    pfas = [
        PfaForecastInput(baubeginn=date(2027, 4, 1), inbetriebnahme=date(2030, 9, 1)),
        PfaForecastInput(baubeginn=date(2028, 1, 1), inbetriebnahme=date(2031, 1, 1)),
    ]
    r = build_forecast(
        effective_phase=MainPhase.GENEHMIGUNGSPLANUNG, today=TODAY, pfas=pfas
    )
    bau = next(s for s in r.next_steps if s.phase is MainPhase.BAU)
    ib = next(s for s in r.next_steps if s.phase is MainPhase.IN_BETRIEB)
    assert bau.expected_date == date(2027, 4, 1)  # earliest construction start
    assert ib.expected_date == date(2031, 1, 1)  # latest in-service
    assert bau.source == "VIB-PFA"
    assert r.estimated_phase_end == date(2027, 4, 1)
    assert r.has_data is True
    assert r.remaining_text is not None


def test_bvwp_durations_used_as_fallback():
    bvwp = BvwpDurations(outstanding_planning=3.0, build=4.0)
    r = build_forecast(effective_phase=MainPhase.VORPLANUNG, today=TODAY, bvwp=bvwp)
    bau = next(s for s in r.next_steps if s.phase is MainPhase.BAU)
    ib = next(s for s in r.next_steps if s.phase is MainPhase.IN_BETRIEB)
    assert bau.source == "BVWP"
    assert bau.expected_date.year == 2029  # 2026 + 3y
    assert ib.expected_date.year == 2033  # BAU + 4y
    assert r.has_data is True


def test_concrete_date_overrides_bvwp():
    bvwp = BvwpDurations(outstanding_planning=10.0, build=10.0)
    pfas = [PfaForecastInput(baubeginn=date(2027, 1, 1))]
    r = build_forecast(
        effective_phase=MainPhase.GENEHMIGUNGSPLANUNG, today=TODAY, pfas=pfas, bvwp=bvwp
    )
    bau = next(s for s in r.next_steps if s.phase is MainPhase.BAU)
    assert bau.expected_date == date(2027, 1, 1)
    assert bau.source == "VIB-PFA"


def test_fulda_announcement_fills_gap():
    r = build_forecast(
        effective_phase=MainPhase.VORPLANUNG,
        today=TODAY,
        fulda=[(MainPhase.BAU, date(2028, 6, 1))],
    )
    bau = next(s for s in r.next_steps if s.phase is MainPhase.BAU)
    assert bau.expected_date == date(2028, 6, 1)
    assert bau.source == "Fulda-Runde"


def test_in_betrieb_has_no_next_steps():
    r = build_forecast(effective_phase=MainPhase.IN_BETRIEB, today=TODAY)
    assert r.next_steps == []
    assert r.estimated_phase_end is None


def test_remaining_text_handles_past_date():
    pfas = [PfaForecastInput(baubeginn=date(2020, 1, 1))]
    r = build_forecast(
        effective_phase=MainPhase.GENEHMIGUNGSPLANUNG, today=TODAY, pfas=pfas
    )
    assert "überschritten" in r.remaining_text
