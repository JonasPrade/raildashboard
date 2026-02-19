from __future__ import annotations

from typing import Any, Dict, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Waypoint(BaseModel):
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)


class RouteIn(BaseModel):
    waypoints: List[Waypoint] = Field(min_length=2)
    profile: Literal["rail_default"] = "rail_default"
    options: Dict[str, Any] = Field(default_factory=dict)


class RoutePreviewOut(BaseModel):
    """GeoJSON Feature returned by the calculate endpoint (not yet persisted)."""

    type: Literal["Feature"] = "Feature"
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


class RouteConfirmIn(BaseModel):
    """Body for the confirm endpoints (add or replace).

    The frontend sends back the GeoJSON Feature it received from /routes/calculate.
    """

    feature: Dict[str, Any]


class RouteOut(BaseModel):
    route_id: UUID
    project_id: UUID
    distance_m: float
    duration_ms: int
    bbox: List[float]
    geom_geojson: Dict[str, Any]
    details: Dict[str, Any]
