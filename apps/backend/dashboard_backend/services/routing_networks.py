"""Which tracks a route may use, and where each part of a route came from.

GraphHopper (OpenRailRouting with the dashboard's extension, docker/graphhopper/orr/)
knows two things about every track:

- its lifecycle status: ``existing``, ``construction`` or ``proposed`` (from OSM
  ``railway=construction|proposed`` and the lifecycle prefixes), and
- its track class (``railway_class``): ``rail`` (Vollbahn), ``light_rail`` (S-Bahn/
  Stadtbahn), ``subway``, ``tram``, ``narrow_gauge``, and ``other`` for a planned track
  whose type OSM does not give (called ``unknown`` here).

A request chooses both (``networks``):

- status switches ``construction`` / ``proposed``, each admitting one more kind of
  track; switched-on tracks are preferred over existing ones (existing ×0.1) — they
  were asked for because the line is new, and an OSM track without speed tags is
  otherwise slower than any existing line (25 km/h default);
- ``track_classes``: ``["rail"]`` by default, or any combination of the other classes.
  ``rail`` is exclusive to them (decision EK-2026-355): a route runs either on main
  line track or on the chosen urban/narrow-gauge networks. ``unknown`` (planned tracks
  without a type) combines with anything but only makes sense with a status switch.

Main line only without status switches runs on ``rail_default`` (unchanged, CH);
everything else on ``rail_flex`` with a query custom model that excludes what was not
chosen. docker/graphhopper/test/smoke.sh sends the same statements to a real router;
tests/unit/test_routing_networks.py pins them.

Stored features carry their origin in ``properties``: ``geometry_source`` = routing |
manual | upload, and for routed lines ``track_status`` and ``railway_class``.
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

CLASS_RAIL = "rail"
CLASS_LIGHT_RAIL = "light_rail"
CLASS_SUBWAY = "subway"
CLASS_TRAM = "tram"
CLASS_NARROW_GAUGE = "narrow_gauge"
CLASS_UNKNOWN = "unknown"
# Order is the order of the query statements (smoke.sh builds them the same way).
TRACK_CLASSES = (
    CLASS_RAIL,
    CLASS_LIGHT_RAIL,
    CLASS_SUBWAY,
    CLASS_TRAM,
    CLASS_NARROW_GAUGE,
    CLASS_UNKNOWN,
)
DEFAULT_TRACK_CLASSES = [CLASS_RAIL]
# Classes that can never be combined with rail (unknown can: there is no existing
# track of that class, it only admits planned tracks without a type).
URBAN_CLASSES = (CLASS_LIGHT_RAIL, CLASS_SUBWAY, CLASS_TRAM, CLASS_NARROW_GAUGE)
# Router enum value per class (railway_class); unknown is OpenRailRouting's OTHER.
_ROUTER_CLASS = {cls: cls.upper() for cls in TRACK_CLASSES} | {CLASS_UNKNOWN: "OTHER"}

# Priority factor for existing track when a planned network is switched on. Below 1, so
# a switched-on track wins over a parallel existing line unless it is much longer.
EXISTING_PRIORITY_WITH_PLANNED = "0.1"

SOURCE_ROUTING = "routing"
SOURCE_MANUAL = "manual"
SOURCE_UPLOAD = "upload"

STATUS_DETAIL = "railway_status"
CLASS_DETAIL = "railway_class"
ROUTE_DETAILS = (STATUS_DETAIL, CLASS_DETAIL)


class NetworkSelectionError(ValueError):
    """The requested networks contradict each other (→ 422)."""


@dataclass(frozen=True)
class RoutingRequest:
    profile: str
    custom_model: Optional[Dict[str, Any]]


def normalize_track_classes(classes: Optional[Sequence[str]]) -> List[str]:
    """Known, de-duplicated classes in canonical order; ``None`` → ``["rail"]``."""
    if classes is None:
        return list(DEFAULT_TRACK_CLASSES)
    unknown = sorted(set(classes) - set(TRACK_CLASSES))
    if unknown:
        raise NetworkSelectionError(f"unknown track class(es): {', '.join(unknown)}")
    chosen = [cls for cls in TRACK_CLASSES if cls in set(classes)]
    if not chosen:
        raise NetworkSelectionError("choose at least one track class")
    return chosen


def normalize_networks(networks: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """All switches with a value; contradictions raise NetworkSelectionError.

    Result: ``{"construction": bool, "proposed": bool, "track_classes": [...]}``.
    """
    networks = dict(networks or {})
    classes = normalize_track_classes(networks.pop("track_classes", None))
    unknown_keys = sorted(set(networks) - set(OPTIONAL_NETWORKS))
    if unknown_keys:
        raise NetworkSelectionError(f"unknown network(s): {', '.join(unknown_keys)}")
    switches: Dict[str, Any] = {key: bool(networks.get(key, False)) for key in OPTIONAL_NETWORKS}

    if CLASS_RAIL in classes and any(cls in classes for cls in URBAN_CLASSES):
        raise NetworkSelectionError(
            "rail (Vollbahn) cannot be combined with light_rail, subway, tram or narrow_gauge; "
            "route those parts separately and append them"
        )
    if CLASS_UNKNOWN in classes and not any(switches.values()):
        raise NetworkSelectionError(
            "track class unknown only admits planned tracks; switch on construction or proposed"
        )
    switches["track_classes"] = classes
    return switches


def is_default_networks(switches: Dict[str, Any]) -> bool:
    """Main line only, no status switch: the unchanged existing-network routing."""
    return not any(switches[key] for key in OPTIONAL_NETWORKS) and switches[
        "track_classes"
    ] == DEFAULT_TRACK_CLASSES


def routing_request(networks: Optional[Dict[str, Any]]) -> RoutingRequest:
    """Profile and query custom model for the given switches."""
    switches = normalize_networks(networks)
    if is_default_networks(switches):
        return RoutingRequest(profile=DEFAULT_PROFILE, custom_model=None)

    priority: List[Dict[str, str]] = [
        {"if": f"{CLASS_DETAIL} == {_ROUTER_CLASS[cls]}", "multiply_by": "0"}
        for cls in TRACK_CLASSES
        if cls not in switches["track_classes"]
    ]
    priority.extend(
        {"if": f"{STATUS_DETAIL} == {status.upper()}", "multiply_by": "0"}
        for key, status in OPTIONAL_NETWORKS.items()
        if not switches[key]
    )
    if any(switches[key] for key in OPTIONAL_NETWORKS):
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


def _segment_values(entries: Optional[Sequence[Sequence[Any]]], n: int, default: str) -> List[str]:
    """Value of a path detail for each of the n-1 segments of the route."""
    values = [default] * max(0, n - 1)
    for entry in entries or []:
        start, end, value = int(entry[0]), int(entry[1]), entry[2]
        for i in range(max(0, start), min(n - 1, end)):
            values[i] = str(value) if value is not None else default
    return values


def _router_class(value: str) -> str:
    """Path detail value → class key (OpenRailRouting's ``other`` is ``unknown``)."""
    return value if value in TRACK_CLASSES and value != CLASS_UNKNOWN else CLASS_UNKNOWN


def route_sections(
    coordinates: Sequence[Sequence[float]], details: Optional[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Contiguous runs of one track status and one track class along the route.

    ``details`` is GraphHopper's ``path.details``; ``railway_status`` and
    ``railway_class`` are lists of ``[from_index, to_index, value]`` over the route's
    coordinates. Without them (older router) the route counts as existing main line
    track. Each section carries its status, class, coordinate range and length.
    """
    n = len(coordinates)
    if n < 2:
        return []
    details = details or {}
    statuses = _segment_values(details.get(STATUS_DETAIL), n, STATUS_EXISTING)
    classes = _segment_values(details.get(CLASS_DETAIL), n, CLASS_RAIL)

    sections: List[Dict[str, Any]] = []
    for i in range(n - 1):
        status = statuses[i] if statuses[i] in TRACK_STATUSES else STATUS_EXISTING
        track_class = _router_class(classes[i])
        last = sections[-1] if sections else None
        if last and last["track_status"] == status and last["railway_class"] == track_class:
            last["to_index"] = i + 1
        else:
            sections.append(
                {"track_status": status, "railway_class": track_class, "from_index": i, "to_index": i + 1}
            )

    for section in sections:
        part = coordinates[section["from_index"] : section["to_index"] + 1]
        section["length_km"] = round(_line_length_m(part) / 1000, 3)
    return sections


def status_totals_km(sections: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    totals = {status: 0.0 for status in TRACK_STATUSES}
    for section in sections:
        totals[section["track_status"]] += section["length_km"]
    return {status: round(km, 2) for status, km in totals.items() if km > 0}


def class_totals_km(sections: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    totals = {cls: 0.0 for cls in TRACK_CLASSES}
    for section in sections:
        totals[section.get("railway_class", CLASS_RAIL)] += section["length_km"]
    return {cls: round(km, 2) for cls, km in totals.items() if km > 0}


def route_line_features(
    coordinates: Sequence[Sequence[float]], sections: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """The route as stored features: one LineString per section, tagged with its origin.

    A route entirely on existing main line track stays one feature, as before.
    Splitting by status keeps new-build and existing-track parts apart (TRAVE needs
    them separately), splitting by class keeps S-Bahn, U-Bahn, tram apart.
    """
    if not sections:
        sections = [
            {
                "track_status": STATUS_EXISTING,
                "railway_class": CLASS_RAIL,
                "from_index": 0,
                "to_index": len(coordinates) - 1,
            }
        ]
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
                    "railway_class": section.get("railway_class", CLASS_RAIL),
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


def feature_class(feature: Dict[str, Any]) -> str:
    """Track class of a stored line: rail / light_rail / subway / tram / narrow_gauge /
    unknown (planned without type), or ``none`` when it carries no class (drawn,
    uploaded, or routed before classes were recorded — not assumed to be main line)."""
    value = (feature.get("properties") or {}).get("railway_class")
    return value if value in TRACK_CLASSES else "none"
