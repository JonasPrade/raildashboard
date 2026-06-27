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

import re
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


def parse_sammel_finve_phase(name: str | None) -> MainPhase | None:
    """Map a Sammel-FinVe name to a planning phase by its Leistungsphase.

    Only the explicit ``Lph`` marker is honoured: ``"SV Lph. 1/2 A"`` →
    VORPLANUNG, ``"SV Lph. 3/ 4"`` → GENEHMIGUNGSPLANUNG. Crucially, this must
    NOT trigger on EKrG-style numbering like ``"SV 3/2010 (EKrG)"`` (the ``3``
    there is an agreement number, not a Leistungsphase). Returns ``None`` when
    no Leistungsphase can be determined.
    """

    if not name:
        return None
    lowered = name.lower()
    if "lph" not in lowered:
        return None
    # Normalise whitespace around the slash ("3/ 4" → "3/4").
    compact = re.sub(r"\s*/\s*", "/", lowered)
    if "1/2" in compact:
        return MainPhase.VORPLANUNG
    if "3/4" in compact:
        return MainPhase.GENEHMIGUNGSPLANUNG
    return None


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
    bauportal_status_id: int | None = None
    media_report_id: int | None = None


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


def _pfa_main_phase(pfa: PfaInput) -> tuple[MainPhase | None, date | None]:
    """Derive a leaf MAIN phase + its date from a single PFA's milestone dates.

    ``inbetriebnahme`` → IN_BETRIEB, else ``baubeginn`` → BAU, else ``datum_pfb``
    (the Planfeststellungsbeschluss concludes the approval phase) →
    GENEHMIGUNGSPLANUNG. No parseable milestone → no MAIN contribution.
    """

    ib = parse_flexible_date(pfa.inbetriebnahme)
    if ib is not None:
        return MainPhase.IN_BETRIEB, ib
    bb = parse_flexible_date(pfa.baubeginn)
    if bb is not None:
        return MainPhase.BAU, bb
    pfb = parse_flexible_date(pfa.datum_pfb)
    if pfb is not None:
        return MainPhase.GENEHMIGUNGSPLANUNG, pfb
    return None, None


def _pfa_pf_spec(pfa: PfaInput, observed_date: date | None, vib_entry_id: int) -> DerivedSpec:
    """PF-track spec for one PFA: ABGESCHLOSSEN once a PFB date exists, else LAEUFT."""

    pfb_date = parse_flexible_date(pfa.datum_pfb)
    label = pfa.nr_pfa or pfa.abschnitt_label or "PFA"
    if pfb_date is not None:
        return DerivedSpec(
            source_type=SourceType.VIB,
            track=ObservationTrack.PF,
            asserted_state=ParallelState.ABGESCHLOSSEN.value,
            observed_date=observed_date,
            note=f"{label}: PFB {pfa.datum_pfb}",
            vib_entry_id=vib_entry_id,
            vib_pfa_entry_id=pfa.id,
        )
    return DerivedSpec(
        source_type=SourceType.VIB,
        track=ObservationTrack.PF,
        asserted_state=ParallelState.LAEUFT.value,
        observed_date=observed_date,
        note=f"{label}: Planfeststellung läuft",
        vib_entry_id=vib_entry_id,
        vib_pfa_entry_id=pfa.id,
    )


def vib_entry_to_specs(
    *,
    vib_entry_id: int,
    status_planung: bool,
    status_bau: bool,
    status_abgeschlossen: bool,
    observed_date: date | None,
    has_planfeststellung_flag: bool,
    pfas: list[PfaInput],
    emit_main: bool = True,
) -> list[DerivedSpec]:
    """Build derived specs for one linked VIB entry (parent/unassigned side).

    The MAIN spec reflects the strongest true status flag, but is suppressed when
    ``emit_main`` is False — used once the entry's sections are split out to
    subprojects, so the parent aggregates via the children's span instead of the
    flattened entry phase. Each passed PFA produces a PF-track spec.
    ``has_planfeststellung_flag`` only affects the note — the caller decides
    whether to flip the editorial flag.
    """

    specs: list[DerivedSpec] = []

    if emit_main:
        main_phase = _strongest_vib_main_phase(
            status_planung, status_bau, status_abgeschlossen
        )
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
        specs.append(_pfa_pf_spec(pfa, observed_date, vib_entry_id))

    return specs


def pfa_to_specs(
    *,
    pfa: PfaInput,
    vib_entry_id: int,
    observed_fallback: date | None,
) -> list[DerivedSpec]:
    """Build derived specs for one PFA assigned to a leaf subproject.

    Emits a MAIN spec derived from the section's own milestone dates (so the
    status lands on the subproject, not the flattened parent) plus the PF-track
    spec. ``observed_fallback`` (the report year-end) is used when the MAIN
    milestone itself carries no parseable date.
    """

    specs: list[DerivedSpec] = []
    main_phase, main_date = _pfa_main_phase(pfa)
    label = pfa.nr_pfa or pfa.abschnitt_label or "PFA"
    if main_phase is not None:
        specs.append(
            DerivedSpec(
                source_type=SourceType.VIB,
                track=ObservationTrack.MAIN,
                asserted_state=main_phase.value,
                observed_date=main_date or observed_fallback,
                note=f"{label}: aus PFA-Terminen",
                vib_entry_id=vib_entry_id,
                vib_pfa_entry_id=pfa.id,
            )
        )
    specs.append(_pfa_pf_spec(pfa, observed_fallback, vib_entry_id))
    return specs


