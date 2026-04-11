# dashboard_backend/api/v1/api.py
from fastapi import APIRouter
from .endpoints import auth, operational_points, project_routes, project_texts, route, projects, project_groups, users, tasks, haushalt_import, finves, settings, vib_import, admin_assignments

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(operational_points.router, prefix="/operational-points", tags=["operational-points"])
api_router.include_router(route.router, prefix="/route", tags=["route"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(project_groups.router, prefix="/project_groups", tags=["project_groups"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(project_routes.router, tags=["routes"])
api_router.include_router(project_texts.router, tags=["texts"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(haushalt_import.router, prefix="/import/haushalt", tags=["haushalt-import"])
api_router.include_router(finves.router, prefix="/finves", tags=["finves"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(vib_import.router, prefix="/import/vib", tags=["vib-import"])
api_router.include_router(admin_assignments.router, prefix="/admin", tags=["admin-assignments"])
