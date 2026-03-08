# dashboard_backend/api/v1/api.py
from fastapi import APIRouter
from .endpoints import project_routes, project_texts, route, projects, project_groups, users, tasks, haushalt_import

api_router = APIRouter()
api_router.include_router(route.router, prefix="/route", tags=["route"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(project_groups.router, prefix="/project_groups", tags=["project_groups"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(project_routes.router, tags=["routes"])
api_router.include_router(project_texts.router, tags=["texts"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(haushalt_import.router, prefix="/import/haushalt", tags=["haushalt-import"])

