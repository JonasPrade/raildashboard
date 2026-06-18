"""Pure planning-state derivation logic (no DB session, fully unit-testable).

The derivation is a **hybrid**: most sources assert a monotone *lower bound*
on the main phase, so the computed headline is the ``max`` over the credible
lower bounds. The computed value is only a *suggestion* — a manual override
(passed in) always wins. Conflicts are never silently resolved away; every
input observation is echoed back as a :class:`SourceContribution` so the API /
frontend can show the full breakdown.

Phase 1 feeds this only with **manual** observations. Phase 2 will materialise
VIB/FinVe observations (``is_derived=True``) and hand them in here unchanged —
no logic change required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from dashboard_backend.models.projects.progress_enums import (
    LifecycleStatus,
    MainPhase,
    ObservationTrack,
    ParallelState,
    SourceType,
)

# --- Tuning constants --------------------------------------------------------

# Default trust per source type, applied when an observation carries no explicit
# per-observation confidence. Editorial manual input ranks highest; media lowest.
SOURCE_TYPE_DEFAULT_TRUST: dict[SourceType, float] = {
    SourceType.MANUELL: 0.9,
    SourceType.BAUPORTAL: 0.8,
    SourceType.FINVE: 0.7,
    SourceType.FULDA_RUNDE: 0.7,
    SourceType.VIB: 0.6,
    SourceType.MEDIEN: 0.4,
}

# Half-life (days) of an observation's recency weight. After this many days the
# recency multiplier has halved — this is what makes the "always outdated" VIB
# fade against fresher sources.
RECENCY_HALF_LIFE_DAYS = 365
# Recency multiplier never drops below this floor. Chosen so that a structured
# source (VIB 0.6, FinVe 0.7) keeps its monotone lower bound regardless of age
# (0.6 × 0.3 = 0.18 ≥ CREDIBILITY_THRESHOLD) — progress doesn't un-happen, so an
# old "in Betrieb" must not be dropped — while fully-decayed low-trust media
# (0.4 × 0.3 = 0.12) can still fall below the threshold.
RECENCY_FLOOR = 0.3
# Recency multiplier for observations without a parseable date.
NO_DATE_RECENCY = 0.6

# An observation must reach this effective confidence to count towards the
# lower-bound max (keeps low-trust noise from lifting the headline).
CREDIBILITY_THRESHOLD = 0.15

# Lazy-resync staleness window (Phase 2): cached ``computed_at`` older than this
# triggers a re-materialisation of derived observations on GET. Defined now so
# Phase 2 only has to consume it.
STALENESS_WINDOW = timedelta(hours=24)


# --- Inputs / outputs --------------------------------------------------------


@dataclass(frozen=True)
class ObservationInput:
    """DB-free view of a single observation, as fed to the derivation."""

    source_type: SourceType
    track: ObservationTrack
    asserted_state: str  # MainPhase value for MAIN, ParallelState value for PF/PARL
    observed_date: date | None = None
    confidence: float | None = None  # explicit per-observation override
    note: str | None = None
    id: int | None = None  # carried through for the breakdown / UI


@dataclass
class SourceContribution:
    """One input observation, annotated with its effective weight and role."""

    id: int | None
    source_type: SourceType
    track: ObservationTrack
    asserted_state: str
    observed_date: date | None
    effective_confidence: float
    was_decisive: bool


@dataclass
class DerivationResult:
    computed_phase: MainPhase
    computed_confidence: float
    effective_phase: MainPhase  # manual override wins over computed
    is_overridden: bool
    lifecycle: LifecycleStatus
    pf_state: ParallelState | None
    parl_state: ParallelState | None
    # False when nothing tells us the main phase (no credible MAIN observation
    # and no manual override). The frontend renders this as "Unbekannt" rather
    # than the NICHT_GESTARTET fallback — "we don't know" ≠ "not started".
    is_known: bool = False
    contributions: list[SourceContribution] = field(default_factory=list)


# --- Helpers -----------------------------------------------------------------


def recency_decay(observed_date: date | None, today: date) -> float:
    """Return a recency multiplier in ``[RECENCY_FLOOR, 1.0]``.

    Fresh observations weigh ~1.0; the weight halves every
    ``RECENCY_HALF_LIFE_DAYS``. Missing/unparseable dates get a flat moderate
    penalty (``NO_DATE_RECENCY``). Future dates are treated as fresh.
    """

    if observed_date is None:
        return NO_DATE_RECENCY
    age_days = (today - observed_date).days
    if age_days <= 0:
        return 1.0
    decay = 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)
    return max(RECENCY_FLOOR, decay)


def effective_confidence(obs: ObservationInput, today: date) -> float:
    """Effective confidence = explicit override, else default trust × recency."""

    if obs.confidence is not None:
        return obs.confidence
    base = SOURCE_TYPE_DEFAULT_TRUST.get(obs.source_type, 0.5)
    return base * recency_decay(obs.observed_date, today)


def _safe_main_phase(value: str) -> MainPhase | None:
    try:
        return MainPhase(value)
    except ValueError:
        return None


def _safe_parallel_state(value: str) -> ParallelState | None:
    try:
        return ParallelState(value)
    except ValueError:
        return None


def _derive_parallel(
    observations: list[ObservationInput],
    track: ObservationTrack,
    today: date,
) -> ParallelState:
    """Lower-bound max over credible observations on a parallel track.

    An active track with no credible observation defaults to ``OFFEN``.
    """

    best = ParallelState.OFFEN
    for obs in observations:
        if obs.track is not track:
            continue
        if effective_confidence(obs, today) < CREDIBILITY_THRESHOLD:
            continue
        state = _safe_parallel_state(obs.asserted_state)
        if state is not None and state.order > best.order:
            best = state
    return best


# --- Main entry point --------------------------------------------------------


def derive_headline(
    observations: list[ObservationInput],
    *,
    has_pf: bool,
    parl_relevant: bool,
    lifecycle: LifecycleStatus = LifecycleStatus.AKTIV,
    manual_phase_override: MainPhase | None = None,
    pf_state_override: ParallelState | None = None,
    parl_state_override: ParallelState | None = None,
    today: date,
) -> DerivationResult:
    """Derive the headline phase + parallel states from observations.

    ``has_pf`` / ``parl_relevant`` gate whether the PF / parliamentary tracks
    are derived at all. Manual overrides win over the computed values. The
    lifecycle is returned as an overlay flag and never changes the phase value.
    """

    # --- Main phase: max over credible MAIN lower bounds ---------------------
    computed_phase = MainPhase.NICHT_GESTARTET
    computed_confidence = 0.0
    decisive_ids: set[int] = set()

    contributions: list[SourceContribution] = []
    for obs in observations:
        eff = effective_confidence(obs, today)
        contributions.append(
            SourceContribution(
                id=obs.id,
                source_type=obs.source_type,
                track=obs.track,
                asserted_state=obs.asserted_state,
                observed_date=obs.observed_date,
                effective_confidence=round(eff, 4),
                was_decisive=False,
            )
        )

    credible_main = [
        (obs, contrib)
        for obs, contrib in zip(observations, contributions)
        if obs.track is ObservationTrack.MAIN
        and contrib.effective_confidence >= CREDIBILITY_THRESHOLD
        and _safe_main_phase(obs.asserted_state) is not None
    ]

    if credible_main:
        max_order = max(
            _safe_main_phase(obs.asserted_state).order for obs, _ in credible_main  # type: ignore[union-attr]
        )
        computed_phase = next(
            phase for phase in MainPhase if phase.order == max_order
        )
        # Confidence = strongest observation that reaches the headline phase.
        deciding = [
            (obs, contrib)
            for obs, contrib in credible_main
            if _safe_main_phase(obs.asserted_state).order == max_order  # type: ignore[union-attr]
        ]
        computed_confidence = round(
            max(contrib.effective_confidence for _, contrib in deciding), 4
        )
        for obs, contrib in deciding:
            contrib.was_decisive = True
            if obs.id is not None:
                decisive_ids.add(obs.id)

    # --- Parallel tracks (only when active) ----------------------------------
    pf_state: ParallelState | None = None
    if has_pf:
        pf_state = pf_state_override or _derive_parallel(
            observations, ObservationTrack.PF, today
        )

    parl_state: ParallelState | None = None
    if parl_relevant:
        parl_state = parl_state_override or _derive_parallel(
            observations, ObservationTrack.PARL, today
        )

    effective_phase = manual_phase_override or computed_phase
    is_known = bool(credible_main) or manual_phase_override is not None

    return DerivationResult(
        computed_phase=computed_phase,
        computed_confidence=computed_confidence,
        effective_phase=effective_phase,
        is_overridden=manual_phase_override is not None,
        lifecycle=lifecycle,
        pf_state=pf_state,
        parl_state=parl_state,
        is_known=is_known,
        contributions=contributions,
    )


def aggregate_span(phases: list[MainPhase]) -> tuple[MainPhase, MainPhase] | None:
    """Min/max span over child leaf phases for a superior project.

    Returns ``None`` when there are no children (caller treats the superior as
    its own leaf).
    """

    if not phases:
        return None
    lo = min(phases, key=lambda p: p.order)
    hi = max(phases, key=lambda p: p.order)
    return lo, hi
