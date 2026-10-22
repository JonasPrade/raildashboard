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

Every date carries its :class:`DatePrecision` (docs/features/feature-project-progress.md
→ „Datumsqualifikation“): a lower-bound Baubeginn yields a lower-bound
commissioning, a date computed by a rule is ASSUMED. Projects of a group with
``assumed_build_months`` (corridor renewals: 6) get their commissioning as
Baubeginn + that period when no source names one.

Concrete dates always win over BVWP estimates. Phases a project's groups skip
(``skipped_phases``, e.g. Vorplanung/Genehmigungsplanung for corridor renewals
without Planfeststellung) are left out of the next steps unless a concrete date
exists for them — data wins over the group default. The function is deterministic in
``today`` (passed in) so it stays unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from dashboard_backend.models.projects.progress_enums import (
    DatePrecision,
    MainPhase,
    SourceType,
)
from dashboard_backend.services.date_precision import (
    add_months,
    date_text,
    derived_precision,
)
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
    # Precision of the free-text dates (parse_flexible_date_with_precision).
    datum_pfb_precision: DatePrecision = DatePrecision.EXACT
    baubeginn_precision: DatePrecision = DatePrecision.EXACT
    inbetriebnahme_precision: DatePrecision = DatePrecision.EXACT


@dataclass(frozen=True)
class ExpectedDate:
    """A dated prognosis for a phase plus the date of the report stating it."""

    phase: MainPhase
    date: date
    reported_on: date | None = None
    precision: DatePrecision = DatePrecision.EXACT
    label: str | None = None


@dataclass(frozen=True)
class ConcreteDate:
    """The winning date of a phase with its source label and precision."""

    date: date
    source: str
    precision: DatePrecision = DatePrecision.EXACT
    label: str | None = None
    # How a computed date came about („Annahme: 6 Monate Bauzeit …“).
    derivation: str | None = None


# Source label of a commissioning computed from the group's build period.
ASSUMED_SOURCE = "Annahme"

ManualExpected = tuple[MainPhase, date] | ExpectedDate


@dataclass(frozen=True)
class BvwpDurations:
    outstanding_planning: float | None = None  # years until construction
    build: float | None = None  # years of construction
    operating: float | None = None  # operating period (not a phase horizon)


@dataclass(frozen=True)
class ForecastStep:
    phase: MainPhase
    expected_date: date | None
    # "VIB-PFA" | "Fulda-Runde" | "Infraplan" | "GVFG" | "Manuell" | "Annahme" | "BVWP" | "Schätzung"
    source: str
    precision: DatePrecision = DatePrecision.EXACT
    label: str | None = None
    derivation: str | None = None


@dataclass
class ForecastResult:
    current_phase: MainPhase
    remaining_text: str | None
    estimated_phase_end: date | None
    estimated_phase_end_precision: DatePrecision = DatePrecision.EXACT
    next_steps: list[ForecastStep] = field(default_factory=list)
    has_data: bool = False
    # Concrete date per phase incl. past ones (list caches, filters).
    concrete: dict[MainPhase, ConcreteDate] = field(default_factory=dict)


def _years_to_days(years: float) -> int:
    return int(round(years * 365.25))


def _humanize_remaining(
    end: date, today: date, precision: DatePrecision = DatePrecision.EXACT
) -> str:
    if precision is DatePrecision.NOT_BEFORE:
        # A lower bound is no end date — claim no remaining duration.
        return f"Ende der aktuellen Phase offen ({date_text(end, precision)})"
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
        pick = max if claim.phase is MainPhase.IN_BETRIEB else min
        # The claim carrying the chosen date keeps its precision and label.
        chosen = pick((current, claim), key=lambda c: c.date)
        reported = max(
            (d for d in (current.reported_on, claim.reported_on) if d is not None),
            default=None,
        )
        best[claim.phase] = ExpectedDate(
            phase=claim.phase,
            date=chosen.date,
            reported_on=reported,
            precision=chosen.precision,
            label=chosen.label,
        )
    return list(best.values())


