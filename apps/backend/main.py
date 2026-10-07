# main.py
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from starlette.middleware.gzip import GZipMiddleware
from starlette.routing import Route

from dashboard_backend.api.v1.api import api_router
from dashboard_backend.core.config import settings
from dashboard_backend.database import get_db
from dashboard_backend.mcp.server import MCP_PATH, McpEndpoint


@contextmanager
def _mcp_session() -> Iterator[Session]:
    # Resolved per call so test overrides of get_db reach the MCP tools too.
    yield from app.dependency_overrides.get(get_db, get_db)()


mcp_endpoint = McpEndpoint(_mcp_session) if settings.mcp_enabled else None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
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

if mcp_endpoint is not None:
    # Plain ASGI route (not an APIRoute): stays out of the OpenAPI schema and
    # hands the request to the MCP transport unchanged.
    app.router.routes.append(Route(MCP_PATH, endpoint=mcp_endpoint))
