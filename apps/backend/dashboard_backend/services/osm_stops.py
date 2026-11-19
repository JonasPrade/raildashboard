"""Stops of S-Bahn/Stadtbahn, U-Bahn and tram networks from OSM as operational points.

The operational points in the database come from RINF and cover the main line network
only (including S-Bahn stations). Routing over light_rail, subway and tram track
(services/routing_networks.py) needs waypoints on those networks too, so their stops
are imported from OSM (Overpass) into ``operational_point`` with ``source = "osm"`` and
``network`` = light_rail | subway | tram. See docs/features/feature-routing.md →
"Gleisarten (S-Bahn, U-Bahn, Straßenbahn, Schmalspur)".

Everything here is pure (no HTTP, no database) and unit-tested; the script
scripts/import_osm_stops.py fetches the data and writes it.

Rules:
- ``railway=station|halt`` + ``station=subway`` → subway, ``station=light_rail`` →
  light_rail; ``railway=tram_stop`` → tram. Elements without a name are skipped.
- Stops of one network with the same name within 300 m are one stop (a tram stop is
  mapped once per direction, a station as node and area): one point at their centre,
  keyed by its first OSM element (nodes before ways before relations, then the smallest
  id), so the op_id stays stable across reruns.
- A light_rail station that is already a RINF operational point (same name, at most
  300 m away) is skipped — Berlin and Hamburg S-Bahn stations are in RINF.
- ``op_id`` is ``OSM-<n|w|r><id>``.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

OVERPASS_QUERY = """
[out:json][timeout:900];
area["ISO3166-1"="DE"][admin_level=2]->.de;
(
  nwr["railway"~"^(station|halt)$"]["station"~"^(subway|light_rail)$"](area.de);
  nwr["railway"="tram_stop"](area.de);
);
out center tags;
""".strip()

MERGE_DISTANCE_M = 300.0
_TYPE_PREFIX = {"node": "n", "way": "w", "relation": "r"}


@dataclass
class OsmStop:
    op_id: str
    name: str
    network: str
    type: str  # OSM railway=* value: station / halt / tram_stop
    latitude: float
    longitude: float


@dataclass(frozen=True)
class KnownPoint:
    """An existing (RINF) operational point to check light_rail stations against."""

    name: str
    latitude: float
    longitude: float


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def stop_network(tags: Dict[str, str]) -> Optional[str]:
    railway = tags.get("railway")
    if railway == "tram_stop":
        return "tram"
    if railway in ("station", "halt"):
        station = tags.get("station")
        if station in ("subway", "light_rail"):
            return station
    return None


def _position(element: Dict[str, Any]) -> Optional[tuple[float, float]]:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center")
    if center and "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None


def _osm_key(element: Dict[str, Any]) -> tuple[int, int]:
    """Sort key: nodes before ways before relations, then by id."""
    order = {"node": 0, "way": 1, "relation": 2}
    return order.get(element.get("type", ""), 3), int(element.get("id", 0))


def normalize_name(name: str) -> str:
    """Name for comparing stops: lower case, without S/U prefixes, station words,
    brackets and punctuation."""
    text = name.lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"^(s\+u|s \+ u|s|u|s-bahn|u-bahn|bahnhof|bf\.?|hbf\.?)\s+", "", text)
    text = re.sub(r"\b(bahnhof|bhf|s-bahnhof|u-bahnhof|haltepunkt)\b", " ", text)
    text = re.sub(r"[^\w]+", " ", text)
    return " ".join(text.split())


def _same_name(a: str, b: str) -> bool:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


def stops_from_overpass(
    elements: Iterable[Dict[str, Any]],
    known_points: Sequence[KnownPoint] = (),
) -> List[OsmStop]:
    """Overpass elements → merged stops, without light_rail stations already in RINF."""
    candidates: List[tuple[Dict[str, Any], str, float, float]] = []
    for element in elements:
        tags = element.get("tags") or {}
        network = stop_network(tags)
        name = (tags.get("name") or "").strip()
        position = _position(element)
        if network is None or not name or position is None:
            continue
        candidates.append((element, network, position[0], position[1]))
    candidates.sort(key=lambda c: _osm_key(c[0]))

    # Merge: same network, same name, within MERGE_DISTANCE_M of the cluster's first stop.
    clusters: List[List[tuple[Dict[str, Any], str, float, float]]] = []
    by_name: Dict[tuple[str, str], List[int]] = {}
    for candidate in candidates:
        element, network, lat, lon = candidate
        key = (network, normalize_name(element["tags"]["name"]))
        target = None
        for index in by_name.get(key, []):
            _, _, first_lat, first_lon = clusters[index][0]
            if haversine_m(lat, lon, first_lat, first_lon) <= MERGE_DISTANCE_M:
                target = index
                break
        if target is None:
            by_name.setdefault(key, []).append(len(clusters))
            clusters.append([candidate])
        else:
            clusters[target].append(candidate)

    stops: List[OsmStop] = []
    for cluster in clusters:
        first, network, _, _ = cluster[0]
        lat = sum(c[2] for c in cluster) / len(cluster)
        lon = sum(c[3] for c in cluster) / len(cluster)
        name = first["tags"]["name"].strip()
        if network == "light_rail" and any(
            haversine_m(lat, lon, p.latitude, p.longitude) <= MERGE_DISTANCE_M
            and _same_name(name, p.name)
            for p in known_points
        ):
            continue
        stops.append(
            OsmStop(
                op_id=f"OSM-{_TYPE_PREFIX.get(first['type'], 'x')}{first['id']}",
                name=name,
                network=network,
                type=first["tags"].get("railway", ""),
                latitude=round(lat, 6),
                longitude=round(lon, 6),
            )
        )
    return stops
