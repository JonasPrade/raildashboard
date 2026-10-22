"""Unit tests for the pure planning-state derivation logic (no DB)."""

from __future__ import annotations

from datetime import date

import pytest

from dashboard_backend.models.projects.progress_enums import (
    LifecycleStatus,
    MainPhase,
    ObservationTrack,
    ParallelState,
    SourceType,
)
from dashboard_backend.services.progress_derivation import (
    CREDIBILITY_THRESHOLD,
    AggregationNode,
    ObservationInput,
    aggregate_span,
    aggregate_tree,
    derive_headline,
    effective_confidence,
    recency_decay,
    stored_headline_phase,
)

TODAY = date(2026, 6, 18)


def _main(state: str, *, source=SourceType.MANUELL, dt=TODAY, conf=None, oid=None):
    return ObservationInput(
        source_type=source,
        track=ObservationTrack.MAIN,
        asserted_state=state,
        observed_date=dt,
        confidence=conf,
        id=oid,
    )


# --- Headline: newest report wins, trust within a year, bounds raise ---------


def test_equal_confidence_resolves_to_higher_phase():
    # All three observations share the same effective confidence (same source,
    # date, no explicit value), so the tie resolves to the highest phase.
    result = derive_headline(
        [_main("VORPLANUNG", oid=1), _main("BAU", oid=2), _main("GENEHMIGUNGSPLANUNG", oid=3)],
        has_pf=False,
        parl_relevant=False,
        today=TODAY,
    )
    assert result.computed_phase is MainPhase.BAU
    assert result.effective_phase is MainPhase.BAU
    decisive = [c.id for c in result.contributions if c.was_decisive]
    assert decisive == [2]


