"""Unit tests for the pure multi-project timeline (services.progress_timeline)."""

from __future__ import annotations

from datetime import date

from dashboard_backend.models.projects.progress_enums import (
    MainPhase,
    ObservationTrack,
    SourceType,
)
from dashboard_backend.services.progress_derivation import ObservationInput
from dashboard_backend.services.progress_forecast import ExpectedDate, PfaForecastInput
from dashboard_backend.services.progress_timeline import (
    CERTAINTY_CONCRETE,
    CERTAINTY_EVIDENCE,
    KIND_PARL,
    KIND_PFB,
    KIND_PHASE,
    build_timeline,
)

TODAY = date(2026, 10, 1)


def _phase(result, phase):
    return [m for m in result.milestones if m.kind == KIND_PHASE and m.phase is phase]


def _obs(phase, observed, source=SourceType.VIB, confidence=None):
    return ObservationInput(
        source_type=source,
        track=ObservationTrack.MAIN,
        asserted_state=phase.value,
        observed_date=observed,
        confidence=confidence,
    )


def test_no_data_is_not_credible():
    result = build_timeline(today=TODAY)
    assert result.milestones == []
    assert result.has_credible_dates is False


def test_pfa_dates_aggregate_first_start_and_last_opening():
    result = build_timeline(
        today=TODAY,
        pfas=[
            PfaForecastInput(datum_pfb=date(2024, 5, 1), baubeginn=date(2027, 1, 1), inbetriebnahme=date(2031, 6, 1)),
            PfaForecastInput(datum_pfb=date(2025, 5, 1), baubeginn=date(2028, 1, 1), inbetriebnahme=date(2033, 6, 1)),
        ],
    )
    assert result.has_credible_dates is True
    [bau] = _phase(result, MainPhase.BAU)
    assert (bau.date, bau.source, bau.certainty) == (date(2027, 1, 1), "VIB-PFA", CERTAINTY_CONCRETE)
    [betrieb] = _phase(result, MainPhase.IN_BETRIEB)
    assert betrieb.date == date(2033, 6, 1)
    # The PFB is its own milestone, not a Genehmigungsplanung start.
    assert _phase(result, MainPhase.GENEHMIGUNGSPLANUNG) == []
    [pfb] = [m for m in result.milestones if m.kind == KIND_PFB]
    assert (pfb.date, pfb.source) == (date(2024, 5, 1), "VIB-PFA")


def test_manual_expected_wins_and_milestones_are_sorted():
    result = build_timeline(
        today=TODAY,
        pfas=[PfaForecastInput(baubeginn=date(2027, 1, 1))],
        fulda=[ExpectedDate(MainPhase.BAU, date(2026, 6, 1), date(2026, 6, 1))],
        manual_expected=[(MainPhase.BAU, date(2029, 3, 1)), (MainPhase.IN_BETRIEB, date(2035, 1, 1))],
    )
    [bau] = _phase(result, MainPhase.BAU)
    assert (bau.date, bau.source) == (date(2029, 3, 1), "Manuell")
    dates = [m.date for m in result.milestones]
    assert dates == sorted(dates)


def test_bvwp_like_estimates_are_absent_and_evidence_alone_is_not_credible():
    result = build_timeline(
        today=TODAY,
        observations=[_obs(MainPhase.VORPLANUNG, date(2023, 12, 31))],
    )
    [vp] = _phase(result, MainPhase.VORPLANUNG)
    assert vp.certainty == CERTAINTY_EVIDENCE
    assert vp.source == "VIB"
    assert result.has_credible_dates is False


def test_evidence_uses_earliest_credible_past_observation():
    result = build_timeline(
        today=TODAY,
        pfas=[PfaForecastInput(inbetriebnahme=date(2032, 1, 1))],
        observations=[
            _obs(MainPhase.BAU, date(2025, 12, 31)),
            _obs(MainPhase.BAU, date(2024, 1, 1), source=SourceType.FINVE),
            # below the credibility threshold → ignored
            _obs(MainPhase.BAU, date(2020, 1, 1), source=SourceType.MEDIEN, confidence=0.05),
            # future-dated observation is not evidence
            _obs(MainPhase.GENEHMIGUNGSPLANUNG, date(2027, 1, 1)),
        ],
    )
    [bau] = _phase(result, MainPhase.BAU)
    assert (bau.date, bau.source, bau.certainty) == (date(2024, 1, 1), "FinVe", CERTAINTY_EVIDENCE)
    assert _phase(result, MainPhase.GENEHMIGUNGSPLANUNG) == []


def test_concrete_date_suppresses_evidence_for_the_same_phase():
    result = build_timeline(
        today=TODAY,
        pfas=[PfaForecastInput(baubeginn=date(2025, 3, 1))],
        observations=[_obs(MainPhase.BAU, date(2024, 12, 31))],
    )
    [bau] = _phase(result, MainPhase.BAU)
    assert bau.certainty == CERTAINTY_CONCRETE


def test_evidence_contradicting_a_higher_earlier_phase_is_dropped():
    # VIB report says "Vorplanung" at year-end 2025, but construction began 2024.
    result = build_timeline(
        today=TODAY,
        pfas=[PfaForecastInput(baubeginn=date(2024, 3, 1))],
        observations=[_obs(MainPhase.VORPLANUNG, date(2025, 12, 31))],
    )
    assert _phase(result, MainPhase.VORPLANUNG) == []


def test_pooled_entries_reduce_per_phase():
    result = build_timeline(
        today=TODAY,
        manual_expected=[
            (MainPhase.BAU, date(2028, 1, 1)),
            (MainPhase.BAU, date(2027, 1, 1)),
            (MainPhase.IN_BETRIEB, date(2031, 1, 1)),
            (MainPhase.IN_BETRIEB, date(2034, 1, 1)),
        ],
    )
    assert _phase(result, MainPhase.BAU)[0].date == date(2027, 1, 1)
    assert _phase(result, MainPhase.IN_BETRIEB)[0].date == date(2034, 1, 1)


def test_editorial_pf_and_parl_dates():
    result = build_timeline(
        today=TODAY,
        pfas=[PfaForecastInput(datum_pfb=date(2020, 1, 1))],
        pf_dates=[date(2026, 2, 1), date(2025, 2, 1)],
        parl_dates=[date(2022, 11, 1)],
    )
    [pfb] = [m for m in result.milestones if m.kind == KIND_PFB]
    assert (pfb.date, pfb.source) == (date(2025, 2, 1), "Manuell")
    [parl] = [m for m in result.milestones if m.kind == KIND_PARL]
    assert parl.date == date(2022, 11, 1)
    assert result.has_credible_dates is True
