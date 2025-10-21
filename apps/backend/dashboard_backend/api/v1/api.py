# dashboard_backend/api/v1/api.py
from fastapi import APIRouter
from .endpoints import route, projects, project_groups

api_router = APIRouter()
api_router.include_router(route.router, prefix="/route", tags=["route"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(project_groups.router, prefix="/project_groups", tags=["project_groups"])