def test_high_confidence_manual_beats_low_confidence_derived_higher_phase():
    # Project-2019 scenario: an editor sets GENEHMIGUNGSPLANUNG at full
    # confidence over a FinVe-derived BAU lower bound. The manual statement
    # must win even though BAU is the higher phase.
    manual = _main("GENEHMIGUNGSPLANUNG", source=SourceType.MANUELL, conf=1.0, oid=97)
    finve = _main("BAU", source=SourceType.FINVE, dt=date(2023, 1, 1), oid=98)
    result = derive_headline([manual, finve], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.computed_phase is MainPhase.GENEHMIGUNGSPLANUNG
    assert result.computed_confidence == 1.0
    decisive = [c.id for c in result.contributions if c.was_decisive]
    assert decisive == [97]


def test_recent_vib_beats_old_finve_bound():
    # Regression (screenshot 2026-10-22): a 15-year-old FinVe outranked the
    # 2023 VIB because both sat on the recency floor. The FinVe is only a lower
    # bound ("at least Bau"); the newer report says the line is in operation.
    vib = _main("IN_BETRIEB", source=SourceType.VIB, dt=date(2023, 12, 31), oid=1)
    finve = _main("BAU", source=SourceType.FINVE, dt=date(2011, 1, 1), oid=2)
    result = derive_headline(
        [vib, finve], has_pf=False, parl_relevant=False, today=date(2026, 10, 22)
    )
    assert result.computed_phase is MainPhase.IN_BETRIEB
    assert [c.id for c in result.contributions if c.was_decisive] == [1]
    assert result.conflict is None
    assert next(c for c in result.contributions if c.id == 2).is_lower_bound is True


def test_newer_report_wins_outside_trust_window():
    # VIB is trusted less than the Bauportal, but two years newer.
    old = _main("BAU", source=SourceType.BAUPORTAL, dt=date(2023, 6, 1), oid=1)
    new = _main("IN_BETRIEB", source=SourceType.VIB, dt=date(2025, 12, 31), oid=2)
    result = derive_headline([old, new], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.computed_phase is MainPhase.IN_BETRIEB
    assert result.conflict is None


def test_trust_decides_within_window():
    # Media is three months newer than the VIB but trusted less; both fall into
    # the same one-year window, so the VIB decides. No set-back → no conflict.
    vib = _main("BAU", source=SourceType.VIB, dt=date(2025, 12, 31), oid=1)
    media = _main("IN_BETRIEB", source=SourceType.MEDIEN, dt=date(2026, 3, 31), oid=2)
    result = derive_headline([vib, media], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.computed_phase is MainPhase.BAU
    assert result.conflict is None


def test_weaker_newer_report_is_held_back_as_conflict():
    finve = _main("BAU", source=SourceType.FINVE, dt=date(2015, 1, 1), oid=1)
    vib = _main("VORPLANUNG", source=SourceType.VIB, dt=date(2025, 12, 31), oid=2)
    result = derive_headline([finve, vib], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.computed_phase is MainPhase.BAU
    assert [c.id for c in result.contributions if c.was_decisive] == [1]
    conflict = result.conflict
    assert conflict is not None
    assert conflict.applied is False
    assert conflict.observation_id == 2
    assert conflict.asserted_phase is MainPhase.VORPLANUNG
    assert conflict.contradicted_ids == [1]
    assert conflict.contradicted_phase is MainPhase.BAU
    assert all(c.in_conflict for c in result.contributions)


def test_weaker_newer_report_is_held_back_against_older_report():
    old = _main("IN_BETRIEB", source=SourceType.VIB, dt=date(2022, 12, 31), oid=1)
    media = _main("BAU", source=SourceType.MEDIEN, dt=date(2026, 5, 1), oid=2)
    result = derive_headline([old, media], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.computed_phase is MainPhase.IN_BETRIEB
    assert result.conflict is not None and result.conflict.applied is False


def test_trusted_newer_report_sets_back_and_reports_conflict():
    finve = _main("BAU", source=SourceType.FINVE, dt=date(2015, 1, 1), oid=1)
    infraplan = _main(
        "GENEHMIGUNGSPLANUNG", source=SourceType.INFRAPLAN, dt=date(2026, 1, 1), oid=2
    )
    result = derive_headline([finve, infraplan], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.computed_phase is MainPhase.GENEHMIGUNGSPLANUNG
    assert result.conflict is not None and result.conflict.applied is True


def test_manual_report_sets_back_without_conflict():
    finve = _main("BAU", source=SourceType.FINVE, dt=date(2015, 1, 1), oid=1)
    manual = _main("VORPLANUNG", source=SourceType.MANUELL, conf=0.5, oid=2)
    result = derive_headline([finve, manual], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.computed_phase is MainPhase.VORPLANUNG
    assert result.conflict is None


def test_manual_override_clears_conflict():
    finve = _main("BAU", source=SourceType.FINVE, dt=date(2015, 1, 1), oid=1)
    vib = _main("VORPLANUNG", source=SourceType.VIB, dt=date(2025, 12, 31), oid=2)
    result = derive_headline(
        [finve, vib],
        has_pf=False,
        parl_relevant=False,
        manual_phase_override=MainPhase.VORPLANUNG,
        today=TODAY,
    )
    assert result.conflict is None
    assert not any(c.in_conflict for c in result.contributions)


def test_lower_bound_does_not_age():
    # A FinVe from 2000 keeps its full trust: financing for a phase stays true
    # however old it is.
    finve = _main("BAU", source=SourceType.FINVE, dt=date(2000, 1, 1), oid=1)
    result = derive_headline([finve], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.computed_phase is MainPhase.BAU
    assert result.contributions[0].effective_confidence == pytest.approx(0.7)


def test_no_observations_means_not_started():
    result = derive_headline([], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.computed_phase is MainPhase.NICHT_GESTARTET
    assert result.computed_confidence == 0.0


def test_no_information_is_not_known():
    # No credible MAIN observation and no override → "Unbekannt", not started.
    result = derive_headline([], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.is_known is False


def test_credible_observation_is_known():
    result = derive_headline(
        [_main("VORPLANUNG", oid=1)], has_pf=False, parl_relevant=False, today=TODAY
    )
    assert result.is_known is True


def test_override_alone_is_known():
    result = derive_headline(
        [],
        has_pf=False,
        parl_relevant=False,
        manual_phase_override=MainPhase.NICHT_GESTARTET,
        today=TODAY,
    )
    # Explicitly asserting NICHT_GESTARTET is real information, unlike the fallback.
    assert result.is_known is True


def test_only_uncredible_observation_is_not_known():
    weak = _main("BAU", source=SourceType.MEDIEN, conf=0.02, oid=1)
    result = derive_headline([weak], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.is_known is False


def test_low_confidence_observation_is_ignored():
    # Media with an explicit tiny confidence stays below the threshold.
    weak = _main("IN_BETRIEB", source=SourceType.MEDIEN, conf=0.05, oid=1)
    strong = _main("VORPLANUNG", oid=2)
    result = derive_headline([weak, strong], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.computed_phase is MainPhase.VORPLANUNG
    assert all(not c.was_decisive for c in result.contributions if c.id == 1)


# --- Recency decay -----------------------------------------------------------


def test_recency_decay_monotonic_and_floored():
    from dashboard_backend.services.progress_derivation import RECENCY_FLOOR

    fresh = recency_decay(TODAY, TODAY)
    one_year = recency_decay(date(2025, 6, 18), TODAY)
    ancient = recency_decay(date(2000, 1, 1), TODAY)
    assert fresh == 1.0
    assert one_year == pytest.approx(0.5, abs=0.02)
    assert ancient == pytest.approx(RECENCY_FLOOR)  # floored
    assert fresh > one_year > ancient


def test_structured_source_keeps_lower_bound_when_old():
    # A multi-year-old VIB "in Betrieb" must still count as a credible lower
    # bound (progress does not un-happen).
    old_vib = _main("IN_BETRIEB", source=SourceType.VIB, dt=date(2019, 12, 31), oid=1)
    result = derive_headline([old_vib], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.computed_phase is MainPhase.IN_BETRIEB
    assert result.contributions[0].effective_confidence >= CREDIBILITY_THRESHOLD


def test_fresh_manual_wins_over_decayed_vib():
    old_vib = _main("BAU", source=SourceType.VIB, dt=date(2025, 8, 1), oid=1)
    fresh_manual = _main("GENEHMIGUNGSPLANUNG", dt=TODAY, oid=2)
    # Both reports fall into the same trust window; the manual one is trusted
    # more, so it decides the headline even though BAU is the higher phase.
    result = derive_headline([old_vib, fresh_manual], has_pf=False, parl_relevant=False, today=TODAY)
    vib_c = next(c for c in result.contributions if c.id == 1)
    man_c = next(c for c in result.contributions if c.id == 2)
    assert vib_c.trust < man_c.trust
    assert result.computed_phase is MainPhase.GENEHMIGUNGSPLANUNG
    assert man_c.was_decisive is True


def test_explicit_confidence_overrides_recency():
    obs = _main("BAU", source=SourceType.VIB, dt=date(2000, 1, 1), conf=0.95, oid=1)
    assert effective_confidence(obs, TODAY) == 0.95


def test_missing_date_uses_flat_penalty():
    no_date = recency_decay(None, TODAY)
    assert 0.0 < no_date < 1.0


# --- Lifecycle overlay -------------------------------------------------------


def test_lifecycle_is_overlay_only():
    result = derive_headline(
        [_main("BAU", oid=1)],
        has_pf=False,
        parl_relevant=False,
        lifecycle=LifecycleStatus.PAUSIERT,
        today=TODAY,
    )
    # Lifecycle does not alter the phase value.
    assert result.computed_phase is MainPhase.BAU
    assert result.lifecycle is LifecycleStatus.PAUSIERT


# --- Manual override ---------------------------------------------------------


def test_manual_override_wins_over_computed():
    result = derive_headline(
        [_main("BAU", oid=1)],
        has_pf=False,
        parl_relevant=False,
        manual_phase_override=MainPhase.VORPLANUNG,
        today=TODAY,
    )
    assert result.computed_phase is MainPhase.BAU  # computed unchanged
    assert result.effective_phase is MainPhase.VORPLANUNG  # override wins
    assert result.is_overridden is True


# --- Parallel tracks ---------------------------------------------------------


def test_parallel_tracks_only_when_active():
    pf_obs = ObservationInput(
        SourceType.MANUELL, ObservationTrack.PF, ParallelState.LAEUFT.value, TODAY, id=1
    )
    parl_obs = ObservationInput(
        SourceType.MANUELL, ObservationTrack.PARL, ParallelState.ABGESCHLOSSEN.value, TODAY, id=2
    )
    # PF active, PARL inactive.
    result = derive_headline(
        [_main("GENEHMIGUNGSPLANUNG", oid=3), pf_obs, parl_obs],
        has_pf=True,
        parl_relevant=False,
        today=TODAY,
    )
    assert result.pf_state is ParallelState.LAEUFT
    assert result.parl_state is None  # not relevant → not derived


def test_active_parallel_track_without_observation_defaults_offen():
    result = derive_headline(
        [_main("VORPLANUNG", oid=1)], has_pf=True, parl_relevant=True, today=TODAY
    )
    assert result.pf_state is ParallelState.OFFEN
    assert result.parl_state is ParallelState.OFFEN


def test_parallel_state_override_wins():
    pf_obs = ObservationInput(
        SourceType.MANUELL, ObservationTrack.PF, ParallelState.OFFEN.value, TODAY, id=1
    )
    result = derive_headline(
        [pf_obs],
        has_pf=True,
        parl_relevant=False,
        pf_state_override=ParallelState.ABGESCHLOSSEN,
        today=TODAY,
    )
    assert result.pf_state is ParallelState.ABGESCHLOSSEN


# --- Superior span -----------------------------------------------------------


def test_aggregate_span_min_max():
    span = aggregate_span([MainPhase.VORPLANUNG, MainPhase.BAU, MainPhase.GENEHMIGUNGSPLANUNG])
    assert span == (MainPhase.VORPLANUNG, MainPhase.BAU)


def test_aggregate_span_empty_is_none():
    assert aggregate_span([]) is None


def test_credibility_threshold_constant_sane():
    assert 0.0 < CREDIBILITY_THRESHOLD < 0.5


# --- Recursive subtree aggregation (arbitrary depth) -------------------------


def _leaf(phase: MainPhase, *, known: bool = True) -> AggregationNode:
    return AggregationNode(leaf_phase=phase, leaf_is_known=known)


def _superior(*children: AggregationNode, override: MainPhase | None = None) -> AggregationNode:
    return AggregationNode(
        leaf_phase=MainPhase.NICHT_GESTARTET,
        leaf_is_known=False,
        manual_override=override,
        children=list(children),
    )


def test_aggregate_tree_leaf_returns_own_phase():
    res = aggregate_tree(_leaf(MainPhase.BAU))
    assert res.is_superior is False
    assert res.span is None
    assert res.display_phase == MainPhase.BAU
    assert res.phases == [MainPhase.BAU]


def test_aggregate_tree_unknown_leaf_contributes_nothing():
    res = aggregate_tree(_leaf(MainPhase.NICHT_GESTARTET, known=False))
    assert res.is_known is False
    assert res.phases == []


def test_aggregate_tree_spans_direct_children():
    res = aggregate_tree(_superior(_leaf(MainPhase.VORPLANUNG), _leaf(MainPhase.BAU)))
    assert res.is_superior is True
    assert res.span == (MainPhase.VORPLANUNG, MainPhase.BAU)
    assert res.is_known is True


def test_aggregate_tree_spans_leaves_across_levels():
    """A level-1 superior must reflect diverging level-3 leaves, not a level-2 summary."""
    deep = _superior(
        _leaf(MainPhase.IN_BETRIEB),
        _superior(_leaf(MainPhase.VORPLANUNG), _leaf(MainPhase.GENEHMIGUNGSPLANUNG)),
    )
    res = aggregate_tree(deep)
    assert res.span == (MainPhase.VORPLANUNG, MainPhase.IN_BETRIEB)


def test_aggregate_tree_override_pins_subtree():
    """A manual override on an intermediate node ignores its diverging leaves."""
    node = _superior(
        _leaf(MainPhase.VORPLANUNG),
        _leaf(MainPhase.IN_BETRIEB),
        override=MainPhase.BAU,
    )
    res = aggregate_tree(node)
    assert res.span is None
    assert res.display_phase == MainPhase.BAU
    assert res.phases == [MainPhase.BAU]


def test_aggregate_tree_override_collapses_into_parent_span():
    """An override on a nested node contributes exactly its pinned phase upward."""
    res = aggregate_tree(
        _superior(
            _leaf(MainPhase.VORPLANUNG),
            _superior(_leaf(MainPhase.NICHT_GESTARTET), override=MainPhase.IN_BETRIEB),
        )
    )
    assert res.span == (MainPhase.VORPLANUNG, MainPhase.IN_BETRIEB)


def test_aggregate_tree_all_unknown_children_is_unknown():
    res = aggregate_tree(
        _superior(_leaf(MainPhase.NICHT_GESTARTET, known=False), _leaf(MainPhase.BAU, known=False))
    )
    assert res.is_known is False
    assert res.span is None


# --- stored_headline_phase (list views read the cached row) -------------------


@pytest.mark.parametrize(
    ("override", "computed", "confidence", "expected"),
    [
        ("BAU", "VORPLANUNG", 0.8, MainPhase.BAU),  # override wins
        ("BAU", None, None, MainPhase.BAU),  # override without any derivation
        (None, "VORPLANUNG", 0.8, MainPhase.VORPLANUNG),
        (None, "NICHT_GESTARTET", 0.5, MainPhase.NICHT_GESTARTET),  # credible "not started"
        (None, "NICHT_GESTARTET", 0.0, None),  # derivation fallback = unknown
        (None, None, None, None),  # never derived
        (None, "KAPUTT", 0.9, None),  # invalid stored value
        ("KAPUTT", "BAU", 0.9, MainPhase.BAU),  # invalid override is ignored
    ],
)
def test_stored_headline_phase(override, computed, confidence, expected):
    assert stored_headline_phase(override, computed, confidence) is expected


def test_stored_headline_phase_matches_derivation_for_unknown():
    result = derive_headline(
        [],
        has_pf=False,
        parl_relevant=False,
        lifecycle=LifecycleStatus.AKTIV,
        today=TODAY,
    )
    assert result.is_known is False
    assert (
        stored_headline_phase(None, result.computed_phase.value, result.computed_confidence)
        is None
    )