def finve_to_spec(
    *,
    finve_id: int,
    is_sammel: bool,
    starting_year: int | None,
    name: str | None = None,
    manual_phase: MainPhase | None = None,
) -> DerivedSpec | None:
    """Map a FinVe to a MAIN observation spec.

    - **Regular FinVe** (Baufinanzierungsvereinbarung) → BAU.
    - **Sammel-FinVe**: phase comes from ``manual_phase`` (editor override) if
      set, else from the Leistungsphase in the name (Lph 1/2 → VORPLANUNG,
      Lph 3/4 → GENEHMIGUNGSPLANUNG). Always weaker confidence.
    - A Sammel-FinVe whose phase can't be determined returns ``None`` (no
      contribution) — it is surfaced for manual assignment instead of guessed.
    """

    observed = None
    if starting_year:
        observed = date(starting_year, 1, 1)

    label = f"FinVe {finve_id}" + (f" · {name}" if name else "")

    if not is_sammel:
        return DerivedSpec(
            source_type=SourceType.FINVE,
            track=ObservationTrack.MAIN,
            asserted_state=MainPhase.BAU.value,
            observed_date=observed,
            note=f"Finanzierungsvereinbarung ({label})",
            finve_id=finve_id,
        )

    phase = manual_phase or parse_sammel_finve_phase(name)
    if phase is None:
        return None  # ambiguous Sammel-FinVe → manual assignment required

    return DerivedSpec(
        source_type=SourceType.FINVE,
        track=ObservationTrack.MAIN,
        asserted_state=phase.value,
        observed_date=observed,
        confidence=SAMMEL_FINVE_CONFIDENCE,
        note=f"Sammel-FinVe ({label})",
        finve_id=finve_id,
    )


def bauportal_status_to_main_phase(status_raw: str | None) -> MainPhase | None:
    """Map a DB-Bauportal ``icon_title`` to a MainPhase.

    ``"…Bauphase"`` → BAU, ``"…Planungsphase"`` → VORPLANUNG (conservative lower
    bound — the portal does not distinguish Vor-/Genehmigungsplanung). Mixed
    (``"…gemischter Projektphase"``) or umbrella (``"Gesamtprojekt …"``) entries
    carry no single phase → no contribution (the parent aggregates over its
    children's span instead).
    """

    if not status_raw:
        return None
    lowered = status_raw.lower()
    if "gemischt" in lowered or "gesamtprojekt" in lowered:
        return None
    if "bauphase" in lowered:
        return MainPhase.BAU
    if "planungsphase" in lowered:
        return MainPhase.VORPLANUNG
    return None


def bauportal_to_spec(
    *,
    bauportal_status_id: int,
    status_raw: str | None,
    projecttime_raw: str | None,
    observed_date: date | None,
) -> DerivedSpec | None:
    """Map a confirmed-matched Bauportal record to a MAIN observation spec.

    Returns ``None`` for mixed/umbrella entries (no single phase). Confidence is
    left at the BAUPORTAL source default (0.8); ``observed_date`` should be the
    fetch date so the portal stays fresh against older sources.
    """

    phase = bauportal_status_to_main_phase(status_raw)
    if phase is None:
        return None
    note = f"DB-Bauportal: {projecttime_raw}" if projecttime_raw else "DB-Bauportal"
    return DerivedSpec(
        source_type=SourceType.BAUPORTAL,
        track=ObservationTrack.MAIN,
        asserted_state=phase.value,
        observed_date=observed_date,
        note=note,
        bauportal_status_id=bauportal_status_id,
    )


def _coerce_main_phase(value: str | None) -> MainPhase | None:
    if not value:
        return None
    try:
        return MainPhase(value)
    except ValueError:
        return None


def media_to_spec(
    *,
    media_report_id: int,
    asserted_phase: str | None,
    observed_date: date | None,
    publication: str | None = None,
    url: str | None = None,
    quote: str | None = None,
) -> DerivedSpec | None:
    """Map a confirmed media report to a MAIN observation spec (low trust 0.4).

    Returns ``None`` when the asserted phase is missing/invalid (the editor must
    pick a valid MainPhase before it contributes). The note carries the
    publication, quote and URL so the provenance is visible in the breakdown.
    """

    phase = _coerce_main_phase(asserted_phase)
    if phase is None:
        return None
    note_parts = [p for p in ("Medien", publication) if p]
    head = ": ".join(note_parts) if len(note_parts) > 1 else note_parts[0]
    detail = " — ".join(p for p in (quote, url) if p)
    note = f"{head} — {detail}" if detail else head
    return DerivedSpec(
        source_type=SourceType.MEDIEN,
        track=ObservationTrack.MAIN,
        asserted_state=phase.value,
        observed_date=observed_date,
        note=note,
        media_report_id=media_report_id,
    )


def pfa_has_pf_evidence(pfas: list[PfaInput]) -> bool:
    """True if any PFA carries Planfeststellung evidence (label/nr or PFB date)."""

    return any(
        (p.nr_pfa or p.abschnitt_label or parse_flexible_date(p.datum_pfb)) for p in pfas
    )
