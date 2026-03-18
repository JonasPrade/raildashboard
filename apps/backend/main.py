# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dashboard_backend.api.v1.api import api_router
from dashboard_backend.core.config import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(api_router, prefix="/api/v1")
