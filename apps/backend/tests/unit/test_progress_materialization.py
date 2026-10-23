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
from dashboard_backend.models.projects.progress_enums import DatePrecision
from dashboard_backend.services.progress_dates import parse_flexible_date, read_milestone
from dashboard_backend.services.progress_materialization import (
    SAMMEL_FINVE_CONFIDENCE,
    PfaInput,
    finve_to_spec,
    parse_sammel_finve_phase,
    assigned_pfas_to_specs,
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
    specs = assigned_pfas_to_specs(
        pfas=[PfaInput(
            id=1, nr_pfa="PFA 1", datum_pfb="2018", baubeginn="2019", inbetriebnahme="06/2022"
        )],
        vib_entry_id=7,
        observed_fallback=date(2023, 12, 31),
    )
    main = [s for s in specs if s.track is ObservationTrack.MAIN]
    assert len(main) == 1
    assert main[0].asserted_state == MainPhase.IN_BETRIEB.value
    assert main[0].observed_date == date(2022, 6, 15)  # the milestone date, not the fallback
    assert main[0].vib_pfa_entry_id == 1


def test_pfa_baubeginn_maps_to_bau():
    specs = assigned_pfas_to_specs(
        pfas=[PfaInput(id=2, nr_pfa="PFA 2", datum_pfb="2018", baubeginn="2020")],
        vib_entry_id=7,
        observed_fallback=date(2023, 12, 31),
    )
    main = [s for s in specs if s.track is ObservationTrack.MAIN]
    assert main[0].asserted_state == MainPhase.BAU.value


def test_pfa_only_pfb_maps_to_genehmigungsplanung_and_pf_abgeschlossen():
    specs = assigned_pfas_to_specs(
        pfas=[PfaInput(id=3, nr_pfa="PFA 3", datum_pfb="01.03.2021")],
        vib_entry_id=7,
        observed_fallback=date(2023, 12, 31),
    )
    main = [s for s in specs if s.track is ObservationTrack.MAIN]
    assert main[0].asserted_state == MainPhase.GENEHMIGUNGSPLANUNG.value
    pf = [s for s in specs if s.track is ObservationTrack.PF]
    assert pf[0].asserted_state == ParallelState.ABGESCHLOSSEN.value


def test_pfa_without_dates_yields_no_main_but_pf_laeuft():
    specs = assigned_pfas_to_specs(
        pfas=[PfaInput(id=4, nr_pfa="PFA 4")],
        vib_entry_id=7,
        observed_fallback=date(2023, 12, 31),
    )
    assert all(s.track is not ObservationTrack.MAIN for s in specs)
    pf = [s for s in specs if s.track is ObservationTrack.PF]
    assert pf[0].asserted_state == ParallelState.LAEUFT.value


# --- Fact vs. prognosis (real cells of the VIB 2024 PFA tables) --------------

VIB_2024_END = date(2024, 12, 31)


@pytest.mark.parametrize(
    "text,expected",
    [
        # Hedged: a prognosis, whatever the date.
        ("vsl. 2027", True),
        ("vsl 2035", True),
        ("vsl.2026", True),
        ("vsl. 12/2025", True),
        ("vsl. 10/2025", True),
        ("offen vsl. 2028", True),
        ("vsl. offen 2029", True),
        ("Hauptverkehrlich vsl. 2030\nGesamtfertigstellung vsl. 2032", True),
        ("voraussichtlich 2024", True),
        ("ca. 2024", True),
        ("geplant 2023", True),
        ("nach 2031", True),
        ("ab 2032", True),
        ("frühestens 07/2032", True),
        # Unhedged but after the report's year-end.
        ("2027", True),
        ("03/2025", True),
        # Reached by the year-end.
        ("07/2024", False),
        ("12/2024", False),
        ("11/2024", False),
        ("29.09.2019", False),
        ("2002¹", False),
        ("30.09.2008 (bvM)", False),
        ("StA 2: 29.12.1997\nStA 3: 13.12.1988", False),
        ("10.01.1998 für Tunnel (rechtskräftig); Planfeststellungsbeschluss 19.11.2012", False),
    ],
)
def test_read_milestone_fact_or_prognosis(text, expected):
    milestone = read_milestone(text, VIB_2024_END)
    assert milestone is not None
    assert milestone.is_expected is expected


@pytest.mark.parametrize("text", [None, "", "offen", "-", "vsl. 20256"])
def test_read_milestone_states_nothing(text):
    assert read_milestone(text, VIB_2024_END) is None


def test_read_milestone_erfolgt_is_an_undated_fact():
    milestone = read_milestone("erfolgt", VIB_2024_END)
    assert milestone is not None
    assert milestone.value is None
    assert milestone.is_expected is False


def test_read_milestone_commissioning_year_is_fahrplanwechsel():
    milestone = read_milestone("vsl. 2027", VIB_2024_END, commissioning=True)
    assert milestone.value == date(2027, 12, 31)
    assert milestone.precision is DatePrecision.MONTH


def _main(specs, *, expected=False):
    return [s for s in specs if s.track is ObservationTrack.MAIN and s.is_expected is expected]


def test_regression_baubeginn_reached_ibn_vsl_is_bau_with_expected_ibn():
    """Baubeginn 03/2021, IBN „vsl. 2027“ → BAU since 03/2021, IBN expected
    (was: IN_BETRIEB on 2027-07-01)."""

    specs = assigned_pfas_to_specs(
        pfas=[PfaInput(id=1, nr_pfa="2.1.2.2", datum_pfb="02.12.2020", baubeginn="03/2021", inbetriebnahme="vsl. 2027")],
        vib_entry_id=7,
        observed_fallback=VIB_2024_END,
    )
    (main,) = _main(specs)
    assert main.asserted_state == MainPhase.BAU.value
    assert main.observed_date == date(2021, 3, 15)
    (ibn,) = _main(specs, expected=True)
    assert ibn.asserted_state == MainPhase.IN_BETRIEB.value
    assert ibn.observed_date == date(2027, 12, 31)
    assert ibn.date_precision is DatePrecision.MONTH
    pf = [s for s in specs if s.track is ObservationTrack.PF]
    assert pf[0].asserted_state == ParallelState.ABGESCHLOSSEN.value


def test_only_prognoses_yield_no_phase_but_expected_bau_and_ibn():
    # Karlsruhe–Basel PFA 7.1 (NBS), VIB 2024.
    specs = assigned_pfas_to_specs(
        pfas=[PfaInput(id=863, nr_pfa="7.1", datum_pfb="vsl. 2027", baubeginn="vsl. 2028", inbetriebnahme="vsl. 2035")],
        vib_entry_id=116,
        observed_fallback=VIB_2024_END,
    )
    assert _main(specs) == []
    expected = {s.asserted_state: s.observed_date for s in _main(specs, expected=True)}
    assert expected == {
        MainPhase.BAU.value: date(2028, 7, 1),
        MainPhase.IN_BETRIEB.value: date(2035, 12, 31),
    }
    (pf,) = [s for s in specs if s.track is ObservationTrack.PF]
    assert pf.asserted_state == ParallelState.LAEUFT.value
    assert "vsl. 2027" in pf.note


def test_unhedged_date_after_the_report_is_expected():
    specs = assigned_pfas_to_specs(
        pfas=[PfaInput(id=1, nr_pfa="1", datum_pfb="2023", baubeginn="2024", inbetriebnahme="2026")],
        vib_entry_id=7,
        observed_fallback=VIB_2024_END,
    )
    (main,) = _main(specs)
    assert main.asserted_state == MainPhase.BAU.value
    (ibn,) = _main(specs, expected=True)
    assert ibn.observed_date == date(2026, 12, 31)


def test_vsl_pfb_keeps_pf_track_running():
    specs = vib_entry_to_specs(
        vib_entry_id=7,
        status_planung=True,
        status_bau=False,
        status_abgeschlossen=False,
        observed_date=VIB_2024_END,
        has_planfeststellung_flag=False,
        pfas=[
            PfaInput(id=1, nr_pfa="8.0", datum_pfb="vsl. 2025"),
            PfaInput(id=2, nr_pfa="8.1", datum_pfb="28.12.2023"),
            PfaInput(id=3, nr_pfa="1.1.11", datum_pfb="erfolgt"),
        ],
    )
    pf = {s.vib_pfa_entry_id: s.asserted_state for s in specs if s.track is ObservationTrack.PF}
    assert pf == {
        1: ParallelState.LAEUFT.value,
        2: ParallelState.ABGESCHLOSSEN.value,
        3: ParallelState.ABGESCHLOSSEN.value,
    }


def test_leaf_with_finished_and_building_sections_is_bau():
    """Teilprojekt 2972 Gaschwitz–Crimmitschau (VIB 2024, excerpt): Altenburg
    went into operation in 11/2024, Regis-Breitingen–Treben-Lehma and
    Gößnitz–Crimmitschau are under construction, Werdau and the 4. BA have
    only their PFB → the leaf is BAU, not IN_BETRIEB."""

    pfas = [
        PfaInput(id=1285, nr_pfa="2.1.1.5–2.1.1.6", datum_pfb="06/2014", baubeginn="08/2015", inbetriebnahme="29.09.2019"),
        PfaInput(id=1287, nr_pfa="2.1.1.7", datum_pfb="03/2005", baubeginn="offen", inbetriebnahme="offen"),
        PfaInput(id=1291, nr_pfa="2.1.2.2–2.1.2.5", datum_pfb="02.12.2021", baubeginn="07/2024", inbetriebnahme="vsl. 2027"),
        PfaInput(id=1293, nr_pfa="2.1.3.0", datum_pfb="22.11.2019", baubeginn="04/2021", inbetriebnahme="11/2024"),
        PfaInput(id=1297, nr_pfa="2.2.1.4–2.2.1.5", datum_pfb="30.09.2020", baubeginn="04/2022", inbetriebnahme="vsl. 2027"),
        PfaInput(id=1298, nr_pfa="2.2.1.4–2.2.1.5", datum_pfb="27.05.2021", baubeginn="07/2024", inbetriebnahme="vsl. 2027"),
        PfaInput(id=1300, nr_pfa="2.2.2.1–3.1.3.6", datum_pfb="25.08.2023", baubeginn="vsl. 2025", inbetriebnahme="vsl. 2025"),
    ]
    specs = assigned_pfas_to_specs(pfas=pfas, vib_entry_id=129, observed_fallback=VIB_2024_END)
    (main,) = _main(specs)
    assert main.asserted_state == MainPhase.BAU.value
    assert main.observed_date == date(2024, 7, 15)  # latest Baubeginn among them
    assert main.note == "2.1.2.2–2.1.2.5, 2.2.1.4–2.2.1.5: aus PFA-Terminen (3 von 7 Abschnitten)"
    (ibn,) = _main(specs, expected=True)  # no expected Bau: building already
    assert (ibn.asserted_state, ibn.observed_date) == (MainPhase.IN_BETRIEB.value, date(2027, 12, 31))
    assert len([s for s in specs if s.track is ObservationTrack.PF]) == len(pfas)


def test_leaf_in_operation_only_when_every_section_is():
    specs = assigned_pfas_to_specs(
        pfas=[
            PfaInput(id=882, nr_pfa="9.1", datum_pfb="22.11.2002", baubeginn="09.12.2002", inbetriebnahme="12/2012"),
            PfaInput(id=885, nr_pfa="9.3", datum_pfb="04/2012", baubeginn="04/2012", inbetriebnahme="11/2012"),
        ],
        vib_entry_id=116,
        observed_fallback=VIB_2024_END,
    )
    (main,) = _main(specs)
    assert main.asserted_state == MainPhase.IN_BETRIEB.value
    assert main.observed_date == date(2012, 12, 15)
    assert _main(specs, expected=True) == []

    # Karlsruhe–Basel leaf 2207: 9.0 Müllheim–Auggen still building („vsl. 12/2025“).
    specs = assigned_pfas_to_specs(
        pfas=[
            PfaInput(id=881, nr_pfa="9.0", datum_pfb="16.07.2015", baubeginn="01/2019", inbetriebnahme="vsl. 12/2025"),
            PfaInput(id=882, nr_pfa="9.1", datum_pfb="22.11.2002", baubeginn="09.12.2002", inbetriebnahme="12/2012"),
        ],
        vib_entry_id=116,
        observed_fallback=VIB_2024_END,
    )
    (main,) = _main(specs)
    assert main.asserted_state == MainPhase.BAU.value
    (ibn,) = _main(specs, expected=True)
    assert ibn.observed_date == date(2025, 12, 15)


def test_finished_section_next_to_pure_prognosis_is_no_phase():
    # A section with only „vsl.“ dates keeps the leaf from counting as in operation.
    specs = assigned_pfas_to_specs(
        pfas=[
            PfaInput(id=1, nr_pfa="A", datum_pfb="2010", baubeginn="2011", inbetriebnahme="2014"),
            PfaInput(id=2, nr_pfa="B", datum_pfb="vsl. 2026", baubeginn="vsl. 2028", inbetriebnahme="vsl. 2031"),
        ],
        vib_entry_id=7,
        observed_fallback=VIB_2024_END,
    )
    assert _main(specs) == []
    assert {s.asserted_state for s in _main(specs, expected=True)} == {
        MainPhase.BAU.value,
        MainPhase.IN_BETRIEB.value,
    }


def test_erfolgt_dates_on_the_report_year_end():
    specs = assigned_pfas_to_specs(
        pfas=[PfaInput(id=1251, nr_pfa="1.1.11", datum_pfb="erfolgt", baubeginn="erfolgt", inbetriebnahme="2005")],
        vib_entry_id=129,
        observed_fallback=VIB_2024_END,
    )
    (main,) = _main(specs)
    assert main.asserted_state == MainPhase.IN_BETRIEB.value
    assert main.observed_date == date(2005, 12, 31)

    specs = assigned_pfas_to_specs(
        pfas=[PfaInput(id=9, nr_pfa="X", datum_pfb="erfolgt", baubeginn="erfolgt", inbetriebnahme="offen")],
        vib_entry_id=129,
        observed_fallback=VIB_2024_END,
    )
    (main,) = _main(specs)
    assert (main.asserted_state, main.observed_date) == (MainPhase.BAU.value, VIB_2024_END)


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
