"""Simplified project geometries for the overview map.

Projects store their geometry as GeoJSON text (``geojson_representation``) in
full resolution. The overview map shows many projects at once, where that
precision is invisible but costs megabytes. This module turns one stored
GeoJSON document into a compact, simplified FeatureCollection:

- all line parts are collected into one MultiLineString and simplified
  (topology-preserving Douglas-Peucker, ``TOLERANCE_DEG``),
- all point parts are collected into one MultiPoint and kept as they are,
- coordinates are rounded to ``COORD_PRECISION`` decimals (~1 m) and reduced
  to 2D; feature properties are dropped (the map never reads them).

Polygons are ignored, matching the map, which only renders lines and points.
The detail page keeps using the exact geometry from ``GET /projects/{id}``.

Results are memoised per process, keyed by a hash of the source text: a changed
geometry produces a different key, so the cache never needs invalidating.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from collections import OrderedDict
from threading import Lock
from typing import Any, Iterator, Optional

from shapely.geometry import LineString

logger = logging.getLogger(__name__)

# ~20 m in latitude; visually lossless on the overview map up to about zoom 13.
TOLERANCE_DEG = 0.0002
# 5 decimals of a degree ≈ 1.1 m.
COORD_PRECISION = 5

_CACHE_MAX_ENTRIES = 8192
_cache: "OrderedDict[bytes, Optional[dict]]" = OrderedDict()
_cache_lock = Lock()


def simplify_geojson_text(geojson_text: Optional[str]) -> Optional[dict]:
    """Return the simplified FeatureCollection for *geojson_text* (or None).

    None means: empty input, unparsable JSON, or no line/point geometry.
    """
    if not geojson_text:
        return None
    key = hashlib.sha1(geojson_text.encode("utf-8")).digest()
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]

    result = _simplify(geojson_text)

    with _cache_lock:
        _cache[key] = result
        if len(_cache) > _CACHE_MAX_ENTRIES:
            _cache.popitem(last=False)
    return result


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _simplify(geojson_text: str) -> Optional[dict]:
    try:
        document = json.loads(geojson_text)
    except (TypeError, ValueError):
        logger.warning("Skipping unparsable geojson_representation")
        return None

    lines: list[list[list[float]]] = []
    points: list[list[float]] = []
    for geometry in _iter_geometries(document):
        geom_type = geometry.get("type")
        coords = geometry.get("coordinates")
        if geom_type == "LineString":
            _add_line(lines, coords)
        elif geom_type == "MultiLineString" and isinstance(coords, list):
            for part in coords:
                _add_line(lines, part)
        elif geom_type == "Point":
            _add_point(points, coords)
        elif geom_type == "MultiPoint" and isinstance(coords, list):
            for part in coords:
                _add_point(points, part)

    features = []
    if lines:
        features.append(_feature("MultiLineString", lines))
    if points:
        features.append(_feature("MultiPoint", points))
    if not features:
        return None
    return {"type": "FeatureCollection", "features": features}


def _iter_geometries(node: Any) -> Iterator[dict]:
    """Yield every plain geometry in a GeoJSON document, depth-first."""
    if not isinstance(node, dict):
        return
    node_type = node.get("type")
    if node_type == "FeatureCollection":
        for feature in node.get("features") or []:
            yield from _iter_geometries(feature)
    elif node_type == "Feature":
        yield from _iter_geometries(node.get("geometry"))
    elif node_type == "GeometryCollection":
        for geometry in node.get("geometries") or []:
            yield from _iter_geometries(geometry)
    elif node_type:
        yield node


def _clean_coord(coord: Any) -> Optional[list[float]]:
    if not isinstance(coord, (list, tuple)) or len(coord) < 2:
        return None
    x, y = coord[0], coord[1]
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    return [float(x), float(y)]


def _round(coord: list[float]) -> list[float]:
    return [round(coord[0], COORD_PRECISION), round(coord[1], COORD_PRECISION)]


def _add_point(points: list, coord: Any) -> None:
    clean = _clean_coord(coord)
    if clean is not None:
        points.append(_round(clean))


def _add_line(lines: list, coords: Any) -> None:
    if not isinstance(coords, list):
        return
    clean = [c for c in (_clean_coord(coord) for coord in coords) if c is not None]
    if len(clean) < 2:
        return
    if len(clean) > 2:
        try:
            simplified = LineString(clean).simplify(TOLERANCE_DEG, preserve_topology=True)
            if not simplified.is_empty and simplified.geom_type == "LineString":
                clean = [list(c) for c in simplified.coords]
        except Exception:  # pragma: no cover - defensive: keep the unsimplified line
            logger.warning("Line simplification failed; keeping full resolution", exc_info=True)
    rounded = [_round(c) for c in clean]
    # Rounding can collapse neighbouring vertices; drop the repeats.
    deduped = [rounded[0]] + [c for prev, c in zip(rounded, rounded[1:]) if c != prev]
    if len(deduped) >= 2:
        lines.append(deduped)


def _feature(geom_type: str, coordinates: list) -> dict:
    return {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": geom_type, "coordinates": coordinates},
    }
