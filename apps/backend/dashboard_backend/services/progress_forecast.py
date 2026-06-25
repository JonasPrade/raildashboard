"""Pure planning-state forecast (no DB).

Combines three input kinds into a "remaining duration + next steps" forecast:
- **Concrete milestone dates** from VIB PFA fields (``baubeginn`` → BAU start,
  ``inbetriebnahme`` → IN_BETRIEB, ``datum_pfb`` → Genehmigung/PF done) and from
  Fulda-Runde announcements (manual observations carrying a phase + date).
- **BVWP planning/build durations** (years) as a fallback when no concrete date
  exists for an upcoming phase.

Concrete dates always win over BVWP estimates. The function is deterministic in
``today`` (passed in) so it stays unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from dashboard_backend.models.projects.progress_enums import MainPhase

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


@dataclass(frozen=True)
class BvwpDurations:
    outstanding_planning: float | None = None  # years until construction
    build: float | None = None  # years of construction
    operating: float | None = None  # operating period (not a phase horizon)


@dataclass(frozen=True)
class ForecastStep:
    phase: MainPhase
    expected_date: date | None
    source: str  # "VIB-PFA" | "Fulda-Runde" | "BVWP" | "Schätzung"


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


def build_forecast(
    *,
    effective_phase: MainPhase,
    today: date,
    pfas: list[PfaForecastInput] | None = None,
    bvwp: BvwpDurations | None = None,
    fulda: list[tuple[MainPhase, date]] | None = None,
) -> ForecastResult:
    pfas = pfas or []
    fulda = fulda or []

    # --- Concrete milestone dates per phase ---------------------------------
    # Aggregate across PFA sections: earliest construction start (first section
    # breaks ground), latest in-service (last section opens), earliest PFB.
    concrete: dict[MainPhase, tuple[date, str]] = {}
    baubeginn_dates = [p.baubeginn for p in pfas if p.baubeginn]
    inbetrieb_dates = [p.inbetriebnahme for p in pfas if p.inbetriebnahme]
    pfb_dates = [p.datum_pfb for p in pfas if p.datum_pfb]
    if pfb_dates:
        concrete[MainPhase.GENEHMIGUNGSPLANUNG] = (min(pfb_dates), "VIB-PFA")
    if baubeginn_dates:
        concrete[MainPhase.BAU] = (min(baubeginn_dates), "VIB-PFA")  # first section starts
    if inbetrieb_dates:
        concrete[MainPhase.IN_BETRIEB] = (max(inbetrieb_dates), "VIB-PFA")  # last section opens

    # Fulda announcements override only if earlier / fill gaps.
    for phase, dt in fulda:
        existing = concrete.get(phase)
        if existing is None or dt < existing[0]:
            concrete[phase] = (dt, "Fulda-Runde")

    has_concrete = bool(concrete)
    has_bvwp = bvwp is not None and (
        bvwp.outstanding_planning is not None or bvwp.build is not None
    )

    # --- Build next steps for phases after the current one ------------------
    upcoming = [p for p in _FORECASTABLE if p.order > effective_phase.order]
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
