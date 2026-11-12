from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import httpx

from dashboard_backend.services.exceptions import RoutingNoPathError, RoutingUpstreamError
from dashboard_backend.services.routing_networks import STATUS_DETAIL


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
        custom_model: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Route between the waypoints.

        Every request asks for the ``railway_status`` path detail, so the caller knows
        which part of the route runs on which kind of track. A ``custom_model`` (network
        switches, see services/routing_networks.py) needs GraphHopper's POST form.
        """
        waypoints = list(waypoints)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                if custom_model is None:
                    params: list[tuple[str, str]] = [
                        ("profile", profile),
                        ("points_encoded", "false"),
                        ("type", "json"),
                        ("locale", "en"),
                        ("details", STATUS_DETAIL),
                    ]
                    params.extend(("point", f"{point['lat']},{point['lon']}") for point in waypoints)
                    for key, value in options.items():
                        params.append((key, str(value)))
                    response = await client.get(f"{self._base_url}/route", params=params)
                else:
                    body: Dict[str, Any] = {
                        **options,
                        "profile": profile,
                        "points": [[point["lon"], point["lat"]] for point in waypoints],
                        "points_encoded": False,
                        "locale": "en",
                        "details": [STATUS_DETAIL],
                        "custom_model": custom_model,
                    }
                    response = await client.post(f"{self._base_url}/route", json=body)
                if response.status_code == 400:
                    # GraphHopper answers 400 when a point cannot be snapped or no
                    # connection exists on the chosen network — a "no path", not an outage.
                    raise RoutingNoPathError(_error_message(response))
                response.raise_for_status()
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as exc:
            raise RoutingUpstreamError(str(exc)) from exc
        return response.json()


def _error_message(response: httpx.Response) -> str:
    try:
        return str(response.json().get("message") or "no path")
    except ValueError:
        return "no path"
