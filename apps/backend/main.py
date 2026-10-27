# main.py
import threading
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from starlette.middleware.gzip import GZipMiddleware
from starlette.routing import Route

from dashboard_backend.api.v1.api import api_router
from dashboard_backend.api.v1.endpoints.health import readiness_router
from dashboard_backend.core.config import settings
from dashboard_backend.database import get_db
from dashboard_backend.dependencies.routes import get_route_service
from dashboard_backend.mcp.server import MCP_PATH, McpEndpoint


@contextmanager
def _mcp_session() -> Iterator[Session]:
    # Resolved per call so test overrides of get_db reach the MCP tools too.
    yield from app.dependency_overrides.get(get_db, get_db)()


def _mcp_route_service():
    # Same per-call resolution as above, so tests can stub the routing service.
    return app.dependency_overrides.get(get_route_service, get_route_service)()


mcp_endpoint = McpEndpoint(_mcp_session, _mcp_route_service) if settings.mcp_enabled else None


def _start_background_jobs() -> None:
    # Initial fill of the map overlaps after the deploy that adds the tables
    # (docs/features/feature-map-overlapping-geometries.md). In a thread: the
    # check touches the database and the broker, and the start must not wait.
    from dashboard_backend.tasks.project_overlap import start_initial_fill_if_empty

    threading.Thread(target=start_initial_fill_if_empty, name="overlap-initial-fill", daemon=True).start()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.start_background_jobs:
        _start_background_jobs()
    if mcp_endpoint is None:
        yield
        return
    async with mcp_endpoint.lifespan():
        yield


app = FastAPI(lifespan=lifespan)

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
# Deploy gate at the root, reached through nginx as /healthz (DEPLOY.md).
app.include_router(readiness_router)

if mcp_endpoint is not None:
    # Plain ASGI route (not an APIRoute): stays out of the OpenAPI schema and
    # hands the request to the MCP transport unchanged.
    app.router.routes.append(Route(MCP_PATH, endpoint=mcp_endpoint))
