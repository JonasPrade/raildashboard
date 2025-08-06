# dashboard_backend/api/v1/api.py
from fastapi import APIRouter
from .endpoints import route

api_router = APIRouter()
api_router.include_router(route.router, prefix="/route", tags=["route"])
