from __future__ import annotations

import json

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_roles
from dashboard_backend.crud.changelog import (
    create_changelog_for_patch,
    get_changelog_entry,
    get_project_changelog,
)
from dashboard_backend.crud.projects.projects import get_project_by_id, get_projects, update_project
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.changelog import ChangeLogRead, RevertFieldRequest
from dashboard_backend.schemas.projects import ProjectSchema
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


@router.get("/{project_id}/changelog", response_model=list[ChangeLogRead])
def read_project_changelog(
    project_id: int,
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
    if not hasattr(project, field_name):
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
