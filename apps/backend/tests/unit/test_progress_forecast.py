"""Unit tests for the pure planning-state forecast."""

from __future__ import annotations

from datetime import date

from dashboard_backend.models.projects.progress_enums import DatePrecision as P
from dashboard_backend.models.projects.progress_enums import MainPhase
from dashboard_backend.services.progress_forecast import (
    BvwpDurations,
    ExpectedDate,
    PfaForecastInput,
    build_forecast,
    concrete_milestone_dates,
    reduce_expected,
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
        fulda=[ExpectedDate(MainPhase.BAU, date(2028, 6, 1), date(2026, 6, 3))],
    )
    bau = next(s for s in r.next_steps if s.phase is MainPhase.BAU)
    assert bau.expected_date == date(2028, 6, 1)
    assert bau.source == "Fulda-Runde"


def test_manual_expected_overrides_all_other_sources():
    # Editorial expected dates win over VIB-PFA, Fulda and BVWP alike.
    bvwp = BvwpDurations(outstanding_planning=2.0, build=3.0)
    pfas = [PfaForecastInput(inbetriebnahme=date(2030, 1, 1))]
    r = build_forecast(
        effective_phase=MainPhase.BAU,
        today=TODAY,
        pfas=pfas,
        bvwp=bvwp,
        fulda=[ExpectedDate(MainPhase.IN_BETRIEB, date(2031, 1, 1), date(2026, 6, 3))],
        manual_expected=[(MainPhase.IN_BETRIEB, date(2029, 12, 1))],
    )
    ib = next(s for s in r.next_steps if s.phase is MainPhase.IN_BETRIEB)
    assert ib.expected_date == date(2029, 12, 1)
    assert ib.source == "Manuell"
    assert r.has_data is True


def test_manual_expected_fills_gap_with_no_other_source():
    r = build_forecast(
        effective_phase=MainPhase.GENEHMIGUNGSPLANUNG,
        today=TODAY,
        manual_expected=[(MainPhase.IN_BETRIEB, date(2032, 5, 1))],
    )
    ib = next(s for s in r.next_steps if s.phase is MainPhase.IN_BETRIEB)
    assert ib.expected_date == date(2032, 5, 1)
    assert ib.source == "Manuell"


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


# --- Skipped planning phases per project group (#164) ------------------------

_RENEWAL_SKIPS = frozenset({MainPhase.VORPLANUNG, MainPhase.GENEHMIGUNGSPLANUNG})


def test_skipped_phases_jump_straight_to_construction():
    r = build_forecast(
        effective_phase=MainPhase.NICHT_GESTARTET,
        today=TODAY,
        skipped_phases=_RENEWAL_SKIPS,
    )
    assert [s.phase for s in r.next_steps] == [MainPhase.BAU, MainPhase.IN_BETRIEB]


def test_skipped_phase_with_concrete_date_stays():
    # Data wins: a dated milestone keeps the phase in the forecast.
    r = build_forecast(
        effective_phase=MainPhase.NICHT_GESTARTET,
        today=TODAY,
        manual_expected=[(MainPhase.GENEHMIGUNGSPLANUNG, date(2027, 1, 1))],
        skipped_phases=_RENEWAL_SKIPS,
    )
    assert [s.phase for s in r.next_steps] == [
        MainPhase.GENEHMIGUNGSPLANUNG,
        MainPhase.BAU,
        MainPhase.IN_BETRIEB,
    ]
    assert r.estimated_phase_end == date(2027, 1, 1)


def test_skipped_phases_use_bvwp_construction_date_as_phase_end():
    bvwp = BvwpDurations(outstanding_planning=2.0, build=3.0)
    r = build_forecast(
        effective_phase=MainPhase.NICHT_GESTARTET,
        today=TODAY,
        bvwp=bvwp,
        skipped_phases=_RENEWAL_SKIPS,
    )
    assert r.next_steps[0].phase is MainPhase.BAU
    assert r.estimated_phase_end.year == 2028


# --- VIB-PFA vs. Fulda-Runde: credibility × recency (feature-fulda-import.md, W1)


def _bau(pfa_reported, fulda_reported):
    concrete = concrete_milestone_dates(
        pfas=[PfaForecastInput(baubeginn=date(2027, 1, 1), reported_on=pfa_reported)],
        fulda=[ExpectedDate(MainPhase.BAU, date(2029, 12, 31), fulda_reported)],
        manual_expected=[],
        today=TODAY,
    )
    bau = concrete[MainPhase.BAU]
    return bau.date, bau.source


def test_newer_fulda_beats_older_vib_even_with_a_later_date():
    # Fulda 0.55 × fresh vs. VIB 0.6 × three years old: Fulda wins although its
    # date is later (no "earlier date overrides" rule any more).
    assert _bau(date(2023, 12, 31), date(2026, 6, 3)) == (date(2029, 12, 31), "Fulda-Runde")


def test_equally_fresh_vib_beats_fulda():
    assert _bau(date(2026, 6, 1), date(2026, 6, 3)) == (date(2027, 1, 1), "VIB-PFA")


def test_newer_vib_beats_older_fulda():
    assert _bau(date(2026, 5, 1), date(2023, 6, 1)) == (date(2027, 1, 1), "VIB-PFA")


def test_reduce_expected_pools_subtree_claims():
    claims = [
        ExpectedDate(MainPhase.BAU, date(2028, 1, 1), date(2025, 6, 1)),
        ExpectedDate(MainPhase.BAU, date(2027, 1, 1), date(2026, 6, 1)),
        ExpectedDate(MainPhase.IN_BETRIEB, date(2030, 1, 1), None),
        ExpectedDate(MainPhase.IN_BETRIEB, date(2032, 1, 1), None),
    ]
    pooled = {c.phase: c for c in reduce_expected(claims)}
    assert pooled[MainPhase.BAU] == ExpectedDate(MainPhase.BAU, date(2027, 1, 1), date(2026, 6, 1))
    assert pooled[MainPhase.IN_BETRIEB].date == date(2032, 1, 1)


