from __future__ import annotations

from typing import Any, Dict, Iterable

import httpx

from dashboard_backend.services.exceptions import RoutingUpstreamError


class RoutingClient:
    """HTTP client for the routing microservice."""

    def __init__(self, base_url: str, timeout: float = 20.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout, connect=5.0)

    async def route(
        self,
        waypoints: Iterable[Dict[str, float]],
        profile: str,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        params: list[tuple[str, str]] = [
            ("profile", profile),
            ("points_encoded", "false"),
            ("type", "json"),
            ("locale", "en"),
        ]
        params.extend(("point", f"{point['lat']},{point['lon']}") for point in waypoints)
        for key, value in options.items():
            params.append((key, str(value)))

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(f"{self._base_url}/route", params=params)
                response.raise_for_status()
            except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
                raise RoutingUpstreamError(str(exc)) from exc
        return response.json()
