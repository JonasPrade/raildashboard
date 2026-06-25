"""Unit tests for the pure VIB/FinVe → derived-observation mapping and the
tolerant date parser."""

from __future__ import annotations

from datetime import date

import pytest

from dashboard_backend.models.projects.progress_enums import (
    MainPhase,
    ObservationTrack,
    ParallelState,
    SourceType,
)
from dashboard_backend.services.progress_dates import parse_flexible_date
from dashboard_backend.services.progress_materialization import (
    SAMMEL_FINVE_CONFIDENCE,
    PfaInput,
    finve_to_spec,
    parse_sammel_finve_phase,
    pfa_has_pf_evidence,
    pfa_to_specs,
    vib_entry_to_specs,
)


# --- Date parsing ------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("01.03.2024", date(2024, 3, 1)),
        ("1.3.2024", date(2024, 3, 1)),
        ("2024-03-15", date(2024, 3, 15)),
        ("12/2024", date(2024, 12, 15)),
        ("03.2024", date(2024, 3, 15)),
        ("2. Quartal 2025", date(2025, 5, 15)),
        ("Q3 2025", date(2025, 8, 15)),
        ("März 2024", date(2024, 3, 15)),
        ("Mitte 2026", date(2026, 7, 15)),
        ("Ende 2027", date(2027, 12, 15)),
        ("voraussichtlich 2025", date(2025, 7, 1)),
        ("ca. 2026", date(2026, 7, 1)),
        ("2024-2026", date(2024, 7, 1)),  # range → earliest
    ],
)
def test_parse_flexible_date(text, expected):
    assert parse_flexible_date(text) == expected


@pytest.mark.parametrize("text", [None, "", "-", "offen", "unbekannt", "n/a", "demnächst"])
def test_parse_flexible_date_unparseable(text):
    assert parse_flexible_date(text) is None


# --- VIB mapping -------------------------------------------------------------


def test_vib_status_maps_to_strongest_main_phase():
    specs = vib_entry_to_specs(
        vib_entry_id=7,
        status_planung=True,
        status_bau=True,
        status_abgeschlossen=False,
        observed_date=date(2023, 12, 31),
        has_planfeststellung_flag=False,
        pfas=[],
    )
    main = [s for s in specs if s.track is ObservationTrack.MAIN]
    assert len(main) == 1
    assert main[0].asserted_state == MainPhase.BAU.value
    assert main[0].source_type is SourceType.VIB
    assert main[0].vib_entry_id == 7


def test_vib_no_status_yields_no_main_spec():
    specs = vib_entry_to_specs(
        vib_entry_id=7,
        status_planung=False,
        status_bau=False,
        status_abgeschlossen=False,
        observed_date=date(2023, 12, 31),
        has_planfeststellung_flag=False,
        pfas=[],
    )
    assert all(s.track is not ObservationTrack.MAIN for s in specs)


def test_vib_pfa_with_pfb_date_is_abgeschlossen():
    specs = vib_entry_to_specs(
        vib_entry_id=7,
        status_planung=True,
        status_bau=False,
        status_abgeschlossen=False,
        observed_date=date(2023, 12, 31),
        has_planfeststellung_flag=False,
        pfas=[PfaInput(id=1, nr_pfa="PFA 1", datum_pfb="03/2022")],
    )
    pf = [s for s in specs if s.track is ObservationTrack.PF]
    assert len(pf) == 1
    assert pf[0].asserted_state == ParallelState.ABGESCHLOSSEN.value
    assert pf[0].vib_pfa_entry_id == 1


def test_vib_pfa_without_pfb_date_is_laeuft():
    specs = vib_entry_to_specs(
        vib_entry_id=7,
        status_planung=True,
        status_bau=False,
        status_abgeschlossen=False,
        observed_date=date(2023, 12, 31),
        has_planfeststellung_flag=False,
        pfas=[PfaInput(id=2, nr_pfa="PFA 2", datum_pfb="offen")],
    )
    pf = [s for s in specs if s.track is ObservationTrack.PF]
    assert pf[0].asserted_state == ParallelState.LAEUFT.value


def test_vib_emit_main_false_suppresses_main_keeps_pf():
    # Once sections are split out to subprojects, the flattened entry MAIN is
    # suppressed but the PF track of unassigned sections still renders.
    specs = vib_entry_to_specs(
        vib_entry_id=7,
        status_planung=True,
        status_bau=True,
        status_abgeschlossen=True,
        observed_date=date(2023, 12, 31),
        has_planfeststellung_flag=False,
        pfas=[PfaInput(id=1, nr_pfa="PFA 1", datum_pfb="03/2022")],
        emit_main=False,
    )
    assert all(s.track is not ObservationTrack.MAIN for s in specs)
    pf = [s for s in specs if s.track is ObservationTrack.PF]
    assert len(pf) == 1
    assert pf[0].asserted_state == ParallelState.ABGESCHLOSSEN.value


# --- Per-PFA → subproject MAIN derivation ------------------------------------


