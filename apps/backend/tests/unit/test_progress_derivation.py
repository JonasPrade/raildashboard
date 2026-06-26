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


# --- Headline: highest confidence wins ---------------------------------------


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
    # confidence; a FinVe-derived BAU sits at a low (decayed) confidence. The
    # manual statement must win even though BAU is the higher phase.
    manual = _main("GENEHMIGUNGSPLANUNG", source=SourceType.MANUELL, conf=1.0, oid=97)
    finve = _main("BAU", source=SourceType.FINVE, dt=date(2023, 1, 1), oid=98)
    result = derive_headline([manual, finve], has_pf=False, parl_relevant=False, today=TODAY)
    assert result.computed_phase is MainPhase.GENEHMIGUNGSPLANUNG
    assert result.computed_confidence == 1.0
    decisive = [c.id for c in result.contributions if c.was_decisive]
    assert decisive == [97]


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
    # The fresh manual observation has far higher effective confidence than the
    # decayed VIB, so it decides the headline — even though BAU is the higher
    # phase. (Confidence wins over phase order.)
    result = derive_headline([old_vib, fresh_manual], has_pf=False, parl_relevant=False, today=TODAY)
    vib_c = next(c for c in result.contributions if c.id == 1)
    man_c = next(c for c in result.contributions if c.id == 2)
    assert vib_c.effective_confidence < man_c.effective_confidence
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
