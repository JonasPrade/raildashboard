"""Data migration 20261022001 corrects the imported GVFG edition 2023 in place."""

from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

from dashboard_backend.models.gvfg import GvfgEntry, GvfgEntryAmount, GvfgProgram
from dashboard_backend.models.projects.project import Project

_PATH = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20261022001_fix_gvfg_2023_parse.py"
_spec = importlib.util.spec_from_file_location("fix_gvfg_2023", _PATH)
migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migration)

_PERIODS = [
    {"label": "1967–2021", "year_from": 1967, "year_to": 2021, "kind": "ausgezahlt"},
    {"label": "1967–2020", "year_from": 1967, "year_to": 2020, "kind": "ausgezahlt"},
    {"label": "2022", "year_from": 2022, "year_to": 2022, "kind": "ausgezahlt"},
    {"label": "vsl. 2022", "year_from": 2022, "year_to": 2022, "kind": "voraussichtlich"},
    {"label": "2023", "year_from": 2023, "year_to": 2023, "kind": "geplant"},
]


def _entry(program, key, lines):
    entry = GvfgEntry(program=program, key=key, key_raw=key, land="x", kind="db", part="finanzrelevant")
    for line_no, (category, aid, periods) in enumerate(lines):
        entry.amounts.append(GvfgEntryAmount(line_no=line_no, category=category, aid_total=aid, periods=periods))
    return entry


def test_fixes_the_2023_edition(db_session):
    project = Project(name="Braunschweig Hbf - BS/Gliesmarode", project_number="03 D 4505_A")
    edition_2023 = GvfgProgram(year_from=2023, year_to=2027, title="2023", periods=_PERIODS)
    edition_2025 = GvfgProgram(year_from=2025, year_to=2029, title="2025", periods=[])
    other = _entry(edition_2023, "02 G 509_A", [("SUM", Decimal("1"), {"1967–2020": "1.00", "2023": "2.00"})])
    mdv = _entry(edition_2023, "16 D 4520_A", [("SUM", None, {"1967–2020": "0.00"}), ("C", None, {})])
    later = _entry(edition_2025, "03 D 4505_A", [])
    later.projects.append(project)
    db_session.add_all([project, edition_2023, edition_2025, other, mdv, later])
    db_session.commit()

    migration.fix_edition(db_session.connection())
    db_session.commit()
    db_session.expire_all()

    program = db_session.get(GvfgProgram, edition_2023.id)
    assert [p["label"] for p in program.periods] == ["1967–2021", "vsl. 2022", "2023"]
    assert db_session.get(GvfgEntry, other.id).amounts[0].periods == {"1967–2021": "1.00", "2023": "2.00"}

    mdv_lines = db_session.get(GvfgEntry, mdv.id).amounts
    assert [(a.category, a.aid_total) for a in mdv_lines] == [
        ("SUM", Decimal("86.25")),
        ("A", Decimal("0.00")),
        ("C", Decimal("86.25")),
    ]

    added = db_session.query(GvfgEntry).filter_by(program_id=edition_2023.id, key="03 D 4505_A").one()
    assert added.key_raw == "03 D 4505 A"
    assert [p.id for p in added.projects] == [project.id]
    assert added.amounts[0].periods["ab 2028"] == "8.63"

    # A second run changes nothing.
    migration.fix_edition(db_session.connection())
    db_session.commit()
    assert db_session.query(GvfgEntry).filter_by(program_id=edition_2023.id, key="03 D 4505_A").count() == 1


def test_without_the_2023_edition_nothing_happens(db_session):
    migration.fix_edition(db_session.connection())
    assert db_session.query(GvfgEntry).count() == 0
