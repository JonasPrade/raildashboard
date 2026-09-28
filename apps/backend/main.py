# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

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

# Compress responses in the app itself so it works regardless of the reverse
# proxy in front (the host proxy was measured passing /api/ JSON uncompressed).
# Level 6 is the usual size/CPU sweet spot. The installed Starlette version has
# no exclude_content_types option (it only skips text/event-stream, hardcoded);
# PDFs get gzipped again here at a small CPU cost.
app.add_middleware(
    GZipMiddleware,
    minimum_size=1024,
    compresslevel=6,
)

app.include_router(api_router, prefix="/api/v1")
