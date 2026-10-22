"""Fill the cached Baubeginn / Inbetriebnahme of every project.

``project_progress.construction_start_*`` / ``commissioning_*`` (date plus
DatePrecision) are the sort and filter values of the project lists and of
``list_projects`` (docs/features/feature-project-progress.md →
„Datumsqualifikation“). They are refreshed whenever a project's planning state
is read or recomputed; this script fills them for all projects at once — once
after the migration 20261022004, and whenever the lists look stale.

Read-only towards the observations; writes only the four cache columns (and
creates missing ``project_progress`` rows). Idempotent.

Usage:
    python scripts/refresh_progress_dates.py
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import selectinload

from dashboard_backend.crud.projects.progress import refresh_date_cache
from dashboard_backend.database import Session
from dashboard_backend.models.projects.project import Project

BATCH = 100


def main() -> int:
    today = date.today()
    with Session() as db:
        ids = [pid for (pid,) in db.query(Project.id).order_by(Project.id)]
        for start in range(0, len(ids), BATCH):
            projects = (
                db.query(Project)
                .options(selectinload(Project.project_groups))
                .filter(Project.id.in_(ids[start : start + BATCH]))
                .all()
            )
            for project in projects:
                refresh_date_cache(db, project, today)
            db.commit()
        print(f"Termine von {len(ids)} Projekten aktualisiert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
