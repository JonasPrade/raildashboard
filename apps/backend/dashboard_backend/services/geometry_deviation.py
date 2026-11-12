"""How far a newly routed line departs from the lines a project already has.

Used before a routed geometry replaces a project's geometry: the editor and the MCP tool
report the numbers, the user decides. Nothing here writes.

The comparison runs in a local metric plane (equirectangular around the mean latitude):
for lines within Germany the error is well below one percent, enough to tell "same
alignment" from "another alignment". Only line features count; points are ignored.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence

import shapely
from shapely.geometry import MultiLineString
from shapely.ops import unary_union

# Within this distance a line counts as following the other one.
CORRIDOR_M = 100.0
# Vertex spacing for the distance sampling.
SAMPLE_STEP_M = 50.0

_M_PER_DEG_LAT = 110_574.0
_M_PER_DEG_LON_EQUATOR = 111_320.0


def _line_parts(features: Iterable[Dict[str, Any]]) -> List[List[Sequence[float]]]:
    parts: List[List[Sequence[float]]] = []
    for feature in features:
        geometry = (feature or {}).get("geometry") or {}
        coords = geometry.get("coordinates") or []
        if geometry.get("type") == "LineString":
            candidates = [coords]
        elif geometry.get("type") == "MultiLineString":
            candidates = coords
        else:
            continue
        parts.extend(c for c in candidates if isinstance(c, list) and len(c) >= 2)
    return parts


def _project(parts: List[List[Sequence[float]]], lat0: float) -> MultiLineString:
    kx = _M_PER_DEG_LON_EQUATOR * math.cos(math.radians(lat0))
    return MultiLineString(
        [[(float(p[0]) * kx, float(p[1]) * _M_PER_DEG_LAT) for p in part] for part in parts]
    )


def _distances(source: MultiLineString, target: Any) -> List[float]:
    sampled = shapely.segmentize(source, SAMPLE_STEP_M)
    points = shapely.points(shapely.get_coordinates(sampled))
    return list(shapely.distance(points, target))


def _within_share(line: Any, corridor: Any) -> float:
    if line.length == 0:
        return 0.0
    return line.intersection(corridor).length / line.length


def geometry_deviation(
    route_coordinates: Sequence[Sequence[float]],
    existing_features: Iterable[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Deviation of a route from the existing lines, or None without existing lines.

    - ``route_within_corridor_share``: part of the route within 100 m of an existing line
    - ``existing_within_corridor_share``: part of the existing lines within 100 m of the route
    - ``max_deviation_m``: largest distance of the route from the existing lines (and vice
      versa, whichever is larger — a symmetric Hausdorff distance, sampled every 50 m)
    - ``mean_deviation_m``: mean distance of the route from the existing lines
    """
    existing_parts = _line_parts(existing_features)
    if not existing_parts or len(route_coordinates) < 2:
        return None

    all_lats = [float(p[1]) for p in route_coordinates] + [
        float(p[1]) for part in existing_parts for p in part
    ]
    lat0 = sum(all_lats) / len(all_lats)
    route = _project([list(route_coordinates)], lat0)
    existing = _project(existing_parts, lat0)
    existing_union = unary_union(existing)
    route_union = unary_union(route)

    route_to_existing = _distances(route, existing_union)
    existing_to_route = _distances(existing, route_union)

    return {
        "route_length_km": round(route.length / 1000, 2),
        "existing_length_km": round(existing.length / 1000, 2),
        "corridor_m": CORRIDOR_M,
        "route_within_corridor_share": round(
            _within_share(route_union, existing_union.buffer(CORRIDOR_M)), 3
        ),
        "existing_within_corridor_share": round(
            _within_share(existing_union, route_union.buffer(CORRIDOR_M)), 3
        ),
        "max_deviation_m": round(max(max(route_to_existing), max(existing_to_route))),
        "mean_deviation_m": round(sum(route_to_existing) / len(route_to_existing)),
    }