def test_pfa_inbetriebnahme_maps_to_in_betrieb():
    specs = pfa_to_specs(
        pfa=PfaInput(
            id=1, nr_pfa="PFA 1", datum_pfb="2018", baubeginn="2019", inbetriebnahme="06/2022"
        ),
        vib_entry_id=7,
        observed_fallback=date(2023, 12, 31),
    )
    main = [s for s in specs if s.track is ObservationTrack.MAIN]
    assert len(main) == 1
    assert main[0].asserted_state == MainPhase.IN_BETRIEB.value
    assert main[0].observed_date == date(2022, 6, 15)  # the milestone date, not the fallback
    assert main[0].vib_pfa_entry_id == 1


def test_pfa_baubeginn_maps_to_bau():
    specs = pfa_to_specs(
        pfa=PfaInput(id=2, nr_pfa="PFA 2", datum_pfb="2018", baubeginn="2020"),
        vib_entry_id=7,
        observed_fallback=date(2023, 12, 31),
    )
    main = [s for s in specs if s.track is ObservationTrack.MAIN]
    assert main[0].asserted_state == MainPhase.BAU.value


def test_pfa_only_pfb_maps_to_genehmigungsplanung_and_pf_abgeschlossen():
    specs = pfa_to_specs(
        pfa=PfaInput(id=3, nr_pfa="PFA 3", datum_pfb="01.03.2021"),
        vib_entry_id=7,
        observed_fallback=date(2023, 12, 31),
    )
    main = [s for s in specs if s.track is ObservationTrack.MAIN]
    assert main[0].asserted_state == MainPhase.GENEHMIGUNGSPLANUNG.value
    pf = [s for s in specs if s.track is ObservationTrack.PF]
    assert pf[0].asserted_state == ParallelState.ABGESCHLOSSEN.value


def test_pfa_without_dates_yields_no_main_but_pf_laeuft():
    specs = pfa_to_specs(
        pfa=PfaInput(id=4, nr_pfa="PFA 4"),
        vib_entry_id=7,
        observed_fallback=date(2023, 12, 31),
    )
    assert all(s.track is not ObservationTrack.MAIN for s in specs)
    pf = [s for s in specs if s.track is ObservationTrack.PF]
    assert pf[0].asserted_state == ParallelState.LAEUFT.value


def test_pfa_has_pf_evidence():
    assert pfa_has_pf_evidence([PfaInput(id=1, nr_pfa="PFA 1")]) is True
    assert pfa_has_pf_evidence([PfaInput(id=1, datum_pfb="2020")]) is True
    assert pfa_has_pf_evidence([PfaInput(id=1)]) is False
    assert pfa_has_pf_evidence([]) is False


# --- FinVe mapping -----------------------------------------------------------


def test_regular_finve_maps_to_bau():
    spec = finve_to_spec(finve_id=3, is_sammel=False, starting_year=2020, name="FinVe 763")
    assert spec is not None
    assert spec.asserted_state == MainPhase.BAU.value
    assert spec.source_type is SourceType.FINVE
    assert spec.observed_date == date(2020, 1, 1)
    assert spec.confidence is None  # uses source default


@pytest.mark.parametrize(
    "name,expected",
    [
        ("SV Lph. 1/2 A", MainPhase.VORPLANUNG),
        ("SV Lph. 1/2 B", MainPhase.VORPLANUNG),
        ("SV Lph. 3/ 4", MainPhase.GENEHMIGUNGSPLANUNG),
        ("SV 3/2010 (EKrG)", None),  # EKrG numbering, NOT Leistungsphase 3
        ("SV 740 m-Netz", None),
        ("SV KV-Kleinmaßnahmen", None),
        (None, None),
    ],
)
def test_parse_sammel_finve_phase(name, expected):
    assert parse_sammel_finve_phase(name) is expected


def test_sammel_lph_1_2_maps_to_vorplanung():
    spec = finve_to_spec(finve_id=763, is_sammel=True, starting_year=2012, name="SV Lph. 1/2 A")
    assert spec is not None
    assert spec.asserted_state == MainPhase.VORPLANUNG.value
    assert spec.confidence == SAMMEL_FINVE_CONFIDENCE


def test_sammel_lph_3_4_maps_to_genehmigungsplanung():
    spec = finve_to_spec(finve_id=5, is_sammel=True, starting_year=None, name="SV Lph. 3/ 4")
    assert spec is not None
    assert spec.asserted_state == MainPhase.GENEHMIGUNGSPLANUNG.value


def test_ambiguous_sammel_finve_yields_no_spec():
    # No Leistungsphase parseable and no manual assignment → skipped.
    spec = finve_to_spec(finve_id=6, is_sammel=True, starting_year=None, name="SV 3/2010 (EKrG)")
    assert spec is None


def test_manual_phase_overrides_ambiguous_sammel():
    spec = finve_to_spec(
        finve_id=6,
        is_sammel=True,
        starting_year=None,
        name="SV 3/2010 (EKrG)",
        manual_phase=MainPhase.BAU,
    )
    assert spec is not None
    assert spec.asserted_state == MainPhase.BAU.value
    assert spec.confidence == SAMMEL_FINVE_CONFIDENCE
