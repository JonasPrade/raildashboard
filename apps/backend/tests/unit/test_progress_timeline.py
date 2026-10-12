"""Unit tests for the pure multi-project timeline (services.progress_timeline)."""

from __future__ import annotations

from datetime import date

from dashboard_backend.models.projects.progress_enums import (
    MainPhase,
    ObservationTrack,
    SourceType,
)
from dashboard_backend.services.progress_derivation import ObservationInput
from dashboard_backend.services.progress_forecast import PfaForecastInput
from dashboard_backend.services.progress_timeline import (
    CERTAINTY_CONCRETE,
    CERTAINTY_EVIDENCE,
    KIND_PARL,
    KIND_PFB,
    KIND_PHASE,
    ConstructionUnitInput,
    build_timeline,
    construction_periods,
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
        fulda=[(MainPhase.BAU, date(2026, 6, 1))],
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


# --- Construction periods of a pooled superior row ---------------------------


def _stage(bau, ib):
    expected = [(MainPhase.BAU, bau)] if bau else []
    if ib:
        expected.append((MainPhase.IN_BETRIEB, ib))
    return ConstructionUnitInput(manual_expected=expected)


def test_separate_stages_give_two_periods():
    # HLK 11: two stages, 2028 and 2031, with no construction in between.
    units = [
        ConstructionUnitInput(),  # the superior itself has no dates
        _stage(date(2028, 1, 1), date(2028, 7, 1)),
        _stage(date(2031, 1, 1), date(2031, 7, 1)),
    ]
    assert construction_periods(units) == [
        (date(2028, 1, 1), date(2028, 7, 1)),
        (date(2031, 1, 1), date(2031, 7, 1)),
    ]


def test_overlapping_and_touching_stages_merge_into_one():
    overlapping = [_stage(date(2028, 1, 1), date(2029, 1, 1)), _stage(date(2028, 6, 1), date(2030, 1, 1))]
    touching = [_stage(date(2028, 1, 1), date(2028, 7, 1)), _stage(date(2028, 7, 1), date(2029, 1, 1))]
    # One continuous period is the plain BAU segment: nothing extra to report.
    assert construction_periods(overlapping) == []
    assert construction_periods(touching) == []


def test_three_stages_merge_partially():
    units = [
        _stage(date(2028, 1, 1), date(2028, 7, 1)),
        _stage(date(2028, 5, 1), date(2029, 1, 1)),
        _stage(date(2031, 1, 1), date(2031, 7, 1)),
    ]
    assert construction_periods(units) == [
        (date(2028, 1, 1), date(2029, 1, 1)),
        (date(2031, 1, 1), date(2031, 7, 1)),
    ]


def test_open_ended_stage_cancels_the_split():
    units = [
        _stage(date(2028, 1, 1), date(2028, 7, 1)),
        _stage(date(2029, 1, 1), None),  # end unknown: may fill the gap
        _stage(date(2031, 1, 1), date(2031, 7, 1)),
    ]
    assert construction_periods(units) == []


def test_opening_only_member():
    old = _stage(None, date(2015, 1, 1))  # finished long before: harmless
    inside = _stage(None, date(2030, 1, 1))  # built sometime before 2030: unknown
    stages = [_stage(date(2028, 1, 1), date(2028, 7, 1)), _stage(date(2031, 1, 1), date(2031, 7, 1))]
    assert len(construction_periods([old, *stages])) == 2
    assert construction_periods([inside, *stages]) == []


def test_contradicting_stage_cancels_the_split():
    units = [
        _stage(date(2028, 1, 1), date(2027, 1, 1)),
        _stage(date(2031, 1, 1), date(2031, 7, 1)),
    ]
    assert construction_periods(units) == []


def test_stage_dates_from_pfa_sections():
    units = [
        ConstructionUnitInput(pfas=[PfaForecastInput(baubeginn=date(2027, 3, 1), inbetriebnahme=date(2028, 1, 1))]),
        ConstructionUnitInput(pfas=[PfaForecastInput(baubeginn=date(2030, 3, 1), inbetriebnahme=date(2031, 1, 1))]),
    ]
    assert len(construction_periods(units)) == 2


def test_build_timeline_carries_periods_and_keeps_milestones():
    stage1 = _stage(date(2028, 1, 1), date(2028, 7, 1))
    stage2 = _stage(date(2031, 1, 1), date(2031, 7, 1))
    result = build_timeline(
        today=TODAY,
        manual_expected=[*stage1.manual_expected, *stage2.manual_expected],
        construction_units=[stage1, stage2],
    )
    # Pooled milestones unchanged: first BAU start, last opening.
    assert _phase(result, MainPhase.BAU)[0].date == date(2028, 1, 1)
    assert _phase(result, MainPhase.IN_BETRIEB)[0].date == date(2031, 7, 1)
    assert result.construction_periods == [
        (date(2028, 1, 1), date(2028, 7, 1)),
        (date(2031, 1, 1), date(2031, 7, 1)),
    ]


def test_build_timeline_single_unit_has_no_periods():
    unit = _stage(date(2028, 1, 1), date(2028, 7, 1))
    result = build_timeline(today=TODAY, manual_expected=unit.manual_expected, construction_units=[unit])
    assert result.construction_periods == []
