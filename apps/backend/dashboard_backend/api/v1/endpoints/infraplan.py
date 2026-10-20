"""Public reads of the confirmed Infraplan years: years, entries of a year,
entries of a project (with cost forecast), checked KPI values.

See docs/features/feature-infraplan-import.md ("Anzeige", "API").
"""

from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from dashboard_backend.crud import infraplan as infraplan_crud
from dashboard_backend.crud.infraplan_import import get_report_by_year
from dashboard_backend.database import get_db
from dashboard_backend.models.projects.project import Project
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.infraplan import (
    InfraplanPublicKpi,
    InfraplanPublicReport,
    InfraplanReportEntrySchema,
    ProjectInfraplanSchema,
)

router = AuthRouter()


@router.get("/reports", response_model=list[InfraplanPublicReport])
def list_reports(db: Session = Depends(get_db)):
    """Confirmed years, newest first."""
    return infraplan_crud.public_reports(db)


@router.get("/reports/{year}/entries", response_model=list[InfraplanReportEntrySchema])
def report_entries(year: int, db: Session = Depends(get_db)):
    """All measures of a year with their projects."""
    report = get_report_by_year(db, year)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Den Infraplan {year} gibt es nicht.")
    return infraplan_crud.report_entries(db, report)


@router.get("/kpis", response_model=list[InfraplanPublicKpi])
def kpis(db: Session = Depends(get_db)):
    """Every KPI with its checked values of all years (unchecked AI values
    stay hidden until the year is approved)."""
    return infraplan_crud.public_kpis(db)


@router.get("/projects/{project_id}", response_model=ProjectInfraplanSchema)
def project_infraplan(project_id: int, db: Session = Depends(get_db)):
    """Infraplan entries of a project across all years, the cost forecast and
    whether the project is missing from the newest year."""
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return infraplan_crud.project_infraplan(db, project_id)
