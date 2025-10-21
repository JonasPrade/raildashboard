from fastapi import APIRouter, Depends, HTTPException
from dashboard_backend.schemas.projects import ProjectSchema
from dashboard_backend.database import get_db
from sqlalchemy.orm import Session
from dashboard_backend.crud.projects.projects import get_projects, get_project_by_id

router = APIRouter()

@router.get("/", response_model=list[ProjectSchema])
def read_all_projects(db: Session = Depends(get_db)):
    """
    Retrieve all projects.
    """
    return get_projects(db)

@router.get("/{project_id}", response_model=ProjectSchema)
def read_project(project_id: int, db: Session = Depends(get_db)):
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