def as_expected(item: ManualExpected) -> ExpectedDate:
    """Manual expected entries come as ``(phase, date)`` or as ExpectedDate."""

    if isinstance(item, ExpectedDate):
        return item
    phase, dt = item
    return ExpectedDate(phase=phase, date=dt)


def apply_assumed_build(
    concrete: dict[MainPhase, ConcreteDate], months: int | None
) -> dict[MainPhase, ConcreteDate]:
    """Commissioning = Baubeginn + ``months`` when no source names one.

    The group rule for projects without a published closure period (corridor
    renewals: 6 months). The result is ASSUMED, or NOT_BEFORE when the
    Baubeginn is only a lower bound.
    """

    bau = concrete.get(MainPhase.BAU)
    if not months or bau is None or MainPhase.IN_BETRIEB in concrete:
        return concrete
    concrete[MainPhase.IN_BETRIEB] = ConcreteDate(
        date=add_months(bau.date, months),
        source=ASSUMED_SOURCE,
        precision=derived_precision(bau.precision),
        derivation=(
            f"Annahme: {months} Monate Bauzeit ab Baubeginn "
            f"{date_text(bau.date, bau.precision)} ({bau.source})"
        ),
    )
    return concrete


def _weight(source: SourceType, reported_on: date | None, today: date) -> float:
    return SOURCE_TYPE_DEFAULT_TRUST[source] * recency_decay(reported_on, today)


def concrete_milestone_dates(
    *,
    pfas: list[PfaForecastInput],
    fulda: list[ExpectedDate],
    manual_expected: list[ManualExpected],
    today: date,
    pfb_as_genehmigung: bool = True,
    infraplan: list[ExpectedDate] | None = None,
    gvfg: list[ExpectedDate] | None = None,
    assumed_build_months: int | None = None,
) -> dict[MainPhase, ConcreteDate]:
    """Concrete (non-estimated) milestone date per phase, with its source label.

    Shared by the forecast and the multi-project timeline so both apply the same
    precedence: per phase, the VIB-PFA, Fulda-Runde, Infraplan or GVFG date with the
    higher weight wins — trust of the source × recency of its report (tie →
    earlier date). Manual expected dates are editorial and always win.

    ``pfb_as_genehmigung`` maps the PFA ``datum_pfb`` onto GENEHMIGUNGSPLANUNG
    (the forecast's reading); the timeline shows the PFB as its own milestone
    and passes False.

    ``assumed_build_months`` (group rule) fills a missing commissioning from the
    Baubeginn (:func:`apply_assumed_build`). Every date keeps its precision.
    """

    # (concrete date, weight) candidates per phase.
    candidates: dict[MainPhase, list[tuple[ConcreteDate, float]]] = {}

    def _pfa_candidate(phase: MainPhase, field: str, pick) -> None:
        dated = [
            (getattr(p, field), p.reported_on, getattr(p, f"{field}_precision"))
            for p in pfas
            if getattr(p, field)
        ]
        if not dated:
            return
        dt = pick(d for d, _, _ in dated)
        # The section(s) carrying the chosen date decide the weight.
        weight = max(_weight(SourceType.VIB, rep, today) for d, rep, _ in dated if d == dt)
        precision = next(prec for d, _, prec in dated if d == dt)
        candidates.setdefault(phase, []).append(
            (ConcreteDate(date=dt, source="VIB-PFA", precision=precision), weight)
        )

    def _claim_candidate(claim: ExpectedDate, source: str, source_type: SourceType) -> None:
        candidates.setdefault(claim.phase, []).append(
            (
                ConcreteDate(
                    date=claim.date, source=source, precision=claim.precision, label=claim.label
                ),
                _weight(source_type, claim.reported_on, today),
            )
        )

    # Aggregate across PFA sections: earliest construction start (first section
    # breaks ground), latest in-service (last section opens), earliest PFB.
    if pfb_as_genehmigung:
        _pfa_candidate(MainPhase.GENEHMIGUNGSPLANUNG, "datum_pfb", min)
    _pfa_candidate(MainPhase.BAU, "baubeginn", min)
    _pfa_candidate(MainPhase.IN_BETRIEB, "inbetriebnahme", max)

    for claim in reduce_expected(fulda):
        _claim_candidate(claim, "Fulda-Runde", SourceType.FULDA_RUNDE)
    # Several Infraplan rows per project (or subtree) → latest year (reduce).
    for claim in reduce_expected(infraplan or []):
        _claim_candidate(claim, "Infraplan", SourceType.INFRAPLAN)
    # GVFG-Bundesprogramm: one expected commissioning per Vorhaben → latest year.
    for claim in reduce_expected(gvfg or []):
        _claim_candidate(claim, "GVFG", SourceType.GVFG)

    concrete: dict[MainPhase, ConcreteDate] = {}
    for phase, options in candidates.items():
        concrete[phase] = max(options, key=lambda o: (o[1], -o[0].date.toordinal()))[0]

    # Manual expected dates are editorial — they always win over derived sources.
    for item in manual_expected:
        claim = as_expected(item)
        concrete[claim.phase] = ConcreteDate(
            date=claim.date, source="Manuell", precision=claim.precision, label=claim.label
        )

    return apply_assumed_build(concrete, assumed_build_months)


