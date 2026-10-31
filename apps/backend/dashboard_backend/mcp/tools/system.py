"""System diagnostics: is the routing service up, are the Celery workers there?

For telling a failing tool call apart from a failing service — e.g. when
route_project_geometry or start_infraplan_parse do not get through. Same right
as the admin area's health checks: ``settings.manage``.
"""

from __future__ import annotations

from typing import Any

import anyio
from mcp.server.mcpserver import Context, MCPServer

from dashboard_backend.mcp.context import get_principal, require
from dashboard_backend.mcp.tools.projects import READ_ONLY
from dashboard_backend.services.routing_health import routing_health
from dashboard_backend.services.worker_health import cached_worker_health


async def get_system_status(*, ctx: Context) -> dict[str, Any]:
    """Health of the services behind the tools (requires ``settings.manage``):
    ``routing`` — GraphHopper reachable, latency, a German message naming the
    next step (probed now); ``workers`` — broker and Celery workers that run
    long jobs such as the Infraplan parse and recomputations (cached for a few
    seconds). Credentials are never included."""
    require(get_principal(ctx), "settings.manage")
    # Both probe the network with a bounded timeout; keep them off the event loop.
    routing = await anyio.to_thread.run_sync(routing_health)
    workers = await anyio.to_thread.run_sync(cached_worker_health)
    return {
        "routing": routing.model_dump(mode="json"),
        "workers": workers.model_dump(mode="json"),
    }


def register(server: MCPServer) -> None:
    server.add_tool(get_system_status, annotations=READ_ONLY)
