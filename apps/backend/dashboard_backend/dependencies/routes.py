from __future__ import annotations

from functools import lru_cache

from dashboard_backend.core.config import settings
from dashboard_backend.services.route_service import RouteService
from dashboard_backend.services.routing_client import RoutingClient


@lru_cache()
def _routing_client() -> RoutingClient:
    return RoutingClient(
        settings.routing_base_url,
        timeout=settings.routing_timeout_seconds,
    )


@lru_cache()
def _route_service() -> RouteService:
    return RouteService(_routing_client(), settings.graph_version)


def get_route_service() -> RouteService:
    return _route_service()
