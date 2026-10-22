"""Pure planning-state forecast (no DB).

Combines three input kinds into a "remaining duration + next steps" forecast:
- **Concrete milestone dates** from VIB PFA fields (``baubeginn`` → BAU start,
  ``inbetriebnahme`` → IN_BETRIEB, ``datum_pfb`` → Genehmigung/PF done), from
  Fulda-Runde prognoses and from the planned commissioning year of the
  Infraplan (derived expected observations carrying a phase + date). When
  several name a date for the same phase, the more credible × more recent
  report wins (trust of the source × recency of the report it comes from).
- **BVWP planning/build durations** (years) as a fallback when no concrete date
  exists for an upcoming phase.

Concrete dates always win over BVWP estimates. Phases a project's groups skip
(``skipped_phases``, e.g. Vorplanung/Genehmigungsplanung for corridor renewals
without Planfeststellung) are left out of the next steps unless a concrete date
exists for them — data wins over the group default. The function is deterministic in
``today`` (passed in) so it stays unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from dashboard_backend.models.projects.progress_enums import MainPhase, SourceType
from dashboard_backend.services.progress_derivation import (
    SOURCE_TYPE_DEFAULT_TRUST,
    recency_decay,
)

# Phases that are forecast targets (everything after NICHT_GESTARTET).
_FORECASTABLE = [
    MainPhase.VORPLANUNG,
    MainPhase.GENEHMIGUNGSPLANUNG,
    MainPhase.BAU,
    MainPhase.IN_BETRIEB,
]


@dataclass(frozen=True)
class PfaForecastInput:
    """Already-parsed PFA milestone dates (parsing happens in the CRUD layer)."""

    datum_pfb: date | None = None
    baubeginn: date | None = None
    inbetriebnahme: date | None = None
    # Date of the VIB report the section comes from (recency of its dates).
    reported_on: date | None = None


@dataclass(frozen=True)
class ExpectedDate:
    """A dated prognosis for a phase plus the date of the report stating it."""

    phase: MainPhase
    date: date
    reported_on: date | None = None


@dataclass(frozen=True)
class BvwpDurations:
    outstanding_planning: float | None = None  # years until construction
    build: float | None = None  # years of construction
    operating: float | None = None  # operating period (not a phase horizon)


@dataclass(frozen=True)
class ForecastStep:
    phase: MainPhase
    expected_date: date | None
    source: str  # "VIB-PFA" | "Fulda-Runde" | "Infraplan" | "Manuell" | "BVWP" | "Schätzung"


@dataclass
class ForecastResult:
    current_phase: MainPhase
    remaining_text: str | None
    estimated_phase_end: date | None
    next_steps: list[ForecastStep] = field(default_factory=list)
    has_data: bool = False


def _years_to_days(years: float) -> int:
    return int(round(years * 365.25))


def _humanize_remaining(end: date, today: date) -> str:
    days = (end - today).days
    if days < 0:
        return "Termin voraussichtlich überschritten"
    if days < 45:
        return "Abschluss der aktuellen Phase steht unmittelbar bevor"
    months = days / 30.4
    if months < 18:
        return f"noch ca. {round(months)} Monate in der aktuellen Phase"
    years = days / 365.25
    return f"noch ca. {round(years)} Jahre in der aktuellen Phase"


def reduce_expected(claims: list[ExpectedDate]) -> list[ExpectedDate]:
    """One prognosis per phase: earliest start, but the latest in-service date.

    Several claims per phase arise when a superior pools its subtree (each
    section has its own dates) — same aggregation as the PFA sections. The
    pooled claim keeps the most recent report date.
    """

    best: dict[MainPhase, ExpectedDate] = {}
    for claim in claims:
        current = best.get(claim.phase)
        if current is None:
            best[claim.phase] = claim
            continue
        if claim.phase is MainPhase.IN_BETRIEB:
            dt = max(current.date, claim.date)
        else:
            dt = min(current.date, claim.date)
        reported = max(
            (d for d in (current.reported_on, claim.reported_on) if d is not None),
            default=None,
        )
        best[claim.phase] = ExpectedDate(phase=claim.phase, date=dt, reported_on=reported)
    return list(best.values())


def _weight(source: SourceType, reported_on: date | None, today: date) -> float:
    return SOURCE_TYPE_DEFAULT_TRUST[source] * recency_decay(reported_on, today)


def concrete_milestone_dates(
    *,
    pfas: list[PfaForecastInput],
    fulda: list[ExpectedDate],
    manual_expected: list[tuple[MainPhase, date]],
    today: date,
    pfb_as_genehmigung: bool = True,
    infraplan: list[ExpectedDate] | None = None,
    gvfg: list[ExpectedDate] | None = None,
) -> dict[MainPhase, tuple[date, str]]:
    """Concrete (non-estimated) milestone date per phase, with its source label.

    Shared by the forecast and the multi-project timeline so both apply the same
    precedence: per phase, the VIB-PFA, Fulda-Runde, Infraplan or GVFG date with the
    higher weight wins — trust of the source × recency of its report (tie →
    earlier date). Manual expected dates are editorial and always win.

    ``pfb_as_genehmigung`` maps the PFA ``datum_pfb`` onto GENEHMIGUNGSPLANUNG
    (the forecast's reading); the timeline shows the PFB as its own milestone
    and passes False.
    """

    # (date, source label, weight) candidates per phase.
    candidates: dict[MainPhase, list[tuple[date, str, float]]] = {}

    def _pfa_candidate(phase: MainPhase, field: str, pick) -> None:
        dated = [(getattr(p, field), p.reported_on) for p in pfas if getattr(p, field)]
        if not dated:
            return
        dt = pick(d for d, _ in dated)
        # The section(s) carrying the chosen date decide the weight.
        weight = max(_weight(SourceType.VIB, rep, today) for d, rep in dated if d == dt)
        candidates.setdefault(phase, []).append((dt, "VIB-PFA", weight))

    # Aggregate across PFA sections: earliest construction start (first section
    # breaks ground), latest in-service (last section opens), earliest PFB.
    if pfb_as_genehmigung:
        _pfa_candidate(MainPhase.GENEHMIGUNGSPLANUNG, "datum_pfb", min)
    _pfa_candidate(MainPhase.BAU, "baubeginn", min)
    _pfa_candidate(MainPhase.IN_BETRIEB, "inbetriebnahme", max)

    for claim in reduce_expected(fulda):
        candidates.setdefault(claim.phase, []).append(
            (claim.date, "Fulda-Runde", _weight(SourceType.FULDA_RUNDE, claim.reported_on, today))
        )
    # Several Infraplan rows per project (or subtree) → latest year (reduce).
    for claim in reduce_expected(infraplan or []):
        candidates.setdefault(claim.phase, []).append(
            (claim.date, "Infraplan", _weight(SourceType.INFRAPLAN, claim.reported_on, today))
        )
    # GVFG-Bundesprogramm: one expected commissioning per Vorhaben → latest year.
    for claim in reduce_expected(gvfg or []):
        candidates.setdefault(claim.phase, []).append(
            (claim.date, "GVFG", _weight(SourceType.GVFG, claim.reported_on, today))
        )

    concrete: dict[MainPhase, tuple[date, str]] = {}
    for phase, options in candidates.items():
        dt, source, _ = max(options, key=lambda o: (o[2], -o[0].toordinal()))
        concrete[phase] = (dt, source)

    # Manual expected dates are editorial — they always win over derived sources.
    for phase, dt in manual_expected:
        concrete[phase] = (dt, "Manuell")

    return concrete


def build_forecast(
    *,
    effective_phase: MainPhase,
    today: date,
    pfas: list[PfaForecastInput] | None = None,
    bvwp: BvwpDurations | None = None,
    fulda: list[ExpectedDate] | None = None,
    manual_expected: list[tuple[MainPhase, date]] | None = None,
    skipped_phases: frozenset[MainPhase] | set[MainPhase] = frozenset(),
    infraplan: list[ExpectedDate] | None = None,
    gvfg: list[ExpectedDate] | None = None,
) -> ForecastResult:
    pfas = pfas or []
    fulda = fulda or []
    manual_expected = manual_expected or []

    concrete = concrete_milestone_dates(
        pfas=pfas,
        fulda=fulda,
        manual_expected=manual_expected,
        today=today,
        infraplan=infraplan or [],
        gvfg=gvfg or [],
    )

    has_concrete = bool(concrete)
    has_bvwp = bvwp is not None and (
        bvwp.outstanding_planning is not None or bvwp.build is not None
    )

    # --- Build next steps for phases after the current one ------------------
    upcoming = [
        p
        for p in _FORECASTABLE
        if p.order > effective_phase.order and (p not in skipped_phases or p in concrete)
    ]
    next_steps: list[ForecastStep] = []

    # BVWP anchor: when no concrete BAU date, estimate it from today + planning.
    bvwp_bau_date: date | None = None
    if has_bvwp and bvwp and bvwp.outstanding_planning is not None:
        bvwp_bau_date = today + timedelta(days=_years_to_days(bvwp.outstanding_planning))

    for phase in upcoming:
        if phase in concrete:
            dt, source = concrete[phase]
            next_steps.append(ForecastStep(phase=phase, expected_date=dt, source=source))
            continue

        estimate: date | None = None
        if phase is MainPhase.BAU and bvwp_bau_date is not None:
            estimate = bvwp_bau_date
        elif phase is MainPhase.IN_BETRIEB and bvwp and bvwp.build is not None:
            anchor = (
                concrete.get(MainPhase.BAU, (None, ""))[0]
                or bvwp_bau_date
                or today
            )
            estimate = anchor + timedelta(days=_years_to_days(bvwp.build))

        next_steps.append(
            ForecastStep(
                phase=phase,
                expected_date=estimate,
                source="BVWP" if estimate is not None else "Schätzung",
            )
        )

    # --- Remaining duration of the current phase ----------------------------
    estimated_phase_end = next_steps[0].expected_date if next_steps else None
    remaining_text = (
        _humanize_remaining(estimated_phase_end, today)
        if estimated_phase_end is not None
        else None
    )

    return ForecastResult(
        current_phase=effective_phase,
        remaining_text=remaining_text,
        estimated_phase_end=estimated_phase_end,
        next_steps=next_steps,
        has_data=has_concrete or has_bvwp,
    )
