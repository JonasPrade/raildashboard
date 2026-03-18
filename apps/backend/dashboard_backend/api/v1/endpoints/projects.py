from __future__ import annotations

import json

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from dashboard_backend.core.security import require_roles
from dashboard_backend.crud.changelog import (
    create_changelog_for_patch,
    get_changelog_entry,
    get_project_changelog,
)
from dashboard_backend.crud.projects.bvwp import get_bvwp_data
from dashboard_backend.crud.projects.projects import get_project_by_id, get_projects, update_project
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.changelog import ChangeLogRead, RevertFieldRequest
from dashboard_backend.schemas.projects import ProjectSchema
from dashboard_backend.schemas.projects.project_schema import BudgetSummarySchema, FinveWithBudgetsSchema, TitelEntrySchema
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.budget import Budget
from dashboard_backend.models.haushalt.budget_titel_entry import BudgetTitelEntry
from dashboard_backend.schemas.projects.bvwp_schema import BvwpProjectDataSchema
from dashboard_backend.schemas.projects.project_update_schema import ProjectUpdate
from dashboard_backend.schemas.users import UserRole

router = AuthRouter()


@router.get("/", response_model=list[ProjectSchema])
def read_all_projects(db: Session = Depends(get_db)):
    """Retrieve all projects."""
    return get_projects(db)


@router.get("/{project_id}", response_model=ProjectSchema)
def read_project(project_id: int, db: Session = Depends(get_db)):
    """Retrieve a single project by ID."""
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/bvwp", response_model=BvwpProjectDataSchema)
def get_project_bvwp(project_id: int, db: Session = Depends(get_db)):
    """Return BVWP assessment data for a project. Returns 404 if no BVWP data exists."""
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    bvwp = get_bvwp_data(db, project_id)
    if not bvwp:
        raise HTTPException(status_code=404, detail="No BVWP data for this project")
    return bvwp


@router.patch("/{project_id}", response_model=ProjectSchema)
def patch_project(
    project_id: int,
    body: ProjectUpdate,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Update project fields. All changed fields are recorded in the changelog."""
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return project

    # Record before/after values in changelog (committed together with the update below)
    create_changelog_for_patch(db, project, update_data, current_user.id, current_user.username)
    return update_project(db, project_id, update_data)


@router.get("/{project_id}/finves", response_model=list[FinveWithBudgetsSchema])
def get_project_finves(project_id: int, db: Session = Depends(get_db)):
    """Return all FinVes linked to a project, each with their full budget history
    including per-Haushaltstiteln breakdown."""
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    finve_ids = [f.id for f in project.finve]
    if not finve_ids:
        return []

    # Eager-load budgets → titel_entries → titel in one query
    finves = (
        db.query(Finve)
        .filter(Finve.id.in_(finve_ids))
        .options(
            joinedload(Finve.budgets).joinedload(Budget.titel_entries).joinedload(BudgetTitelEntry.titel)
        )
        .all()
    )

    result = []
    for finve in finves:
        budgets_sorted = sorted(finve.budgets, key=lambda b: b.budget_year)
        budget_schemas = []
        for b in budgets_sorted:
            titel_schemas = [TitelEntrySchema.from_entry(e) for e in b.titel_entries]
            budget_schemas.append(
                BudgetSummarySchema(
                    budget_year=b.budget_year,
                    lfd_nr=b.lfd_nr,
                    bedarfsplan_number=b.bedarfsplan_number,
                    cost_estimate_original=b.cost_estimate_original,
                    cost_estimate_last_year=b.cost_estimate_last_year,
                    cost_estimate_actual=b.cost_estimate_actual,
                    delta_previous_year=b.delta_previous_year,
                    delta_previous_year_relativ=b.delta_previous_year_relativ,
                    spent_two_years_previous=b.spent_two_years_previous,
                    allowed_previous_year=b.allowed_previous_year,
                    spending_residues=b.spending_residues,
                    year_planned=b.year_planned,
                    next_years=b.next_years,
                    titel_entries=titel_schemas,
                )
            )
        result.append(
            FinveWithBudgetsSchema(
                id=finve.id,
                name=finve.name,
                starting_year=finve.starting_year,
                cost_estimate_original=finve.cost_estimate_original,
                is_sammel_finve=finve.is_sammel_finve,
                budgets=budget_schemas,
            )
        )
    return result


@router.get("/{project_id}/changelog", response_model=list[ChangeLogRead])
def read_project_changelog(
    project_id: int,
    current_user: User = Depends(require_roles()),
    db: Session = Depends(get_db),
):
    """Return the full changelog for a project, newest entries first."""
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return get_project_changelog(db, project_id)


@router.post("/{project_id}/changelog/revert", response_model=ProjectSchema)
def revert_project_field(
    project_id: int,
    body: RevertFieldRequest,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Revert a single field to its previous value as recorded in the given ChangeLogEntry."""
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    entry = get_changelog_entry(db, body.changelog_entry_id, project_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Changelog entry not found")

    field_name = entry.field_name
    if field_name not in ProjectUpdate.model_fields.keys():
        raise HTTPException(status_code=400, detail=f"Unknown field: {field_name}")

    # Parse stored JSON value back to the original Python type
    target_value = json.loads(entry.old_value) if entry.old_value is not None else None

    # Record the revert action in the changelog before applying it
    create_changelog_for_patch(
        db,
        project,
        {field_name: target_value},
        current_user.id,
        current_user.username,
        action="REVERT",
    )
    return update_project(db, project_id, {field_name: target_value})
