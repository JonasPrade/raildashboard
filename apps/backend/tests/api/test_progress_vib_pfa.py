"""Materialisation of the PFA rows assigned to a leaf subproject: prognoses
(„vsl. 2027“) are expected milestones, and the sections of one VIB entry
decide the leaf together (regression: Teilprojekt 2972, VIB 2024)."""

from __future__ import annotations

from datetime import date

from dashboard_backend.crud.projects.progress import get_or_create_progress, sync_derived_observations
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.vib.vib_entry import VibEntry
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry
from dashboard_backend.models.vib.vib_report import VibReport


def test_leaf_under_construction_with_vsl_commissioning(client, db_session):
    parent = Project(name="ABS Karlsruhe – Stuttgart – Nürnberg – Leipzig/Dresden")
    db_session.add(parent)
    db_session.flush()
    leaf = Project(name="Gaschwitz–Crimmitschau/Werdau", superior_project_id=parent.id)
    db_session.add(leaf)
    report = VibReport(year=2024)
    db_session.add(report)
    db_session.flush()
    entry = VibEntry(
        vib_report_id=report.id,
        vib_section="B.4.1.5",
        vib_name_raw="Lfd. Vorhaben Nr. 6",
        projects=[parent],
        confirmed=True,
        status_abgeschlossen=True,
    )
    db_session.add(entry)
    db_session.flush()
    db_session.add_all(
        [
            VibPfaEntry(vib_entry_id=entry.id, project_id=leaf.id, nr_pfa="2.1.3.0",
                        datum_pfb="22.11.2019", baubeginn="04/2021", inbetriebnahme="11/2024"),
            VibPfaEntry(vib_entry_id=entry.id, project_id=leaf.id, nr_pfa="2.1.2.2–2.1.2.5",
                        datum_pfb="02.12.2021", baubeginn="07/2024", inbetriebnahme="vsl. 2027"),
            VibPfaEntry(vib_entry_id=entry.id, project_id=leaf.id, nr_pfa="2.2.1.4–2.2.1.5",
                        datum_pfb="30.09.2020", baubeginn="04/2022", inbetriebnahme="vsl. 2027"),
        ]
    )
    db_session.commit()

    sync_derived_observations(db_session, leaf.id)
    db_session.commit()
    rows = (
        db_session.query(ProgressObservation)
        .filter(ProgressObservation.project_id == leaf.id, ProgressObservation.track == "MAIN")
        .all()
    )
    facts = [(o.asserted_state, o.observed_date) for o in rows if not o.is_expected]
    expected = [(o.asserted_state, o.observed_date) for o in rows if o.is_expected]
    assert facts == [("BAU", date(2024, 7, 15))]
    assert expected == [("IN_BETRIEB", date(2027, 12, 31))]

    get_or_create_progress(db_session, leaf.id)
    db_session.commit()
    body = client.get(f"/api/v1/projects/{leaf.id}/progress").json()
    assert body["computed_phase"] == "BAU"
