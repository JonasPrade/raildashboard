from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Waypoint(BaseModel):
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)


class RouteNetworks(BaseModel):
    """Optional networks a route may use in addition to existing track (all off by
    default). Further networks (issue #363) become further fields."""

    construction: bool = Field(
        False, description="Tracks under construction from OSM (railway=construction)."
    )
    proposed: bool = Field(False, description="Proposed tracks from OSM (railway=proposed).")


class RouteIn(BaseModel):
    waypoints: List[Waypoint] = Field(min_length=2)
    profile: Literal["rail_default"] = "rail_default"
    options: Dict[str, Any] = Field(default_factory=dict)
    networks: RouteNetworks = Field(default_factory=RouteNetworks)
    compare_project_id: Optional[int] = Field(
        None,
        description="Compare the route with this project's lines; the result carries "
        "properties.deviation (null when the project has no lines).",
    )


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
    project_id: int
    distance_m: float
    duration_ms: int
    bbox: List[float]
    geom_geojson: Dict[str, Any]
    details: Dict[str, Any]
