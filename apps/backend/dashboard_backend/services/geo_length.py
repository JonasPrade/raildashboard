"""Geodesic length of the line geometries in a GeoJSON string.

Mirrors ``apps/frontend/src/shared/geo/length.ts`` (the "Länge aus Geometrie
berechnen" button), so the MCP tool and the UI produce the same number: the
haversine sum over every LineString / MultiLineString, rounded to 0.01 km.
"""

from __future__ import annotations

import json
import math
from typing import Any

_EARTH_RADIUS_M = 6371000  # mean earth radius in metres


def compute_geojson_length_km(geojson: str | None) -> float | None:
    """Total length in km, or None when the input has no parseable line geometry."""
    if not geojson:
        return None
    try:
        parsed = json.loads(geojson)
    except (TypeError, ValueError):
        return None

    meters = 0.0
    for coords in _collect_line_coords(parsed):
        for a, b in zip(coords, coords[1:]):
            meters += _haversine_m(a, b)
    if meters <= 0:
        return None
    return round(meters / 1000, 2)


def _collect_line_coords(node: Any) -> list[list]:
    if not isinstance(node, dict):
        return []
    kind = node.get("type")
    if kind == "FeatureCollection" and isinstance(node.get("features"), list):
        return [line for feature in node["features"] for line in _collect_line_coords(feature)]
    if kind == "Feature":
        return _collect_line_coords(node.get("geometry"))
    if kind == "LineString" and isinstance(node.get("coordinates"), list):
        return [node["coordinates"]]
    if kind == "MultiLineString" and isinstance(node.get("coordinates"), list):
        return list(node["coordinates"])
    if kind == "GeometryCollection" and isinstance(node.get("geometries"), list):
        return [line for geom in node["geometries"] for line in _collect_line_coords(geom)]
    return []


def _haversine_m(a: list, b: list) -> float:
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    sin_lat = math.sin((lat2 - lat1) / 2)
    sin_lon = math.sin((lon2 - lon1) / 2)
    h = sin_lat * sin_lat + math.cos(lat1) * math.cos(lat2) * sin_lon * sin_lon
    return 2 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))
