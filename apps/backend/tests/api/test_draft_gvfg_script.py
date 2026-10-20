"""The one-off correction of the GVFG 2025–2029 import projects (#204)."""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

from dashboard_backend.crud.changelog import create_changelog_for_create, create_changelog_for_patch
from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.gvfg import GvfgEntry, GvfgProgram
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "draft_gvfg_2025_projects.py"
spec = importlib.util.spec_from_file_location("draft_gvfg_2025_projects", SCRIPT)
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


def _import_project(db, group, key, program):
    project = Project(name=f"Vorhaben {key}", project_number=key, is_draft=False)
    project.project_groups = [group]
    db.add(project)
    db.flush()
    create_changelog_for_create(db, project, {"name": project.name, "project_number": key}, None, "imp")
    entry = GvfgEntry(
        program=program, key=key, key_raw=key, land="Hamburg", kind="kommunal", part="finanzrelevant"
    )
    entry.projects.append(project)
    db.add(entry)
    db.commit()
    return project


def test_check_accepts_untouched_and_reports_maintained(db_session):
    group = ProjectGroup(name="GVFG", short_name="GVFG", color="#000")
    program = GvfgProgram(year_from=2025, year_to=2029, title="t", stand=date(2025, 7, 18), periods=[])
    db_session.add_all([group, program])
    db_session.flush()
    clean = _import_project(db_session, group, "02 G 1_A", program)
    edited = _import_project(db_session, group, "02 G 2_A", program)
    create_changelog_for_patch(db_session, edited, {"description": "gepflegt"}, 1, "u")
    edited.description = "gepflegt"
    db_session.commit()

    assert script.check(db_session, clean) == []
    problems = script.check(db_session, edited)
    assert any("description" in p for p in problems)
    assert any("edited since the import" in p for p in problems)

    orphan = Project(name="Ohne Vorhaben", project_number="x", is_draft=False)
    db_session.add(orphan)
    db_session.commit()
    assert any("not linked" in p for p in script.check(db_session, orphan))
    assert db_session.query(ChangeLog).filter_by(project_id=clean.id).count() == 1
