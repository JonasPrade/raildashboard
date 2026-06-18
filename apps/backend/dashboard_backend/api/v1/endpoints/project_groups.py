from fastapi import Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from dashboard_backend.crud.projects.project_groups import (
    get_project_groups,
    get_project_group_by_id,
    get_project_group_by_short_name,
    create_project_group,
    update_project_group,
    delete_project_group,
)
from dashboard_backend.database import get_db
from dashboard_backend.schemas.projects import ProjectGroupSchema, ProjectGroupCreate
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.core.security import require_permission

router = AuthRouter()


class ProjectGroupUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    description: Optional[str] = None
    public: Optional[bool] = None
    color: Optional[str] = None
    plot_only_superior_projects: Optional[bool] = None
    is_visible: Optional[bool] = None
    is_default_selected: Optional[bool] = None


@router.get("/", response_model=list[ProjectGroupSchema])
def read_project_groups(db: Session = Depends(get_db)):
    return get_project_groups(db)


@router.get("/{group_id}", response_model=ProjectGroupSchema)
def read_project_group(group_id: int, db: Session = Depends(get_db)):
    group = get_project_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="ProjectGroup not found")
    return group


@router.post("/", response_model=ProjectGroupSchema, status_code=201)
def create_project_group_endpoint(
    body: ProjectGroupCreate,
    _: None = Depends(require_permission("projectgroup.create")),
    db: Session = Depends(get_db),
):
    if get_project_group_by_short_name(db, body.short_name):
        raise HTTPException(status_code=409, detail="short_name already in use")
    return create_project_group(db, body.model_dump())


@router.patch("/{group_id}", response_model=ProjectGroupSchema)
def patch_project_group(
    group_id: int,
    body: ProjectGroupUpdate,
    _: None = Depends(require_permission("projectgroup.edit")),
    db: Session = Depends(get_db),
):
    updates = body.model_dump(exclude_unset=True)

    new_short_name = updates.get("short_name")
    if new_short_name is not None:
        existing = get_project_group_by_short_name(db, new_short_name)
        if existing and existing.id != group_id:
            raise HTTPException(status_code=409, detail="short_name already in use")

    group = update_project_group(db, group_id, updates)
    if not group:
        raise HTTPException(status_code=404, detail="ProjectGroup not found")
    return group


@router.delete("/{group_id}", status_code=204)
def delete_project_group_endpoint(
    group_id: int,
    _: None = Depends(require_permission("projectgroup.edit")),
    db: Session = Depends(get_db),
):
    group = delete_project_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="ProjectGroup not found")
    return None
