from __future__ import annotations

from typing import Any, Dict, Iterable, Sequence
from uuid import UUID

from geoalchemy2.shape import from_shape
from shapely.geometry import LineString, Polygon
from sqlalchemy.orm import Session

from dashboard_backend.crud.routes import (
    get_route_by_cache_key,
    list_routes_for_project,
    persist_route,
)
from dashboard_backend.models.routes import Route, route_hash
from dashboard_backend.services.exceptions import RoutingNoPathError
from dashboard_backend.services.routing_client import RoutingClient


class RouteService:
    """Coordinates caching, persistence and microservice interaction."""

    def __init__(self, routing_client: RoutingClient, graph_version: str) -> None:
        self._routing_client = routing_client
        self._graph_version = graph_version

    async def create_and_store(
        self,
        db: Session,
        project_id: UUID,
        waypoints: Iterable[Dict[str, float]],
        profile: str,
        options: Dict[str, Any],
    ) -> Route:
        cache_key = route_hash(waypoints, profile, options, self._graph_version)
        cached = get_route_by_cache_key(db, cache_key)
        if cached is not None:
            return cached

        response = await self._routing_client.route(waypoints, profile, options)
        path = self._extract_path(response)
        line = self._build_line(path)
        bbox = self._build_bbox(line)

        route = Route(
            project_id=project_id,
            profile=profile,
            graph_version=self._graph_version,
            distance_m=float(path["distance"]),
            duration_ms=int(path["time"]),
            geom=from_shape(line, srid=4326),
            bbox=from_shape(bbox, srid=4326),
            details=self._build_details(path),
            cache_key=cache_key,
        )
        return persist_route(db, route)

    async def list_for_project(
        self, db: Session, project_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Route]:
        return list_routes_for_project(db, project_id, limit=limit, offset=offset)

    @staticmethod
    def _extract_path(response: Dict[str, Any]) -> Dict[str, Any]:
        paths = response.get("paths")
        if not paths:
            raise RoutingNoPathError("routing service returned no paths")
        path = paths[0]
        if "points" not in path or "coordinates" not in path["points"]:
            raise RoutingNoPathError("routing service did not include coordinates")
        return path

    @staticmethod
    def _build_line(path: Dict[str, Any]) -> LineString:
        coordinates = path["points"]["coordinates"]
        if not coordinates:
            raise RoutingNoPathError("routing path contains no coordinates")
        return LineString([(float(lon), float(lat)) for lon, lat in coordinates])

    @staticmethod
    def _build_bbox(line: LineString) -> Polygon:
        minx, miny, maxx, maxy = line.bounds
        return Polygon(
            [
                (minx, miny),
                (maxx, miny),
                (maxx, maxy),
                (minx, maxy),
                (minx, miny),
            ]
        )

    @staticmethod
    def _build_details(path: Dict[str, Any]) -> Dict[str, Any]:
        keys = ("snapped_waypoints", "ascend", "descend")
        return {
            "raw_service": "graphhopper",
            "encoded": False,
            "resp_meta": {key: path.get(key) for key in keys if key in path},
        }
