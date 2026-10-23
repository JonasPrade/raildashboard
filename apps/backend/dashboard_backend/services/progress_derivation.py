"""Pure planning-state derivation logic (no DB session, fully unit-testable).

Observations come in two kinds (decided 2026-10-22):

* **Lower bounds** (:data:`LOWER_BOUND_SOURCES`, today the FinVe) say "the
  project has reached *at least* this phase" — a Finanzierungsvereinbarung for
  Bau stays true however old it is. They only ever *raise* the headline; they
  never compete with a status report that says the project is further along.
* **Status reports** (VIB, Infraplan, GVFG, Bauportal, Fulda-Runde, Medien, manual)
  describe the state at their date. The **newest** report wins; only within
  :data:`TRUST_WINDOW` before the newest report does **trust** decide instead
  of recency (ties → higher phase). Trust is the explicit per-observation
  confidence, else the source-type default — without recency decay.

A status report that asserts a *lower* phase than older information (a lower
bound or an older report) would set the project back. It only does so when its
trust is at least that of every contradicting observation, or when it is a
manual entry; otherwise the higher phase is kept. Either way (except manual
entries, which are editorial decisions) the derivation reports a
:class:`PhaseConflict` that the admin area collects for review.

The computed value is only a *suggestion* — a manual override (passed in)
always wins for the effective phase. Every input observation is echoed back as
a :class:`SourceContribution` so the API / frontend can show the full
breakdown.
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
    # Bedarfsplan/InvKG rows; GVFG rows carry an explicit 0.75 (Länderangaben).
    SourceType.INFRAPLAN: 0.85,
    # GVFG-Bundesprogramm: Länderangaben, like the GVFG rows of the Infraplan.
    SourceType.GVFG: 0.75,
    SourceType.BAUPORTAL: 0.8,
    SourceType.FINVE: 0.7,
    # Fulda-Runde: a working-level preview, a little below the reports.
    SourceType.FULDA_RUNDE: 0.55,
    SourceType.VIB: 0.6,
    SourceType.MEDIEN: 0.4,
}

# Sources whose observations are lower bounds ("at least this phase") rather
# than status reports. They raise the headline but never decide against a
# report that sees the project further along, and they do not age.
LOWER_BOUND_SOURCES: frozenset[SourceType] = frozenset({SourceType.FINVE})

# Within this window before the newest status report, trust decides instead of
# recency (reports of the same cycle compete on trust).
TRUST_WINDOW = timedelta(days=365)

# Half-life (days) of an observation's recency weight. Recency no longer ranks
# observations (the date order does); it only lets old, low-trust status
# reports drop below ``CREDIBILITY_THRESHOLD``. Also used by the forecast.
RECENCY_HALF_LIFE_DAYS = 365
# Recency multiplier never drops below this floor, so a structured report
# (VIB 0.6 × 0.3 = 0.18 ≥ 0.15) stays credible however old it is, while
# fully-decayed media (0.4 × 0.3 = 0.12) falls below the threshold.
RECENCY_FLOOR = 0.3
# Recency multiplier for observations without a parseable date.
NO_DATE_RECENCY = 0.6

# An observation must reach this effective confidence to be considered at all
# (keeps low-trust noise from deciding the headline).
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
    # DatePrecision value of ``observed_date`` (display only; the derivation
    # uses the date as its sort value).
    date_precision: str = "EXACT"


@dataclass
class SourceContribution:
    """One input observation, annotated with its weight and role."""

    id: int | None
    source_type: SourceType
    track: ObservationTrack
    asserted_state: str
    observed_date: date | None
    # Trust × recency (lower bounds: trust only); decides credibility only.
    effective_confidence: float
    was_decisive: bool
    # Trust without recency: explicit confidence, else the source default.
    trust: float = 0.0
    is_lower_bound: bool = False
    # True for both sides of a reported PhaseConflict.
    in_conflict: bool = False
    date_precision: str = "EXACT"  # display only (DatePrecision value)


@dataclass
class PhaseConflict:
    """A newer status report asserts a lower phase than older information.

    ``applied`` tells whether the report set the headline back (its trust is at
    least that of every contradicting observation) or was held back.
    """

    observation_id: int | None
    source_type: SourceType
    asserted_phase: MainPhase
    observed_date: date | None
    trust: float
    # Older observations (lower bounds or reports) asserting a higher phase.
    contradicted_ids: list[int | None]
    contradicted_phase: MainPhase  # highest phase among them
    applied: bool
    date_precision: str = "EXACT"  # display only (DatePrecision value)


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
    conflict: PhaseConflict | None = None


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


def is_lower_bound(obs: ObservationInput) -> bool:
    return obs.source_type in LOWER_BOUND_SOURCES


def trust(obs: ObservationInput) -> float:
    """Trust without recency: explicit confidence, else the source default."""

    if obs.confidence is not None:
        return obs.confidence
    return SOURCE_TYPE_DEFAULT_TRUST.get(obs.source_type, 0.5)


def effective_confidence(obs: ObservationInput, today: date) -> float:
    """Credibility weight: explicit override, else trust × recency.

    Lower bounds do not age (a FinVe for Bau stays true), so they keep their
    trust.
    """

    if obs.confidence is not None:
        return obs.confidence
    if is_lower_bound(obs):
        return trust(obs)
    return trust(obs) * recency_decay(obs.observed_date, today)


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


@dataclass
class _Main:
    """A credible MAIN observation with its parsed phase."""

    obs: ObservationInput
    contrib: SourceContribution
    phase: MainPhase


def _sort_date(item: _Main) -> date:
    # Undated reports count as the oldest.
    return item.obs.observed_date or date.min


def _strongest(items: list[_Main]) -> list[_Main]:
    """Items with the highest trust, then the highest phase among those."""

    top_trust = max(i.contrib.trust for i in items)
    top = [i for i in items if i.contrib.trust == top_trust]
    top_order = max(i.phase.order for i in top)
    return [i for i in top if i.phase.order == top_order]


def _decide_main(
    credible: list[_Main],
) -> tuple[list[_Main], PhaseConflict | None]:
    """Pick the decisive MAIN observation(s); report a set-back as a conflict."""

    bounds = [i for i in credible if i.contrib.is_lower_bound]
    reports = [i for i in credible if not i.contrib.is_lower_bound]

    if not reports:
        # Only lower bounds: the highest bound holds.
        top_order = max(i.phase.order for i in bounds)
        return _strongest([i for i in bounds if i.phase.order == top_order]), None

    # Status: newest report; within the trust window trust decides.
    anchor = max(_sort_date(i) for i in reports)
    window_start = anchor - TRUST_WINDOW if anchor - date.min > TRUST_WINDOW else date.min
    in_window = [i for i in reports if _sort_date(i) >= window_start]
    status = _strongest(in_window)
    current = max(status, key=_sort_date)

    # Older information that sees the project further along.
    higher = [
        i
        for i in bounds + [r for r in reports if _sort_date(r) < window_start]
        if i.phase.order > current.phase.order
    ]
    if not higher or current.obs.source_type is SourceType.MANUELL:
        return status, None

    blockers = [i for i in higher if i.contrib.trust > current.contrib.trust]
    conflict = PhaseConflict(
        observation_id=current.obs.id,
        source_type=current.obs.source_type,
        asserted_phase=current.phase,
        observed_date=current.obs.observed_date,
        trust=current.contrib.trust,
        contradicted_ids=[i.obs.id for i in higher],
        contradicted_phase=max((i.phase for i in higher), key=lambda p: p.order),
        applied=not blockers,
        date_precision=current.obs.date_precision,
    )
    current.contrib.in_conflict = True
    for i in higher:
        i.contrib.in_conflict = True
    if not blockers:
        return status, conflict
    # Held back: the highest phase among the more trusted older observations.
    top_order = max(i.phase.order for i in blockers)
    return _strongest([i for i in blockers if i.phase.order == top_order]), conflict


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

    computed_phase = MainPhase.NICHT_GESTARTET
    computed_confidence = 0.0
    conflict: PhaseConflict | None = None

    contributions: list[SourceContribution] = []
    for obs in observations:
        contributions.append(
            SourceContribution(
                id=obs.id,
                source_type=obs.source_type,
                track=obs.track,
                asserted_state=obs.asserted_state,
                observed_date=obs.observed_date,
                effective_confidence=round(effective_confidence(obs, today), 4),
                was_decisive=False,
                trust=round(trust(obs), 4),
                is_lower_bound=is_lower_bound(obs),
                date_precision=obs.date_precision,
            )
        )

    credible_main = [
        _Main(obs, contrib, phase)
        for obs, contrib in zip(observations, contributions)
        if obs.track is ObservationTrack.MAIN
        and contrib.effective_confidence >= CREDIBILITY_THRESHOLD
        and (phase := _safe_main_phase(obs.asserted_state)) is not None
    ]

    if credible_main:
        decisive, conflict = _decide_main(credible_main)
        computed_phase = decisive[0].phase
        computed_confidence = decisive[0].contrib.trust
        for item in decisive:
            item.contrib.was_decisive = True

    # A manual override is an editorial decision on the phase: nothing left to
    # review, so no conflict is reported.
    if manual_phase_override is not None:
        conflict = None
        for c in contributions:
            c.in_conflict = False

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
        conflict=conflict,
    )


def stored_headline_phase(
    manual_phase_override: str | None,
    computed_phase: str | None,
    computed_confidence: float | None,
) -> MainPhase | None:
    """Headline phase from the *cached* ``project_progress`` columns, or None.

    Used by list views, which must not run the derivation (or the lazy resync)
    per project. Mirrors ``derive_headline``: the manual override wins; else the
    cached ``computed_phase`` counts only when a credible MAIN observation
    decided it. ``derive_headline`` stores ``NICHT_GESTARTET`` with confidence
    ``0.0`` as a fallback when nothing is known — that is reported as ``None``
    ("unknown", matching ``is_known=False``) rather than as "not started".
    Values that are not a valid ``MainPhase`` are treated as unknown.
    """

    override = _safe_main_phase(manual_phase_override) if manual_phase_override else None
    if override is not None:
        return override
    if not computed_phase or not computed_confidence or computed_confidence <= 0:
        return None
    return _safe_main_phase(computed_phase)


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


# --- Recursive subtree aggregation (arbitrary nesting depth) -----------------


@dataclass
class AggregationNode:
    """One project in a superior/subproject tree, ready for recursive aggregation.

    The planning state lives at the **leaves**: a node *without* children carries
    its own derived phase (``leaf_phase`` + ``leaf_is_known``). An *intermediate*
    node (one *with* children) ignores its own observations and instead spans its
    descendant leaves — **except** a manual phase override, which pins the whole
    subtree to a single phase ("the editor says this entire section is in Bau").

    The identity fields are ignored by the algorithm; callers populate them so a
    payload for the direct children can be built from the aggregated tree.
    """

    leaf_phase: MainPhase
    leaf_is_known: bool
    manual_override: MainPhase | None = None
    children: list["AggregationNode"] = field(default_factory=list)
    project_id: int | None = None
    name: str | None = None
    lifecycle: LifecycleStatus | None = None


@dataclass
class AggregationResult:
    # All known leaf phases under this node (or the single pinned override phase).
    phases: list[MainPhase]
    is_known: bool
    is_superior: bool
    # min..max over ``phases`` for an aggregating intermediate node; ``None`` for
    # leaves and for an override-pinned node (which show ``display_phase`` instead).
    span: tuple[MainPhase, MainPhase] | None
    # A single representative phase: the leaf's own phase, the pinned override, or
    # the span's upper bound for an aggregating node (a sensible scalar fallback).
    display_phase: MainPhase


def aggregate_tree(node: AggregationNode) -> AggregationResult:
    """Recursively aggregate a subtree of arbitrary depth.

    Leaves contribute their own phase; intermediate nodes span the union of all
    leaves below them, so a level-1 superior reflects diverging level-3 leaves —
    not a level-2 node's stale summary. A manual override on an intermediate node
    short-circuits the recursion and pins the whole subtree to that phase.
    """

    if not node.children:
        phases = [node.leaf_phase] if node.leaf_is_known else []
        return AggregationResult(
            phases=phases,
            is_known=node.leaf_is_known,
            is_superior=False,
            span=None,
            display_phase=node.leaf_phase,
        )

    if node.manual_override is not None:
        return AggregationResult(
            phases=[node.manual_override],
            is_known=True,
            is_superior=True,
            span=None,
            display_phase=node.manual_override,
        )

    phases: list[MainPhase] = []
    for child in node.children:
        # A replaced subproject (and its subtree) no longer counts: its successor
        # carries the scheme (docs/features/feature-project-replacement.md, W3).
        if child.lifecycle is LifecycleStatus.ERSETZT:
            continue
        phases.extend(aggregate_tree(child).phases)
    span = aggregate_span(phases)
    display = span[1] if span is not None else MainPhase.NICHT_GESTARTET
    return AggregationResult(
        phases=phases,
        is_known=bool(phases),
        is_superior=True,
        span=span,
        display_phase=display,
    )
