"""Pure mapping from VIB / FinVe records to derived observation specs.

These functions contain **no DB access** so they can be unit-tested directly.
``crud.projects.progress.sync_derived_observations`` loads the ORM records,
calls these mappers, and persists the resulting specs as ``ProgressObservation``
rows with ``is_derived=True``.

Mapping (per feature-project-progress.md):
- VIB ``status_planung`` → MAIN ≥ VORPLANUNG, ``status_bau`` → ≥ BAU,
  ``status_abgeschlossen`` → ≥ IN_BETRIEB. PFA fields drive the PF track
  (and the forecast, handled elsewhere).
- FinVe link → MAIN ≥ BAU; Sammel-FinVe weaker (lower explicit confidence).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from dashboard_backend.models.projects.progress_enums import (
    MainPhase,
    ObservationTrack,
    ParallelState,
    SourceType,
)
from dashboard_backend.services.progress_dates import parse_flexible_date

# Sammel-FinVe (year-scoped pooled financing) is a much weaker signal than a
# dedicated FinVe, so it gets an explicit low confidence instead of the FinVe
# source default.
SAMMEL_FINVE_CONFIDENCE = 0.35


@dataclass(frozen=True)
class DerivedSpec:
    """A derived observation to be materialised (mirrors ObservationInput +
    provenance). ``confidence=None`` means: use the source-type default."""

    source_type: SourceType
    track: ObservationTrack
    asserted_state: str
    observed_date: date | None = None
    confidence: float | None = None
    note: str | None = None
    vib_entry_id: int | None = None
    vib_pfa_entry_id: int | None = None
    finve_id: int | None = None


@dataclass(frozen=True)
class PfaInput:
    id: int
    nr_pfa: str | None = None
    abschnitt_label: str | None = None
    datum_pfb: str | None = None
    baubeginn: str | None = None
    inbetriebnahme: str | None = None


def _strongest_vib_main_phase(
    status_planung: bool, status_bau: bool, status_abgeschlossen: bool
) -> MainPhase | None:
    if status_abgeschlossen:
        return MainPhase.IN_BETRIEB
    if status_bau:
        return MainPhase.BAU
    if status_planung:
        return MainPhase.VORPLANUNG
    return None


def vib_entry_to_specs(
    *,
    vib_entry_id: int,
    status_planung: bool,
    status_bau: bool,
    status_abgeschlossen: bool,
    observed_date: date | None,
    has_planfeststellung_flag: bool,
    pfas: list[PfaInput],
) -> list[DerivedSpec]:
    """Build derived specs for one linked VIB entry.

    The MAIN spec reflects the strongest true status flag. Each PFA produces a
    PF-track spec (ABGESCHLOSSEN once a Planfeststellungsbeschluss date exists,
    otherwise LAEUFT). ``has_planfeststellung_flag`` only affects the note —
    the caller decides whether to flip the editorial flag.
    """

    specs: list[DerivedSpec] = []

    main_phase = _strongest_vib_main_phase(status_planung, status_bau, status_abgeschlossen)
    if main_phase is not None:
        specs.append(
            DerivedSpec(
                source_type=SourceType.VIB,
                track=ObservationTrack.MAIN,
                asserted_state=main_phase.value,
                observed_date=observed_date,
                note="aus VIB-Statusangaben",
                vib_entry_id=vib_entry_id,
            )
        )

    for pfa in pfas:
        pfb_date = parse_flexible_date(pfa.datum_pfb)
        label = pfa.nr_pfa or pfa.abschnitt_label or "PFA"
        if pfb_date is not None:
            specs.append(
                DerivedSpec(
                    source_type=SourceType.VIB,
                    track=ObservationTrack.PF,
                    asserted_state=ParallelState.ABGESCHLOSSEN.value,
                    observed_date=observed_date,
                    note=f"{label}: PFB {pfa.datum_pfb}",
                    vib_entry_id=vib_entry_id,
                    vib_pfa_entry_id=pfa.id,
                )
            )
        else:
            specs.append(
                DerivedSpec(
                    source_type=SourceType.VIB,
                    track=ObservationTrack.PF,
                    asserted_state=ParallelState.LAEUFT.value,
                    observed_date=observed_date,
                    note=f"{label}: Planfeststellung läuft",
                    vib_entry_id=vib_entry_id,
                    vib_pfa_entry_id=pfa.id,
                )
            )

    return specs


def finve_to_spec(
    *,
    finve_id: int,
    is_sammel: bool,
    starting_year: int | None,
) -> DerivedSpec:
    """A financing agreement implies construction is funded → MAIN ≥ BAU.

    A Sammel-FinVe (pooled, year-scoped) is a weaker signal → only
    GENEHMIGUNGSPLANUNG, with a low explicit confidence.
    """

    observed = None
    if starting_year:
        observed = date(starting_year, 1, 1)

    if is_sammel:
        return DerivedSpec(
            source_type=SourceType.FINVE,
            track=ObservationTrack.MAIN,
            asserted_state=MainPhase.GENEHMIGUNGSPLANUNG.value,
            observed_date=observed,
            confidence=SAMMEL_FINVE_CONFIDENCE,
            note="Sammelfinanzierungsvereinbarung",
            finve_id=finve_id,
        )

    return DerivedSpec(
        source_type=SourceType.FINVE,
        track=ObservationTrack.MAIN,
        asserted_state=MainPhase.BAU.value,
        observed_date=observed,
        note="Finanzierungsvereinbarung",
        finve_id=finve_id,
    )


def pfa_has_pf_evidence(pfas: list[PfaInput]) -> bool:
    """True if any PFA carries Planfeststellung evidence (label/nr or PFB date)."""

    return any(
        (p.nr_pfa or p.abschnitt_label or parse_flexible_date(p.datum_pfb)) for p in pfas
    )
