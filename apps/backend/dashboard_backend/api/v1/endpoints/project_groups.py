from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dashboard_backend.crud.projects.project_groups import (
    get_project_groups,
    get_project_group_by_id,
    update_project_group,
)
from dashboard_backend.database import get_db
from dashboard_backend.schemas.projects import ProjectGroupSchema
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.core.security import require_roles, UserRole

router = AuthRouter()


class ProjectGroupUpdate(BaseModel):
    is_default_selected: bool


@router.get("/", response_model=list[ProjectGroupSchema])
def read_project_groups(db: Session = Depends(get_db)):
    return get_project_groups(db)


@router.get("/{group_id}")
def read_project_group(group_id: int, db: Session = Depends(get_db)):
    group = get_project_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="ProjectGroup not found")
    return group


@router.patch("/{group_id}", response_model=ProjectGroupSchema)
def patch_project_group(
    group_id: int,
    body: ProjectGroupUpdate,
    _: None = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
):
    group = update_project_group(db, group_id, body.model_dump(exclude_unset=True))
    if not group:
        raise HTTPException(status_code=404, detail="ProjectGroup not found")
    return group
