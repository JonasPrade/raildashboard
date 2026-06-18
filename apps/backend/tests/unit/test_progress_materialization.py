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
    pfa_has_pf_evidence,
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


def test_pfa_has_pf_evidence():
    assert pfa_has_pf_evidence([PfaInput(id=1, nr_pfa="PFA 1")]) is True
    assert pfa_has_pf_evidence([PfaInput(id=1, datum_pfb="2020")]) is True
    assert pfa_has_pf_evidence([PfaInput(id=1)]) is False
    assert pfa_has_pf_evidence([]) is False


# --- FinVe mapping -----------------------------------------------------------


def test_regular_finve_maps_to_bau():
    spec = finve_to_spec(finve_id=3, is_sammel=False, starting_year=2020)
    assert spec.asserted_state == MainPhase.BAU.value
    assert spec.source_type is SourceType.FINVE
    assert spec.observed_date == date(2020, 1, 1)
    assert spec.confidence is None  # uses source default


def test_sammel_finve_is_weaker():
    spec = finve_to_spec(finve_id=4, is_sammel=True, starting_year=None)
    assert spec.asserted_state == MainPhase.GENEHMIGUNGSPLANUNG.value
    assert spec.confidence == SAMMEL_FINVE_CONFIDENCE
    assert spec.observed_date is None
