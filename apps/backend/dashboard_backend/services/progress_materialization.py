"""Pure mapping from VIB / FinVe / … / Infraplan records to derived observation specs.

These functions contain **no DB access** so they can be unit-tested directly.
``crud.projects.progress.sync_derived_observations`` loads the ORM records,
calls these mappers, and persists the resulting specs as ``ProgressObservation``
rows with ``is_derived=True``.

Mapping (per feature-project-progress.md):
- VIB ``status_planung`` → MAIN ≥ VORPLANUNG, ``status_bau`` → ≥ BAU,
  ``status_abgeschlossen`` → ≥ IN_BETRIEB. PFA fields drive the PF track
  (and the forecast, handled elsewhere); PFAs assigned to a leaf give its MAIN
  phase from the milestones actually reached — prognoses („vsl. 2027“) are
  expected observations.
- FinVe link → MAIN ≥ BAU; Sammel-FinVe weaker (lower explicit confidence),
  dated by the first Haushalt edition listing the project.
- GVFG-Bundesprogramm (newest edition) → MAIN from Inbetriebnahme, Lph and
  Baubeginn, plus the expected commissioning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from dashboard_backend.models.projects.progress_enums import (
    DatePrecision,
    MainPhase,
    ObservationTrack,
    ParallelState,
    SourceType,
)
from dashboard_backend.services.fulda_categories import get_category
from dashboard_backend.services.progress_dates import (
    Milestone,
    commissioning_in_year,
    parse_flexible_date,
    read_milestone,
)
from dashboard_backend.services.sammel_years import listing_label

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
    fulda_announcement_id: int | None = None
    infraplan_entry_id: int | None = None
    gvfg_entry_id: int | None = None
    # Prognosis: feeds the forecast only, never the phase.
    is_expected: bool = False
    # How precisely ``observed_date`` is known (year-only sources → YEAR).
    date_precision: DatePrecision = DatePrecision.EXACT


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


@dataclass(frozen=True)
class _Section:
    """One PFA read as of the report's year-end: the last milestone reached
    (``phase``) and the milestones still expected."""

    pfa: PfaInput
    phase: MainPhase | None
    reached: Milestone | None
    expected_bau: Milestone | None
    expected_ibn: Milestone | None

    @property
    def is_open(self) -> bool:
        """Not in operation yet, and the table says something about it."""
        if self.phase is MainPhase.IN_BETRIEB:
            return False
        return self.phase is not None or self.expected_bau is not None or self.expected_ibn is not None


def _read_section(pfa: PfaInput, as_of: date | None) -> _Section:
    """Milestones of one PFA: Inbetriebnahme → IN_BETRIEB, else Baubeginn →
    BAU, else PFB (concludes the approval phase) → GENEHMIGUNGSPLANUNG — only
    milestones actually reached by ``as_of`` count; a hedged or later date
    („vsl. 2027“, „2027“ in the VIB 2024) is expected."""

    ibn = read_milestone(pfa.inbetriebnahme, as_of, commissioning=True)
    start = read_milestone(pfa.baubeginn, as_of)
    pfb = read_milestone(pfa.datum_pfb, as_of)
    phase, reached = None, None
    for candidate, milestone in (
        (MainPhase.IN_BETRIEB, ibn),
        (MainPhase.BAU, start),
        (MainPhase.GENEHMIGUNGSPLANUNG, pfb),
    ):
        if milestone is not None and not milestone.is_expected:
            phase, reached = candidate, milestone
            break

    def pending(milestone: Milestone | None) -> Milestone | None:
        return milestone if milestone is not None and milestone.is_expected else None

    return _Section(
        pfa=pfa,
        phase=phase,
        reached=reached,
        expected_bau=pending(start) if phase in (None, MainPhase.GENEHMIGUNGSPLANUNG) else None,
        expected_ibn=pending(ibn) if phase is not MainPhase.IN_BETRIEB else None,
    )


def _pfa_label(pfa: PfaInput) -> str:
    return pfa.nr_pfa or pfa.abschnitt_label or "PFA"


def _labels(sections: list[_Section]) -> str:
    return ", ".join(dict.fromkeys(_pfa_label(s.pfa) for s in sections))


def _pfa_pf_spec(pfa: PfaInput, observed_date: date | None, vib_entry_id: int) -> DerivedSpec:
    """PF-track spec for one PFA: ABGESCHLOSSEN once the PFB has been issued by
    the report's year-end (``observed_date``), else LAEUFT — a PFB „vsl. 2027“
    is still pending."""

    pfb = read_milestone(pfa.datum_pfb, observed_date)
    label = _pfa_label(pfa)
    if pfb is not None and not pfb.is_expected:
        return DerivedSpec(
            source_type=SourceType.VIB,
            track=ObservationTrack.PF,
            asserted_state=ParallelState.ABGESCHLOSSEN.value,
            observed_date=observed_date,
            note=f"{label}: PFB {pfa.datum_pfb}",
            vib_entry_id=vib_entry_id,
            vib_pfa_entry_id=pfa.id,
        )
    pending = f" (PFB {pfa.datum_pfb})" if pfb is not None else ""
    return DerivedSpec(
        source_type=SourceType.VIB,
        track=ObservationTrack.PF,
        asserted_state=ParallelState.LAEUFT.value,
        observed_date=observed_date,
        note=f"{label}: Planfeststellung läuft{pending}",
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


def assigned_pfas_to_specs(
    *,
    pfas: list[PfaInput],
    vib_entry_id: int,
    observed_fallback: date | None,
) -> list[DerivedSpec]:
    """Build derived specs for the PFAs of one VIB entry assigned to one leaf
    subproject (so the status lands on the subproject, not the flattened parent).

    ``observed_fallback`` is the report's year-end: the day the table speaks
    for. Only milestones reached by then are facts (:func:`_read_section`).

    - **One MAIN spec per leaf and entry.** The leaf is IN_BETRIEB only when no
      section is still open; otherwise it takes the highest phase reached among
      the open sections (finished sections next to sections under construction
      → BAU). Separate per-section reports would let a finished section win on
      the newest date or on the higher phase of a tie. Dated on the latest
      milestone of those sections (``observed_fallback`` when undated,
      „erfolgt“). Open sections without any milestone reached yet → no MAIN.
    - **Expected** (``is_expected``) Bau at the earliest pending Baubeginn while
      no section is building yet, and IN_BETRIEB at the latest pending
      Inbetriebnahme — they feed the timeline / breakdown, never the phase.
    - One PF-track spec per section.
    """

    sections = [_read_section(pfa, observed_fallback) for pfa in pfas]
    open_sections = [s for s in sections if s.is_open]
    if open_sections:
        candidates = [s for s in open_sections if s.phase is not None]
    else:
        candidates = [s for s in sections if s.phase is MainPhase.IN_BETRIEB]

    specs: list[DerivedSpec] = []
    phase = max((s.phase for s in candidates), key=lambda p: p.order, default=None)
    if phase is not None:
        at_phase = [s for s in candidates if s.phase is phase]

        def reached_on(section: _Section) -> date | None:
            return section.reached.value or observed_fallback

        decisive = max(at_phase, key=lambda s: reached_on(s) or date.min)
        count = f" ({len(at_phase)} von {len(sections)} Abschnitten)" if len(sections) > 1 else ""
        specs.append(
            DerivedSpec(
                source_type=SourceType.VIB,
                track=ObservationTrack.MAIN,
                asserted_state=phase.value,
                observed_date=reached_on(decisive),
                date_precision=decisive.reached.precision,
                note=f"{_labels(at_phase)}: aus PFA-Terminen{count}",
                vib_entry_id=vib_entry_id,
                vib_pfa_entry_id=decisive.pfa.id,
            )
        )

    if phase is None or phase.order < MainPhase.BAU.order:
        pending_bau = [s for s in sections if s.expected_bau is not None]
        if pending_bau:
            first = min(pending_bau, key=lambda s: s.expected_bau.value)
            specs.append(
                DerivedSpec(
                    source_type=SourceType.VIB,
                    track=ObservationTrack.MAIN,
                    asserted_state=MainPhase.BAU.value,
                    observed_date=first.expected_bau.value,
                    date_precision=first.expected_bau.precision,
                    note=f"{_pfa_label(first.pfa)}: Baubeginn {first.pfa.baubeginn}",
                    vib_entry_id=vib_entry_id,
                    vib_pfa_entry_id=first.pfa.id,
                    is_expected=True,
                )
            )
    if open_sections:
        pending_ibn = [s for s in sections if s.expected_ibn is not None]
        if pending_ibn:
            last = max(pending_ibn, key=lambda s: s.expected_ibn.value)
            specs.append(
                DerivedSpec(
                    source_type=SourceType.VIB,
                    track=ObservationTrack.MAIN,
                    asserted_state=MainPhase.IN_BETRIEB.value,
                    observed_date=last.expected_ibn.value,
                    date_precision=last.expected_ibn.precision,
                    note=f"{_pfa_label(last.pfa)}: Inbetriebnahme {last.pfa.inbetriebnahme}",
                    vib_entry_id=vib_entry_id,
                    vib_pfa_entry_id=last.pfa.id,
                    is_expected=True,
                )
            )

    specs.extend(_pfa_pf_spec(pfa, observed_fallback, vib_entry_id) for pfa in pfas)
    return specs


def finve_to_spec(
    *,
    finve_id: int,
    is_sammel: bool,
    starting_year: int | None,
    name: str | None = None,
    manual_phase: MainPhase | None = None,
    listed_years: list[int] | None = None,
    first_edition_year: int | None = None,
) -> DerivedSpec | None:
    """Map a FinVe to a MAIN observation spec.

    - **Regular FinVe** (Baufinanzierungsvereinbarung) → BAU.
    - **Sammel-FinVe**: phase comes from ``manual_phase`` (editor override) if
      set, else from the Leistungsphase in the name (Lph 1/2 → VORPLANUNG,
      Lph 3/4 → GENEHMIGUNGSPLANUNG). Always weaker confidence.
    - A Sammel-FinVe whose phase can't be determined returns ``None`` (no
      contribution) — it is surfaced for manual assignment instead of guessed.
    - A Sammel-FinVe is dated by the first Haushalt edition that lists the
      project (``listed_years``), never by the agreement's conclusion year:
      the project list is rewritten every year. ``first_edition_year`` (the
      earliest edition read in) marks that the project may be listed earlier.
    """

    label = f"FinVe {finve_id}" + (f" · {name}" if name else "")

    if not is_sammel:
        observed = date(starting_year, 1, 1) if starting_year else None
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

    listing = listing_label(listed_years or [], first_edition_year)
    return DerivedSpec(
        source_type=SourceType.FINVE,
        track=ObservationTrack.MAIN,
        asserted_state=phase.value,
        observed_date=date(min(listed_years), 1, 1) if listed_years else None,
        date_precision=DatePrecision.YEAR,
        confidence=SAMMEL_FINVE_CONFIDENCE,
        note=f"Sammel-FinVe ({label})" + (f" · gelistet {listing}" if listing else ""),
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


def fulda_to_spec(
    *,
    fulda_announcement_id: int,
    category: str | None,
    document_date: date | None,
    expected_date: date | None,
    drucksache: str | None = None,
) -> DerivedSpec | None:
    """Map a confirmed Fulda announcement to a MAIN observation spec (trust 0.55).

    "Ist" lines (current phase, completed without follow-up phase) assert their
    phase as of the answer's ``document_date``. Prognoses and new admissions
    become an *expected* observation (``is_expected``) at ``expected_date``
    (fallback: 31 Dec of the document year): it never raises the phase and only
    feeds the forecast / timeline. Returns ``None`` for hint-only categories.
    """

    cat = get_category(category)
    if cat is None or cat.phase is None:
        return None
    note = f"Fulda-Runde (Drs. {drucksache})" if drucksache else "Fulda-Runde"
    precision = DatePrecision.EXACT
    if cat.is_expected:
        observed = expected_date
        if observed is None and document_date is not None:
            # No prognosis date printed: the answer's year is all we know.
            observed, precision = date(document_date.year, 12, 31), DatePrecision.YEAR
    else:
        observed = document_date
    return DerivedSpec(
        source_type=SourceType.FULDA_RUNDE,
        track=ObservationTrack.MAIN,
        asserted_state=cat.phase.value,
        observed_date=observed,
        note=note,
        is_expected=cat.is_expected,
        fulda_announcement_id=fulda_announcement_id,
        date_precision=precision,
    )


def pfa_has_pf_evidence(pfas: list[PfaInput]) -> bool:
    """True if any PFA carries Planfeststellung evidence (label/nr or PFB date)."""

    return any(
        (p.nr_pfa or p.abschnitt_label or parse_flexible_date(p.datum_pfb)) for p in pfas
    )


# GVFG rows of the Infraplan are Länderangaben, unchecked (Fn. 23): lower trust.
INFRAPLAN_GVFG_CONFIDENCE = 0.75


def infraplan_main_phase(
    *,
    section: str,
    lph_from: int | None,
    lph_to: int | None,
    under_construction: bool,
    baurecht: bool,
) -> MainPhase | None:
    """Lower bound of the main phase from a row's Realisierungsstand.

    ``Bau`` → BAU; ``Lph 4 abgeschlossen – durchgängiges Baurecht`` →
    GENEHMIGUNGSPLANUNG (the PF track is completed separately); Teil D (no
    Lph yet) → NICHT_GESTARTET; otherwise by the Leistungsphasen: within 1–2 →
    VORPLANUNG, within 3–4 → GENEHMIGUNGSPLANUNG, from 5 → BAU. Spans across
    those bounds (``Lph 1 - 4``, ``Lph 1 - 9``) and ``offen`` say nothing.
    """

    if under_construction:
        return MainPhase.BAU
    if baurecht:
        return MainPhase.GENEHMIGUNGSPLANUNG
    if section == "BP_D":
        return MainPhase.NICHT_GESTARTET
    if lph_from is None:
        return None
    upper = lph_to if lph_to is not None else lph_from
    if lph_from >= 5:
        return MainPhase.BAU
    if lph_from >= 3 and upper <= 4:
        return MainPhase.GENEHMIGUNGSPLANUNG
    if lph_from >= 1 and upper <= 2:
        return MainPhase.VORPLANUNG
    return None


def infraplan_entry_to_specs(
    *,
    infraplan_entry_id: int,
    section: str,
    report_year: int,
    observed_date: date | None,
    lph_from: int | None,
    lph_to: int | None,
    under_construction: bool,
    baurecht: bool,
    ibn_year: int | None,
    ibn_qualifier: str | None,
    parl_state: str | None,
    state_raw: str | None = None,
    include_phase_and_date: bool = True,
) -> list[DerivedSpec]:
    """Derived specs for one Infraplan row linked to a project (trust 0.85,
    GVFG rows 0.75).

    - MAIN: lower bound from the Realisierungsstand (:func:`infraplan_main_phase`).
    - PF: ABGESCHLOSSEN for ``durchgängiges Baurecht``.
    - PARL (Bedarfsplan only): ``abgeschlossen`` → ABGESCHLOSSEN, ``Verfahren
      läuft`` → LAEUFT; ``vorgesehen`` / ``nicht vereinbart`` assert nothing.
    - Expected IN_BETRIEB at 31 Dec of the planned commissioning year — not for
      ``offen`` nor for a year before the report (GVFG remainders).

    ``include_phase_and_date`` is False for a GVFG row whose GVFG edition is
    more recent (decision 22): that edition then delivers phase and date.
    """

    is_gvfg = section.startswith("GVFG")
    confidence = INFRAPLAN_GVFG_CONFIDENCE if is_gvfg else None
    label = f"Infraplan {report_year}"
    specs: list[DerivedSpec] = []

    def spec(track: ObservationTrack, state: str, note: str, **extra) -> DerivedSpec:
        return DerivedSpec(
            source_type=SourceType.INFRAPLAN,
            track=track,
            asserted_state=state,
            observed_date=extra.pop("observed", observed_date),
            confidence=confidence,
            note=note,
            infraplan_entry_id=infraplan_entry_id,
            **extra,
        )

    if include_phase_and_date:
        phase = infraplan_main_phase(
            section=section,
            lph_from=lph_from,
            lph_to=lph_to,
            under_construction=under_construction,
            baurecht=baurecht,
        )
        if phase is not None:
            state = f": {state_raw}" if state_raw else ""
            specs.append(spec(ObservationTrack.MAIN, phase.value, f"{label}{state}"))
        if baurecht:
            specs.append(
                spec(ObservationTrack.PF, ParallelState.ABGESCHLOSSEN.value, f"{label}: durchgängiges Baurecht")
            )
        if ibn_year is not None and ibn_qualifier != "OFFEN" and ibn_year >= report_year:
            specs.append(
                spec(
                    ObservationTrack.MAIN,
                    MainPhase.IN_BETRIEB.value,
                    f"{label}: geplante Inbetriebnahme {ibn_year}",
                    observed=commissioning_in_year(ibn_year)[0],
                    is_expected=True,
                    # Year only: the Fahrplanwechsel, shown as 12/YYYY.
                    date_precision=commissioning_in_year(ibn_year)[1],
                )
            )

    if not is_gvfg and parl_state in ("ABGESCHLOSSEN", "LAEUFT"):
        specs.append(
            spec(
                ObservationTrack.PARL,
                ParallelState(parl_state).value,
                f"{label}: parlamentarische Befassung "
                + ("abgeschlossen" if parl_state == "ABGESCHLOSSEN" else "läuft"),
            )
        )
    return specs


def infraplan_parl_relevant(parl_state: str | None) -> bool | None:
    """PaBe relevance "laut Infraplan": ``nicht vereinbart`` → not relevant,
    any other statement → relevant, no statement (GVFG/InvKG) → None."""

    if not parl_state:
        return None
    return parl_state != "NICHT_VEREINBART"


_GVFG_LPH = re.compile(r"^\s*(\d)\s*(?:-\s*(\d))?\s*$")


def gvfg_lph_main_phase(lph: str | None) -> MainPhase | None:
    """Lower bound of the main phase from the printed Lph of a GVFG Vorhaben.

    Same reading as the GVFG rows of the Infraplan (:func:`infraplan_main_phase`):
    from 5 → BAU, within 3–4 → GENEHMIGUNGSPLANUNG, within 1–2 → VORPLANUNG;
    a lone ``9`` (Objektbetreuung) → IN_BETRIEB. Spans across those bounds
    (``1 - 9``, ``4 - 8``) and lists (``4, 9``, ``1 - 3 / 5 - 9``) say nothing.
    """

    match = _GVFG_LPH.match(lph or "")
    if match is None:
        return None
    lph_from = int(match.group(1))
    upper = int(match.group(2)) if match.group(2) else lph_from
    if lph_from == 9:
        return MainPhase.IN_BETRIEB
    if lph_from >= 5:
        return MainPhase.BAU
    if lph_from >= 3 and upper <= 4:
        return MainPhase.GENEHMIGUNGSPLANUNG
    if lph_from >= 1 and upper <= 2:
        return MainPhase.VORPLANUNG
    return None


def gvfg_ibn_year(commissioning_planned: int | None, commissioning_actual: int | None) -> int | None:
    """The commissioning year a GVFG Vorhaben states: "Inbetriebnahme tats."
    (in the editions often a future year, i.e. the current expectation), else
    "Inbetriebnahme gepl."."""

    return commissioning_actual if commissioning_actual is not None else commissioning_planned


def gvfg_entry_to_specs(
    *,
    gvfg_entry_id: int,
    edition: str,
    stand: date,
    lph: str | None,
    construction_start: int | None,
    commissioning_planned: int | None,
    commissioning_actual: int | None,
) -> list[DerivedSpec]:
    """Derived specs for one Vorhaben of the newest GVFG edition (trust 0.75,
    observed on the edition's Stand).

    - MAIN: the strongest of "Inbetriebnahme tats." before the Stand year →
      IN_BETRIEB, the Lph (:func:`gvfg_lph_main_phase`) and a Baubeginn up to
      the Stand year → BAU. One observation only: several with the same weight
      would let the weaker phase win on a tie of dates.
    - Expected IN_BETRIEB at 31 Dec of :func:`gvfg_ibn_year` when that year is
      not before the Stand year (earlier years are Restarbeiten).
    """

    label = f"GVFG {edition}"
    stand_year = stand.year
    reasons: list[tuple[MainPhase, str]] = []
    if commissioning_actual is not None and commissioning_actual < stand_year:
        reasons.append((MainPhase.IN_BETRIEB, f"Inbetriebnahme {commissioning_actual}"))
    lph_phase = gvfg_lph_main_phase(lph)
    if lph_phase is not None:
        reasons.append((lph_phase, f"Lph {lph.strip()}"))
    if construction_start is not None and construction_start <= stand_year:
        reasons.append((MainPhase.BAU, f"Baubeginn {construction_start}"))

    specs: list[DerivedSpec] = []
    phase = max((p for p, _ in reasons), key=lambda p: p.order, default=None)
    if phase is not None:
        specs.append(
            DerivedSpec(
                source_type=SourceType.GVFG,
                track=ObservationTrack.MAIN,
                asserted_state=phase.value,
                observed_date=stand,
                note=f"{label}: " + ", ".join(text for _, text in reasons),
                gvfg_entry_id=gvfg_entry_id,
            )
        )
    ibn_year = gvfg_ibn_year(commissioning_planned, commissioning_actual)
    if phase is not MainPhase.IN_BETRIEB and ibn_year is not None and ibn_year >= stand_year:
        specs.append(
            DerivedSpec(
                source_type=SourceType.GVFG,
                track=ObservationTrack.MAIN,
                asserted_state=MainPhase.IN_BETRIEB.value,
                observed_date=commissioning_in_year(ibn_year)[0],
                note=f"{label}: geplante Inbetriebnahme {ibn_year}",
                gvfg_entry_id=gvfg_entry_id,
                is_expected=True,
                # Only the year is printed: the Fahrplanwechsel, shown as 12/YYYY.
                date_precision=commissioning_in_year(ibn_year)[1],
            )
        )
    return specs