def build_forecast(
    *,
    effective_phase: MainPhase,
    today: date,
    pfas: list[PfaForecastInput] | None = None,
    bvwp: BvwpDurations | None = None,
    fulda: list[ExpectedDate] | None = None,
    manual_expected: list[ManualExpected] | None = None,
    skipped_phases: frozenset[MainPhase] | set[MainPhase] = frozenset(),
    infraplan: list[ExpectedDate] | None = None,
    gvfg: list[ExpectedDate] | None = None,
    assumed_build_months: int | None = None,
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
        assumed_build_months=assumed_build_months,
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
            c = concrete[phase]
            next_steps.append(
                ForecastStep(
                    phase=phase,
                    expected_date=c.date,
                    source=c.source,
                    precision=c.precision,
                    label=c.label,
                    derivation=c.derivation,
                )
            )
            continue

        # BVWP durations are estimates: ASSUMED, or NOT_BEFORE when anchored on
        # a lower-bound Baubeginn.
        estimate: date | None = None
        precision = DatePrecision.ASSUMED
        derivation: str | None = None
        if phase is MainPhase.BAU and bvwp_bau_date is not None:
            estimate = bvwp_bau_date
            derivation = f"Schätzung: heute + BVWP-Planungsdauer {bvwp.outstanding_planning:g} Jahre"
        elif phase is MainPhase.IN_BETRIEB and bvwp and bvwp.build is not None:
            bau = concrete.get(MainPhase.BAU)
            if bau is not None:
                anchor, precision = bau.date, derived_precision(bau.precision)
                anchor_text = f"Baubeginn {date_text(bau.date, bau.precision)}"
            elif bvwp_bau_date is not None:
                anchor, anchor_text = bvwp_bau_date, "geschätztem Baubeginn"
            else:
                anchor, anchor_text = today, "heute"
            estimate = anchor + timedelta(days=_years_to_days(bvwp.build))
            derivation = f"Schätzung: BVWP-Bauzeit {bvwp.build:g} Jahre ab {anchor_text}"

        next_steps.append(
            ForecastStep(
                phase=phase,
                expected_date=estimate,
                source="BVWP" if estimate is not None else "Schätzung",
                precision=precision if estimate is not None else DatePrecision.EXACT,
                derivation=derivation,
            )
        )

    # --- Remaining duration of the current phase ----------------------------
    first = next_steps[0] if next_steps else None
    estimated_phase_end = first.expected_date if first else None
    remaining_text = (
        _humanize_remaining(estimated_phase_end, today, first.precision)
        if first is not None and estimated_phase_end is not None
        else None
    )

    return ForecastResult(
        current_phase=effective_phase,
        remaining_text=remaining_text,
        estimated_phase_end=estimated_phase_end,
        estimated_phase_end_precision=first.precision if first else DatePrecision.EXACT,
        next_steps=next_steps,
        has_data=has_concrete or has_bvwp,
        concrete=concrete,
    )
