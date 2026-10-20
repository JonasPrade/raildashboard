"""Is the routing service (GraphHopper) answering? — health for the admin status page.

Routing a project geometry needs GraphHopper. When it is down, the failure only
surfaces as a 502 on the map, so the system status page asks it directly.

Same two rules as ``worker_health``: the probe is bounded by a short timeout and
never raises — every failure becomes a value the page can show.
"""

from __future__ import annotations

import time

import httpx

from dashboard_backend.core.config import settings
from dashboard_backend.schemas.system import RoutingHealthSchema
from dashboard_backend.services.worker_health import sanitize_broker_url

PROBE_TIMEOUT_SECONDS = 3.0

_UNREACHABLE = (
    "Der Routing-Dienst (GraphHopper) ist nicht erreichbar. Strecken können nicht "
    "geroutet werden. Prüfen: `docker compose ps graphhopper` und "
    "`docker compose logs --tail=50 graphhopper` (nach einem Neustart baut er den "
    "Graphen neu auf, das kann mehrere Minuten dauern)."
)
_BAD_STATUS = (
    "Der Routing-Dienst antwortet, meldet aber einen Fehler. Prüfen: "
    "`docker compose logs --tail=50 graphhopper`."
)


def routing_health(timeout: float = PROBE_TIMEOUT_SECONDS) -> RoutingHealthSchema:
    """One bounded look at GraphHopper's ``/health`` endpoint."""
    base_url = settings.routing_base_url.rstrip("/")
    shown_url = sanitize_broker_url(base_url)
    started = time.monotonic()
    try:
        response = httpx.get(f"{base_url}/health", timeout=timeout)
    except httpx.HTTPError as exc:
        return RoutingHealthSchema(
            status="unreachable",
            base_url=shown_url,
            message=_UNREACHABLE,
            detail=f"{type(exc).__name__}: {exc}"[:300],
            checked_at=time.time(),
        )

    latency_ms = round((time.monotonic() - started) * 1000)
    if response.status_code != 200:
        return RoutingHealthSchema(
            status="error",
            base_url=shown_url,
            http_status=response.status_code,
            latency_ms=latency_ms,
            message=_BAD_STATUS,
            detail=f"HTTP {response.status_code}",
            checked_at=time.time(),
        )
    return RoutingHealthSchema(
        status="ok",
        base_url=shown_url,
        http_status=response.status_code,
        latency_ms=latency_ms,
        message=f"Routing-Dienst erreichbar (Antwort in {latency_ms} ms).",
        checked_at=time.time(),
    )
