"""Pure multi-project timeline (no DB): dated milestones for one project row.

Feeds the "Zeitstrahl" view (docs/features/feature-project-timeline.md). Two
kinds of dates are produced:

- **Concrete** milestones — phase starts from VIB-PFA dates, Fulda-Runde
  announcements and manual expected entries (same precedence as the forecast,
  via :func:`concrete_milestone_dates`), plus the Planfeststellung and the
  parliamentary involvement dates. Only these make a project *credible* enough
  to appear on the timeline. BVWP duration estimates are never used.
- **Evidence** points — for a phase without a concrete date, the earliest date
  of a credible, non-expected MAIN observation ("spätestens seit"). Evidence
  that contradicts the phase order (a higher phase is dated earlier) is dropped.

For a superior, the pooled row has one BAU start (earliest) and one opening
(latest). When the subprojects build in separate stages, the row additionally
carries the **construction periods** — the union of each member's own
Baubeginn–Inbetriebnahme interval — so the bar does not paint the gap between
stages as construction (:func:`construction_periods`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from dashboard_backend.models.projects.progress_enums import (
    MainPhase,
    ObservationTrack,
    SourceType,
)
from dashboard_backend.services.progress_derivation import (
    CREDIBILITY_THRESHOLD,
    ObservationInput,
    effective_confidence,
)
from dashboard_backend.services.progress_forecast import (
    PfaForecastInput,
    concrete_milestone_dates,
)

KIND_PHASE = "PHASE"
KIND_PFB = "PFB"
KIND_PARL = "PARL"

CERTAINTY_CONCRETE = "CONCRETE"
CERTAINTY_EVIDENCE = "EVIDENCE"

# Phases that have a start on the timeline (NICHT_GESTARTET has no start event).
_TIMELINE_PHASES = (
    MainPhase.VORPLANUNG,
    MainPhase.GENEHMIGUNGSPLANUNG,
    MainPhase.BAU,
    MainPhase.IN_BETRIEB,
)

_SOURCE_LABEL: dict[SourceType, str] = {
    SourceType.VIB: "VIB",
    SourceType.FINVE: "FinVe",
    SourceType.FULDA_RUNDE: "Fulda-Runde",
    SourceType.BAUPORTAL: "Bauportal",
    SourceType.MEDIEN: "Medien",
    SourceType.MANUELL: "Manuell",
}


@dataclass(frozen=True)
class TimelineMilestone:
    kind: str  # KIND_PHASE | KIND_PFB | KIND_PARL
    date: date
    source: str
    certainty: str  # CERTAINTY_CONCRETE | CERTAINTY_EVIDENCE
    phase: MainPhase | None = None  # set for KIND_PHASE


@dataclass(frozen=True)
class ConstructionUnitInput:
    """Concrete date inputs of one member of a pooled row (the superior itself
    or one project of its subtree), read with its own PFAs only."""

    pfas: list[PfaForecastInput] = field(default_factory=list)
    fulda: list[tuple[MainPhase, date]] = field(default_factory=list)
    manual_expected: list[tuple[MainPhase, date]] = field(default_factory=list)


@dataclass
class TimelineResult:
    milestones: list[TimelineMilestone] = field(default_factory=list)
    # True when at least one concrete milestone exists (evidence alone is not enough).
    has_credible_dates: bool = False
    # Disjoint construction periods (start, end), only when there are at least
    # two — a single period is the plain BAU segment and needs no extra data.
    construction_periods: list[tuple[date, date]] = field(default_factory=list)


def _reduce_per_phase(pairs: list[tuple[MainPhase, date]]) -> list[tuple[MainPhase, date]]:
    """One date per phase: earliest start, but the latest in-service date.

    Several entries per phase arise when a superior pools its subtree (each
    section has its own dates) — same aggregation as the PFA sections.
    """

    best: dict[MainPhase, date] = {}
    for phase, dt in pairs:
        current = best.get(phase)
        if current is None:
            best[phase] = dt
        elif phase is MainPhase.IN_BETRIEB:
            best[phase] = max(current, dt)
        else:
            best[phase] = min(current, dt)
    return list(best.items())


def construction_periods(units: list[ConstructionUnitInput]) -> list[tuple[date, date]]:
    """Union of the members' Baubeginn–Inbetriebnahme intervals.

    Overlapping or touching intervals merge into one period. The result is
    only returned when it has a real gap (two or more periods); otherwise the
    plain BAU segment of the row is already right. Conservative on incomplete
    data, since a gap must never be invented:

    - a member with a construction start but no opening (open end) or with
      contradicting dates (opening not after the start) cancels the split;
    - a member with only an opening date cancels it too, unless that opening
      lies before the first construction start (an older, finished stage).
    """

    intervals: list[tuple[date, date]] = []
    openings_only: list[date] = []
    for unit in units:
        concrete = concrete_milestone_dates(
            pfas=unit.pfas,
            fulda=_reduce_per_phase(unit.fulda),
            manual_expected=_reduce_per_phase(unit.manual_expected),
            pfb_as_genehmigung=False,
        )
        start = concrete.get(MainPhase.BAU, (None, ""))[0]
        end = concrete.get(MainPhase.IN_BETRIEB, (None, ""))[0]
        if start is None and end is None:
            continue
        if start is None:
            openings_only.append(end)
            continue
        if end is None or end <= start:
            return []
        intervals.append((start, end))

    if not intervals:
        return []
    intervals.sort()
    if any(opening > intervals[0][0] for opening in openings_only):
        return []

    merged: list[tuple[date, date]] = [intervals[0]]
    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged if len(merged) >= 2 else []


def _evidence_dates(
    observations: list[ObservationInput], today: date
) -> dict[MainPhase, tuple[date, str]]:
    """Earliest dated credible MAIN observation per phase (past dates only)."""

    evidence: dict[MainPhase, tuple[date, str]] = {}
    for obs in observations:
        if obs.track is not ObservationTrack.MAIN or obs.observed_date is None:
            continue
        if obs.observed_date > today:
            continue  # a future "observation" is a plan, not evidence
        if effective_confidence(obs, today) < CREDIBILITY_THRESHOLD:
            continue
        try:
            phase = MainPhase(obs.asserted_state)
        except ValueError:
            continue
        if phase not in _TIMELINE_PHASES:
            continue
        current = evidence.get(phase)
        if current is None or obs.observed_date < current[0]:
            evidence[phase] = (obs.observed_date, _SOURCE_LABEL.get(obs.source_type, obs.source_type.value))
    return evidence


def build_timeline(
    *,
    today: date,
    pfas: list[PfaForecastInput] | None = None,
    fulda: list[tuple[MainPhase, date]] | None = None,
    manual_expected: list[tuple[MainPhase, date]] | None = None,
    observations: list[ObservationInput] | None = None,
    pf_dates: list[date] | None = None,
    parl_dates: list[date] | None = None,
    construction_units: list[ConstructionUnitInput] | None = None,
) -> TimelineResult:
    """Assemble the dated milestones of one timeline row.

    ``observations`` are the non-expected observations used for evidence;
    ``pf_dates`` / ``parl_dates`` are editorial dates (several when a superior
    pools its subtree — the earliest wins). ``construction_units`` are the
    per-member inputs of a pooled row (see :func:`construction_periods`).
    """

    pfas = pfas or []
    concrete = concrete_milestone_dates(
        pfas=pfas,
        fulda=_reduce_per_phase(fulda or []),
        manual_expected=_reduce_per_phase(manual_expected or []),
        pfb_as_genehmigung=False,
    )

    milestones: list[TimelineMilestone] = [
        TimelineMilestone(
            kind=KIND_PHASE, date=dt, source=source, certainty=CERTAINTY_CONCRETE, phase=phase
        )
        for phase, (dt, source) in concrete.items()
        if phase in _TIMELINE_PHASES
    ]

    # Evidence fills phases without a concrete date, unless a higher phase is
    # dated earlier (the observation date then can't be the phase's start).
    evidence = _evidence_dates(observations or [], today)
    dated = {phase: dt for phase, (dt, _) in concrete.items()}
    dated.update({phase: dt for phase, (dt, _) in evidence.items() if phase not in dated})
    for phase, (dt, source) in evidence.items():
        if phase in concrete:
            continue
        contradicted = any(
            other.order > phase.order and other_dt < dt for other, other_dt in dated.items()
        )
        if contradicted:
            continue
        milestones.append(
            TimelineMilestone(
                kind=KIND_PHASE, date=dt, source=source, certainty=CERTAINTY_EVIDENCE, phase=phase
            )
        )

    # Planfeststellung: the editorial date wins over the PFA decision dates.
    if pf_dates:
        milestones.append(
            TimelineMilestone(
                kind=KIND_PFB, date=min(pf_dates), source="Manuell", certainty=CERTAINTY_CONCRETE
            )
        )
    else:
        pfb_dates = [p.datum_pfb for p in pfas if p.datum_pfb]
        if pfb_dates:
            milestones.append(
                TimelineMilestone(
                    kind=KIND_PFB, date=min(pfb_dates), source="VIB-PFA", certainty=CERTAINTY_CONCRETE
                )
            )

    if parl_dates:
        milestones.append(
            TimelineMilestone(
                kind=KIND_PARL, date=min(parl_dates), source="Manuell", certainty=CERTAINTY_CONCRETE
            )
        )

    milestones.sort(key=lambda m: (m.date, m.phase.order if m.phase else -1))
    return TimelineResult(
        milestones=milestones,
        has_credible_dates=any(m.certainty == CERTAINTY_CONCRETE for m in milestones),
        construction_periods=(
            construction_periods(construction_units)
            if construction_units and len(construction_units) >= 2
            else []
        ),
    )
