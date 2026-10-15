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
    SourceType.INFRAPLAN: "Infraplan",
    SourceType.MANUELL: "Manuell",
}


@dataclass(frozen=True)
class TimelineMilestone:
    kind: str  # KIND_PHASE | KIND_PFB | KIND_PARL
    date: date
    source: str
    certainty: str  # CERTAINTY_CONCRETE | CERTAINTY_EVIDENCE
    phase: MainPhase | None = None  # set for KIND_PHASE


@dataclass
class TimelineResult:
    milestones: list[TimelineMilestone] = field(default_factory=list)
    # True when at least one concrete milestone exists (evidence alone is not enough).
    has_credible_dates: bool = False


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
) -> TimelineResult:
    """Assemble the dated milestones of one timeline row.

    ``observations`` are the non-expected observations used for evidence;
    ``pf_dates`` / ``parl_dates`` are editorial dates (several when a superior
    pools its subtree — the earliest wins).
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
    )
