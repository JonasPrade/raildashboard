"""Which tracks a route may use, and where each part of a route came from.

GraphHopper (OpenRailRouting with the dashboard's extension, docker/graphhopper/orr/)
knows the lifecycle status of every rail track: ``existing``, ``construction`` or
``proposed`` (from OSM ``railway=construction|proposed`` and the lifecycle prefixes).

- Without a switch the route runs on the profile ``rail_default``, which never uses or
  snaps to a track that is not in operation.
- Each switch admits one more kind of track. The route then runs on the flexible profile
  ``rail_flex`` with a query custom model that excludes everything not switched on and
  prefers the switched-on tracks over the existing ones — they were asked for because
  the line is new, and an OSM track without speed tags is otherwise slower than any
  existing line (25 km/h default).

The switches are a dict of booleans so that further networks (issue #363: subway, tram)
can be added as further keys. docker/graphhopper/test/smoke.sh sends the same statements
to a real router; tests/unit/test_routing_networks.py pins them.

Stored features carry their origin in ``properties``:
``geometry_source`` = routing | manual | upload, and for routed lines ``track_status``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_PROFILE = "rail_default"
FLEX_PROFILE = "rail_flex"

STATUS_EXISTING = "existing"
STATUS_CONSTRUCTION = "construction"
STATUS_PROPOSED = "proposed"
TRACK_STATUSES = (STATUS_EXISTING, STATUS_CONSTRUCTION, STATUS_PROPOSED)

# Optional networks a request can switch on: switch key -> track status it admits.
OPTIONAL_NETWORKS: Dict[str, str] = {
    "construction": STATUS_CONSTRUCTION,
    "proposed": STATUS_PROPOSED,
}

# Priority factor for existing track when a planned network is switched on. Below 1, so
# a switched-on track wins over a parallel existing line unless it is much longer.
EXISTING_PRIORITY_WITH_PLANNED = "0.1"

SOURCE_ROUTING = "routing"
SOURCE_MANUAL = "manual"
SOURCE_UPLOAD = "upload"

STATUS_DETAIL = "railway_status"


@dataclass(frozen=True)
class RoutingRequest:
    profile: str
    custom_model: Optional[Dict[str, Any]]


def normalize_networks(networks: Optional[Dict[str, bool]]) -> Dict[str, bool]:
    """All known switches with a boolean value; unknown keys are rejected."""
    networks = networks or {}
    unknown = sorted(set(networks) - set(OPTIONAL_NETWORKS))
    if unknown:
        raise ValueError(f"unknown network(s): {', '.join(unknown)}")
    return {key: bool(networks.get(key, False)) for key in OPTIONAL_NETWORKS}


def routing_request(networks: Optional[Dict[str, bool]]) -> RoutingRequest:
    """Profile and query custom model for the given switches."""
    switches = normalize_networks(networks)
    if not any(switches.values()):
        return RoutingRequest(profile=DEFAULT_PROFILE, custom_model=None)

    priority: List[Dict[str, str]] = [
        {"if": f"{STATUS_DETAIL} == {status.upper()}", "multiply_by": "0"}
        for key, status in OPTIONAL_NETWORKS.items()
        if not switches[key]
    ]
    priority.append(
        {
            "if": f"{STATUS_DETAIL} == {STATUS_EXISTING.upper()}",
            "multiply_by": EXISTING_PRIORITY_WITH_PLANNED,
        }
    )
    return RoutingRequest(profile=FLEX_PROFILE, custom_model={"priority": priority})


# --- sections of a route ---------------------------------------------------------------


def _haversine_m(a: Sequence[float], b: Sequence[float]) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def _line_length_m(coords: Sequence[Sequence[float]]) -> float:
    return sum(_haversine_m(coords[i], coords[i + 1]) for i in range(len(coords) - 1))


def route_sections(
    coordinates: Sequence[Sequence[float]], details: Optional[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Contiguous runs of one track status along the route.

    ``details`` is GraphHopper's ``path.details``; ``railway_status`` is a list of
    ``[from_index, to_index, value]`` over the route's coordinates. Without it (older
    router) the whole route counts as existing track. Adjacent runs of the same status
    are merged; each section carries its coordinate range and length.
    """
    n = len(coordinates)
    if n < 2:
        return []
    raw = (details or {}).get(STATUS_DETAIL) or [[0, n - 1, STATUS_EXISTING]]

    sections: List[Dict[str, Any]] = []
    for entry in raw:
        start, end, status = int(entry[0]), int(entry[1]), str(entry[2])
        start, end = max(0, start), min(n - 1, end)
        if end <= start:
            continue
        if status not in TRACK_STATUSES:
            status = STATUS_EXISTING
        if sections and sections[-1]["track_status"] == status and sections[-1]["to_index"] == start:
            sections[-1]["to_index"] = end
        else:
            sections.append({"track_status": status, "from_index": start, "to_index": end})

    for section in sections:
        part = coordinates[section["from_index"] : section["to_index"] + 1]
        section["length_km"] = round(_line_length_m(part) / 1000, 3)
    return sections


def status_totals_km(sections: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    totals = {status: 0.0 for status in TRACK_STATUSES}
    for section in sections:
        totals[section["track_status"]] += section["length_km"]
    return {status: round(km, 2) for status, km in totals.items() if km > 0}


def route_line_features(
    coordinates: Sequence[Sequence[float]], sections: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """The route as stored features: one LineString per section, tagged with its origin.

    A route entirely on existing track stays one feature, as before. Splitting by status
    keeps new-build and existing-track parts apart (TRAVE needs them separately).
    """
    if not sections:
        sections = [{"track_status": STATUS_EXISTING, "from_index": 0, "to_index": len(coordinates) - 1}]
    features = []
    for section in sections:
        part = [list(c) for c in coordinates[section["from_index"] : section["to_index"] + 1]]
        if len(part) < 2:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": part},
                "properties": {
                    "geometry_source": SOURCE_ROUTING,
                    "track_status": section["track_status"],
                },
            }
        )
    return features


def feature_origin(feature: Dict[str, Any]) -> str:
    """Short origin key of a stored feature: routing_existing / routing_construction /
    routing_proposed / manual / upload / unknown (saved before origins were recorded)."""
    properties = feature.get("properties") or {}
    source = properties.get("geometry_source")
    if source == SOURCE_ROUTING:
        status = properties.get("track_status")
        return f"routing_{status if status in TRACK_STATUSES else STATUS_EXISTING}"
    if source in (SOURCE_MANUAL, SOURCE_UPLOAD):
        return str(source)
    return "unknown"
