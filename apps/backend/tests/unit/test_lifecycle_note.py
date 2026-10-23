"""Reason and start date of PAUSIERT / ABGEBROCHEN (feature-project-progress.md →
Lebenszyklus, #261): set with the status, cleared on AKTIV, in the changelog."""

from __future__ import annotations

from datetime import date

import pytest

from dashboard_backend.crud.projects.progress import update_progress
from dashboard_backend.models.change_tracking import ChangeLog, ChangeLogEntry
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_progress import ProjectProgress
from tests.unit.test_progress_aggregation import db, engine  # noqa: F401


@pytest.fixture()
def project(engine, db):  # noqa: F811
    ChangeLog.__table__.create(bind=engine)
    ChangeLogEntry.__table__.create(bind=engine)
    row = Project(name="P")
    db.add(row)
    db.commit()
    return row


def _row(db, pid):  # noqa: F811
    return db.query(ProjectProgress).filter(ProjectProgress.project_id == pid).one()


def test_note_and_date_with_paused(db, project):  # noqa: F811
    update_progress(
        db,
        project.id,
        {"lifecycle_status": "PAUSIERT", "lifecycle_note": "  Finanzierung offen ", "lifecycle_date": date(2026, 1, 1)},
        None,
    )
    row = _row(db, project.id)
    assert (row.lifecycle_note, row.lifecycle_date) == ("Finanzierung offen", date(2026, 1, 1))
    fields = {e.field_name for e in db.query(ChangeLogEntry)}
    assert {"progress.lifecycle_note", "progress.lifecycle_date"} <= fields

    update_progress(db, project.id, {"lifecycle_note": "", "clear_lifecycle_date": True}, None)
    row = _row(db, project.id)
    assert (row.lifecycle_note, row.lifecycle_date) == (None, None)


def test_active_clears_note_and_date(db, project):  # noqa: F811
    update_progress(
        db, project.id, {"lifecycle_status": "ABGEBROCHEN", "lifecycle_note": "x", "lifecycle_date": date(2025, 5, 1)}, None
    )
    update_progress(db, project.id, {"lifecycle_status": "AKTIV"}, None)
    row = _row(db, project.id)
    assert (row.lifecycle_note, row.lifecycle_date) == (None, None)


def test_note_ignored_while_active(db, project):  # noqa: F811
    update_progress(db, project.id, {"lifecycle_note": "zu früh"}, None)
    assert _row(db, project.id).lifecycle_note is None
