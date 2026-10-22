"""Migration 20261022004: date precision columns (expand only, nothing changed
or deleted; existing observations become EXACT, the HLK group gets 6 months)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20261022004_date_precision.py"
)
_spec = importlib.util.spec_from_file_location("date_precision_migration", _MIGRATION)
migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migration)


def _columns(conn, table):
    return {c["name"] for c in sa.inspect(conn).get_columns(table)}


def _run(conn, step):
    ctx = MigrationContext.configure(conn)
    migration.op = Operations(ctx)  # the module imported ``op`` as a proxy
    step()


def test_upgrade_keeps_existing_rows_exact_and_downgrade_removes_columns():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE progress_observation (id INTEGER PRIMARY KEY, observed_date DATE, note TEXT)"
        )
        conn.exec_driver_sql("CREATE TABLE project_group (id INTEGER PRIMARY KEY, short_name TEXT)")
        conn.exec_driver_sql("CREATE TABLE project_progress (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql(
            "INSERT INTO progress_observation VALUES (1, '2032-01-01', 'Annahme: 6 Monate Bauzeit')"
        )
        conn.exec_driver_sql("INSERT INTO project_group VALUES (1, 'HLK'), (2, 'BSWAG')")

        _run(conn, migration.upgrade)

        row = conn.exec_driver_sql(
            "SELECT observed_date, note, date_precision, date_label FROM progress_observation"
        ).one()
        assert tuple(row) == ("2032-01-01", "Annahme: 6 Monate Bauzeit", "EXACT", None)
        months = dict(
            conn.exec_driver_sql("SELECT short_name, assumed_build_months FROM project_group").all()
        )
        assert months == {"HLK": 6, "BSWAG": None}
        assert {
            "construction_start_date",
            "construction_start_precision",
            "commissioning_date",
            "commissioning_precision",
        } <= _columns(conn, "project_progress")

        _run(conn, migration.downgrade)

        assert _columns(conn, "progress_observation") == {"id", "observed_date", "note"}
        assert _columns(conn, "project_group") == {"id", "short_name"}
        assert _columns(conn, "project_progress") == {"id"}
        assert conn.exec_driver_sql("SELECT count(*) FROM progress_observation").scalar() == 1
