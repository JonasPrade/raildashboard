# main.py
from fastapi import FastAPI

from dashboard_backend.api.v1.api import api_router

app = FastAPI()
app.include_router(api_router, prefix="/api/v1")