# --- Datumsqualifikation: precision travels through the forecast -------------

def _step(result, phase):
    return next(s for s in result.next_steps if s.phase is phase)


def test_not_before_construction_yields_not_before_commissioning():
    # „nach 2031“: Baubeginn only a lower bound → the assumed opening is one too.
    r = build_forecast(
        effective_phase=MainPhase.NICHT_GESTARTET,
        today=TODAY,
        manual_expected=[ExpectedDate(MainPhase.BAU, date(2032, 1, 1), precision=P.NOT_BEFORE)],
        assumed_build_months=6,
    )
    bau, ibn = _step(r, MainPhase.BAU), _step(r, MainPhase.IN_BETRIEB)
    assert (bau.precision, bau.source) == (P.NOT_BEFORE, "Manuell")
    assert (ibn.expected_date, ibn.precision, ibn.source) == (date(2032, 7, 1), P.NOT_BEFORE, "Annahme")
    assert ibn.derivation == "Annahme: 6 Monate Bauzeit ab Baubeginn nach 2031 (Manuell)"


def test_year_construction_plus_build_period_is_assumed():
    r = build_forecast(
        effective_phase=MainPhase.NICHT_GESTARTET,
        today=TODAY,
        manual_expected=[ExpectedDate(MainPhase.BAU, date(2028, 1, 1), precision=P.YEAR)],
        assumed_build_months=6,
    )
    ibn = _step(r, MainPhase.IN_BETRIEB)
    assert (ibn.expected_date, ibn.precision) == (date(2028, 7, 1), P.ASSUMED)
    assert "6 Monate Bauzeit ab Baubeginn 2028" in ibn.derivation
    assert _step(r, MainPhase.BAU).precision is P.YEAR


def test_build_period_never_overrides_a_named_commissioning():
    r = build_forecast(
        effective_phase=MainPhase.NICHT_GESTARTET,
        today=TODAY,
        manual_expected=[
            (MainPhase.BAU, date(2028, 2, 6)),
            (MainPhase.IN_BETRIEB, date(2028, 11, 30)),
        ],
        assumed_build_months=6,
    )
    ibn = _step(r, MainPhase.IN_BETRIEB)
    assert (ibn.expected_date, ibn.source, ibn.precision) == (date(2028, 11, 30), "Manuell", P.EXACT)


def test_without_group_rule_no_commissioning_is_assumed():
    r = build_forecast(
        effective_phase=MainPhase.NICHT_GESTARTET,
        today=TODAY,
        manual_expected=[(MainPhase.BAU, date(2028, 1, 1))],
    )
    assert _step(r, MainPhase.IN_BETRIEB).expected_date is None


def test_precision_of_derived_claims_and_pfa_dates():
    concrete = concrete_milestone_dates(
        pfas=[
            PfaForecastInput(
                baubeginn=date(2027, 12, 15),
                baubeginn_precision=P.MONTH,
                reported_on=TODAY,
            )
        ],
        fulda=[],
        infraplan=[ExpectedDate(MainPhase.IN_BETRIEB, date(2030, 12, 31), TODAY, precision=P.YEAR)],
        manual_expected=[],
        today=TODAY,
    )
    assert concrete[MainPhase.BAU].precision is P.MONTH
    assert (concrete[MainPhase.IN_BETRIEB].source, concrete[MainPhase.IN_BETRIEB].precision) == (
        "Infraplan",
        P.YEAR,
    )


def test_bvwp_estimates_are_assumed():
    r = build_forecast(
        effective_phase=MainPhase.VORPLANUNG,
        today=TODAY,
        bvwp=BvwpDurations(outstanding_planning=4, build=3),
    )
    for phase in (MainPhase.BAU, MainPhase.IN_BETRIEB):
        step = _step(r, phase)
        assert (step.source, step.precision) == ("BVWP", P.ASSUMED)
        assert step.derivation.startswith("Schätzung")


def test_bvwp_build_on_a_lower_bound_stays_a_lower_bound():
    r = build_forecast(
        effective_phase=MainPhase.GENEHMIGUNGSPLANUNG,
        today=TODAY,
        bvwp=BvwpDurations(build=2),
        manual_expected=[ExpectedDate(MainPhase.BAU, date(2032, 1, 1), precision=P.NOT_BEFORE)],
    )
    assert _step(r, MainPhase.IN_BETRIEB).precision is P.NOT_BEFORE


def test_remaining_text_claims_no_duration_for_a_lower_bound():
    r = build_forecast(
        effective_phase=MainPhase.NICHT_GESTARTET,
        today=TODAY,
        manual_expected=[ExpectedDate(MainPhase.BAU, date(2032, 1, 1), precision=P.NOT_BEFORE)],
        skipped_phases={MainPhase.VORPLANUNG, MainPhase.GENEHMIGUNGSPLANUNG},
    )
    assert r.estimated_phase_end_precision is P.NOT_BEFORE
    assert r.remaining_text == "Ende der aktuellen Phase offen (nach 2031)"


def test_pooled_claims_keep_the_precision_of_the_chosen_date():
    pooled = {
        c.phase: c
        for c in reduce_expected(
            [
                ExpectedDate(MainPhase.IN_BETRIEB, date(2030, 12, 31), precision=P.YEAR),
                ExpectedDate(MainPhase.IN_BETRIEB, date(2032, 1, 1), precision=P.NOT_BEFORE),
            ]
        )
    }
    assert pooled[MainPhase.IN_BETRIEB].precision is P.NOT_BEFORE
