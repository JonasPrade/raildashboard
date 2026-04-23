from __future__ import annotations

from sqlalchemy.orm import Session

from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.vib.vib_entry import VibEntry
from dashboard_backend.models.vib.vib_entry_project import vib_entry_project
from dashboard_backend.models.vib.vib_report import VibReport
from dashboard_backend.schemas.admin_assignments import (
    UnassignedFinveSchema,
    UnassignedVibEntrySchema,
)


def list_unassigned_finves(db: Session) -> list[UnassignedFinveSchema]:
    """Return FinVes that have no entry in finve_to_project."""
    rows = (
        db.query(Finve)
        .outerjoin(FinveToProject, FinveToProject.finve_id == Finve.id)
        .filter(FinveToProject.id.is_(None))
        .order_by(Finve.id)
        .all()
    )
    return [
        UnassignedFinveSchema(
            id=f.id,
            name=f.name,
            is_sammel_finve=f.is_sammel_finve,
            starting_year=f.starting_year,
        )
        for f in rows
    ]


def list_unassigned_vib_entries(db: Session) -> list[UnassignedVibEntrySchema]:
    """Return VibEntries that have no row in vib_entry_project."""
    rows = (
        db.query(VibEntry, VibReport.year)
        .join(VibReport, VibReport.id == VibEntry.vib_report_id)
        .outerjoin(
            vib_entry_project,
            vib_entry_project.c.vib_entry_id == VibEntry.id,
        )
        .filter(vib_entry_project.c.project_id.is_(None))
        .order_by(VibReport.year.desc(), VibEntry.id)
        .all()
    )
    return [
        UnassignedVibEntrySchema(
            id=entry.id,
            vib_name_raw=entry.vib_name_raw,
            vib_section=entry.vib_section,
            category=entry.category,
            report_year=year,
        )
        for entry, year in rows
    ]


def get_finve(db: Session, finve_id: int) -> Finve | None:
    return db.get(Finve, finve_id)


def get_vib_entry(db: Session, entry_id: int) -> VibEntry | None:
    return db.get(VibEntry, entry_id)


def assign_finve_to_projects(db: Session, finve_id: int, project_ids: list[int]) -> None:
    """Insert finve_to_project rows (haushalt_year=NULL). Skips existing links."""
    for pid in project_ids:
        exists = (
            db.query(FinveToProject)
            .filter(
                FinveToProject.finve_id == finve_id,
                FinveToProject.project_id == pid,
                FinveToProject.haushalt_year.is_(None),
            )
            .first()
        )
        if not exists:
            db.add(FinveToProject(finve_id=finve_id, project_id=pid, haushalt_year=None))
    db.flush()


def link_project_to_finves(db: Session, project_id: int, finve_ids: list[int]) -> None:
    """Link many FinVes to one project in a single batched insert.

    Used by the new-project wizard. Existing (project_id, finve_id, NULL)
    links are preserved.
    """
    if not finve_ids:
        return
    existing = (
        db.query(FinveToProject.finve_id)
        .filter(
            FinveToProject.finve_id.in_(finve_ids),
            FinveToProject.project_id == project_id,
            FinveToProject.haushalt_year.is_(None),
        )
        .all()
    )
    existing_ids = {row[0] for row in existing}
    for finve_id in finve_ids:
        if finve_id not in existing_ids:
            db.add(FinveToProject(finve_id=finve_id, project_id=project_id, haushalt_year=None))


def assign_vib_entry_to_projects(db: Session, entry_id: int, project_ids: list[int]) -> None:
    """Insert vib_entry_project rows. Skips existing links."""
    rows = db.execute(
        vib_entry_project.select().where(
            vib_entry_project.c.vib_entry_id == entry_id
        )
    ).all()
    existing_pids = {row.project_id for row in rows}
    new_rows = [
        {"vib_entry_id": entry_id, "project_id": pid}
        for pid in project_ids
        if pid not in existing_pids
    ]
    if new_rows:
        db.execute(vib_entry_project.insert(), new_rows)
    db.flush()
