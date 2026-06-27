"""Unit tests for the DB-Bauportal importer (#47): status mapping, fuzzy
matching and the upsert logic — all DB-free (no live network)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from dashboard_backend.models.projects.bauportal_status import BauportalStatus
from dashboard_backend.models.projects.project import Project
from dashboard_backend.services.progress_materialization import (
    bauportal_status_to_main_phase,
    bauportal_to_spec,
)
from dashboard_backend.tasks.bauportal import import_bauportal
from dashboard_backend.tasks.vib_matching import suggest_project_for_bauportal

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "bauportal_sample.json"


@dataclass
class FakeProject:
    id: int
    name: str


# --- status → phase mapping --------------------------------------------------


def test_status_bauphase_maps_to_bau():
    assert bauportal_status_to_main_phase("Projekt in der Bauphase").value == "BAU"


def test_status_planungsphase_maps_to_vorplanung():
    assert (
        bauportal_status_to_main_phase("Projekt in der Planungsphase").value
        == "VORPLANUNG"
    )


def test_status_mixed_and_umbrella_have_no_phase():
    assert bauportal_status_to_main_phase("Projekt in gemischter Projektphase") is None
    assert bauportal_status_to_main_phase("Gesamtprojekt in der Bauphase") is None
    assert bauportal_status_to_main_phase(None) is None
    assert bauportal_status_to_main_phase("") is None


def test_to_spec_carries_provenance_and_note():
    spec = bauportal_to_spec(
        bauportal_status_id=7,
        status_raw="Projekt in der Bauphase",
        projecttime_raw="2025 – 2027",
        observed_date=None,
    )
    assert spec is not None
    assert spec.source_type.value == "BAUPORTAL"
    assert spec.track.value == "MAIN"
    assert spec.asserted_state == "BAU"
    assert spec.bauportal_status_id == 7
    assert spec.confidence is None  # source default 0.8 applies downstream
    assert "2025 – 2027" in spec.note


def test_to_spec_returns_none_for_mixed():
    assert (
        bauportal_to_spec(
            bauportal_status_id=1,
            status_raw="Projekt in gemischter Projektphase",
            projecttime_raw=None,
            observed_date=None,
        )
        is None
    )


# --- fuzzy matching ----------------------------------------------------------


def test_suggest_matches_close_name():
    projects = [
        FakeProject(1, "Ausbau Hanau–Würzburg/Fulda"),
        FakeProject(2, "740 Meter-Netz – Röblingen am See Bahnhof"),
    ]
    assert suggest_project_for_bauportal("740 Meter-Netz – Röblingen am See Bahnhof", projects) == 2


def test_suggest_returns_none_below_threshold():
    projects = [FakeProject(1, "Völlig anderes Projekt XYZ")]
    assert suggest_project_for_bauportal("740 Meter-Netz – Münster", projects) is None
    assert suggest_project_for_bauportal("", projects) is None


# --- upsert logic (fake session, fixture records) ----------------------------


class _FakeQuery:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _FakeSession:
    """Minimal Session stand-in covering only what import_bauportal uses."""

    def __init__(self, projects, existing):
        self._projects = projects
        self._existing = existing
        self.added: list = []
        self.commits = 0

    def query(self, model):
        if model is Project:
            return _FakeQuery(self._projects)
        if model is BauportalStatus:
            return _FakeQuery(self._existing)
        return _FakeQuery([])

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1


def _records():
    return json.loads(FIXTURE.read_text())


def test_import_creates_rows_and_suggestions():
    records = _records()
    # one project whose name matches a fixture entry exactly
    target = next(r for r in records if r["icon_title"] == "Projekt in der Bauphase")
    projects = [FakeProject(99, target["shorttitle"])]
    db = _FakeSession(projects=projects, existing=[])

    summary = import_bauportal(db, records=records)

    assert summary["fetched"] == len(records)
    assert summary["created"] == len(records)
    assert summary["updated"] == 0
    assert len(db.added) == len(records)
    assert db.commits == 1

    matched = next(r for r in db.added if r.bauportal_id == target["id"])
    assert matched.suggested_project_id == 99
    assert matched.status_raw == "Projekt in der Bauphase"
    assert matched.project_id is None  # suggestion only, not confirmed


def test_import_updates_existing_and_preserves_confirmed_match():
    records = _records()
    first = records[0]
    existing_row = BauportalStatus(
        bauportal_id=first["id"],
        shorttitle="old title",
        project_id=42,            # already confirmed by an editor
        suggested_project_id=7,
    )
    db = _FakeSession(projects=[], existing=[existing_row])

    summary = import_bauportal(db, records=records)

    assert summary["updated"] == 1
    assert summary["created"] == len(records) - 1
    # confirmed match must survive re-import; suggestion not overwritten while confirmed
    assert existing_row.project_id == 42
    assert existing_row.suggested_project_id == 7
    assert existing_row.shorttitle == first["shorttitle"]  # raw fields refreshed


def test_import_skips_records_without_id_or_title():
    records = [
        {"id": None, "shorttitle": "no id"},
        {"id": 5, "shorttitle": ""},
        {"id": 6, "shorttitle": "Valid", "icon_title": "Projekt in der Bauphase"},
    ]
    db = _FakeSession(projects=[], existing=[])
    summary = import_bauportal(db, records=records)
    assert summary["skipped"] == 2
    assert summary["created"] == 1
