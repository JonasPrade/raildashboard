"""One-off: turn the near-empty projects of the GVFG import 2025–2029 into drafts (#204).

The import used to create projects as final. This marks project ids 2839–2859 as
drafts, but only if each of them still looks like the import left it: linked to a
Vorhaben of the 2025–2029 edition with the same project number, group GVFG, no
changelog entry besides the CREATE, and none of the maintained fields filled.
Any deviation is reported and the project is left alone. Idempotent: projects that
are already drafts are skipped.

Usage:
    python scripts/draft_gvfg_2025_projects.py            # report only
    python scripts/draft_gvfg_2025_projects.py --apply    # write
"""

from __future__ import annotations

import argparse
import sys

from dashboard_backend.crud.changelog import create_changelog_for_patch
from dashboard_backend.database import Session
from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.gvfg import GvfgEntry, GvfgProgram
from dashboard_backend.models.projects.project import Project

PROJECT_IDS = range(2839, 2860)
PROGRAM_YEAR_FROM = 2025
# Fields the import sets; everything else must still be empty/default.
IMPORT_FIELDS = {"id", "name", "project_number", "is_draft"}
USERNAME = "gvfg-draft-correction"  # shown in the project history


def _maintained_fields(project: Project) -> list[str]:
    found = []
    for column in Project.__table__.columns:
        if column.name in IMPORT_FIELDS:
            continue
        value = getattr(project, column.name)
        default = column.default.arg if column.default is not None and column.default.is_scalar else None
        if value in (None, "", False, 0) or value == default:
            continue
        found.append(column.name)
    return found


def check(db, project: Project) -> list[str]:
    """Reasons why *project* is not an untouched import project (empty = fine)."""
    problems = []
    linked = (
        db.query(GvfgEntry)
        .join(GvfgProgram)
        .filter(GvfgProgram.year_from == PROGRAM_YEAR_FROM, GvfgEntry.projects.any(Project.id == project.id))
        .all()
    )
    if not linked:
        problems.append("not linked to a Vorhaben of the 2025–2029 edition")
    elif not any(e.key == project.project_number for e in linked):
        problems.append("project_number differs from the key of its Vorhaben")
    if {g.short_name for g in project.project_groups} - {"GVFG", "GVFG BW"}:
        problems.append("has other project groups")
    if project.superior_project_id is not None or db.query(Project).filter(
        Project.superior_project_id == project.id
    ).count():
        problems.append("is part of a project hierarchy")
    logs = db.query(ChangeLog).filter(ChangeLog.project_id == project.id).all()
    if sorted(log.action for log in logs).count("CREATE") != 1:
        problems.append("changelog has no single CREATE entry")
    # The import itself adds the GVFG group as a PATCH; anything else is maintenance.
    edited = sorted(
        {e.field_name for log in logs if log.action != "CREATE" for e in log.entries} - {"project_group_ids"}
    )
    if edited:
        problems.append("edited since the import: " + ", ".join(edited))
    if fields := _maintained_fields(project):
        problems.append("maintained fields: " + ", ".join(fields))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the change (default: report only)")
    args = parser.parse_args()

    deviations = changed = already = 0
    with Session() as db:
        for pid in PROJECT_IDS:
            project = db.get(Project, pid)
            if project is None:
                print(f"{pid}: not found — skipped")
                deviations += 1
                continue
            if project.is_draft:
                already += 1
                continue
            problems = check(db, project)
            if problems:
                print(f"{pid} {project.name!r}: NOT CHANGED — " + "; ".join(problems))
                deviations += 1
                continue
            print(f"{pid} {project.name!r}: -> draft")
            changed += 1
            if args.apply:
                create_changelog_for_patch(db, project, {"is_draft": True}, None, USERNAME)
                project.is_draft = True
        if args.apply:
            db.commit()
    mode = "applied" if args.apply else "dry run"
    print(f"{mode}: {changed} to draft, {already} already draft, {deviations} deviations")
    return 1 if deviations else 0


if __name__ == "__main__":
    sys.exit(main())
