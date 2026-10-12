"""Plausibility checks for a project geometry (MCP ``check_geometry``).

Pure functions over parsed GeoJSON features, so they can be tested without a
database. The caller resolves the operational points named in the project name
(``place_names_from_project_name``) and passes their coordinates in.

Every check reports a finding, never a verdict: a project may legitimately
consist of several separate parts (e.g. single stations of a programme), and a
hand-drawn new line has no route. The findings point at what to look at.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from dashboard_backend.services.geo_length import _haversine_m

# A two-point line part at least this long is a chord, not a routed track
# (routed lines carry a vertex every few dozen metres).
CHORD_MIN_KM = 0.2
# Share of the line length in chords from which the geometry counts as sketched.
CHORD_SHARE_THRESHOLD = 0.5
# Line ends closer than this are considered connected.
DEFAULT_GAP_TOLERANCE_KM = 0.05
# An operational point named in the project name should lie this close to the line.
DEFAULT_STATION_DISTANCE_KM = 3.0
# Stored length deviates when it differs by more than max(absolute, relative).
LENGTH_TOLERANCE_KM = 0.5
LENGTH_TOLERANCE_SHARE = 0.02
MAX_REPORTED_GAPS = 5
# Words tried per side when matching place names ("Bad Friedrichshall Hbf").
MAX_PLACE_WORDS = 4

# Place separators in project names: a dash (en/em/minus) with or without spaces,
# or a hyphen surrounded by spaces. "Köln-Mülheim" stays one place.
_PLACE_SPLIT = re.compile(r"\s*[–—−]\s*|\s+-\s+")
_PARENTHESES = re.compile(r"\([^)]*\)")


@dataclass(frozen=True)
class Station:
    """An operational point named in the project name, with its coordinates."""

    role: str  # "start" | "end"
    query: str
    name: str
    op_id: str | None
    lon: float
    lat: float


def _km(a: list[float], b: list[float]) -> float:
    return _haversine_m(a, b) / 1000


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def line_parts(features: list[dict[str, Any]]) -> list[list[list[float]]]:
    """All LineString parts (MultiLineStrings split up) with at least two positions."""
    parts: list[list[list[float]]] = []
    for feature in features:
        geometry = (feature or {}).get("geometry") or {}
        kind = geometry.get("type")
        coords = geometry.get("coordinates") or []
        candidates = [coords] if kind == "LineString" else coords if kind == "MultiLineString" else []
        for part in candidates:
            if isinstance(part, list) and len(part) >= 2:
                parts.append([[float(p[0]), float(p[1])] for p in part])
    return parts


def _part_length_km(part: list[list[float]]) -> float:
    return sum(_km(a, b) for a, b in zip(part, part[1:]))


def place_names_from_project_name(name: str | None) -> tuple[list[str], list[str]]:
    """Candidate names for the first and the last place in a project name.

    "Hochleistungskorridorsanierung Stuttgart – Ulm" → (["…sanierung Stuttgart",
    "Stuttgart"], ["Ulm"]): the first place is a suffix of the text before the
    first dash, the last place a prefix of the text after the last dash. Longer
    candidates come first so "Bad Cannstatt" wins over "Cannstatt". Returns two
    empty lists when the name names no route ("Bf Seebergen").
    """
    if not name:
        return [], []
    parts = [p.strip() for p in _PLACE_SPLIT.split(_PARENTHESES.sub(" ", name)) if p.strip()]
    if len(parts) < 2:
        return [], []
    first_words = parts[0].split()
    last_words = parts[-1].split()
    starts = [
        " ".join(first_words[-n:]) for n in range(min(MAX_PLACE_WORDS, len(first_words)), 0, -1)
    ]
    ends = [" ".join(last_words[:n]) for n in range(min(MAX_PLACE_WORDS, len(last_words)), 0, -1)]
    return starts, ends


def _chord_finding(parts: list[list[list[float]]], total_km: float) -> dict[str, Any] | None:
    chords = [p for p in parts if len(p) == 2 and _part_length_km(p) >= CHORD_MIN_KM]
    if not chords or total_km <= 0:
        return None
    chord_km = sum(_part_length_km(p) for p in chords)
    share = chord_km / total_km
    if share < CHORD_SHARE_THRESHOLD:
        return None
    return {
        "check": "chords",
        "message": (
            f"{len(chords)} von {len(parts)} Linienteilen sind gerade Zweipunkt-Sehnen "
            f"({share:.0%} der Länge) — vermutlich skizziert statt geroutet."
        ),
        "chord_segments": len(chords),
        "line_parts": len(parts),
        "chord_share": _round(share),
    }


def _components(parts: list[list[list[float]]], tolerance_km: float) -> list[list[int]]:
    """Group line parts whose ends touch (within the tolerance)."""
    parent = list(range(len(parts)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    ends = [(p[0], p[-1]) for p in parts]
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            if find(i) == find(j):
                continue
            if any(_km(a, b) <= tolerance_km for a in ends[i] for b in ends[j]):
                parent[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for i in range(len(parts)):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def _gap_finding(parts: list[list[list[float]]], tolerance_km: float) -> dict[str, Any] | None:
    components = _components(parts, tolerance_km)
    if len(components) < 2:
        return None
    # Minimum spanning tree over the components (Prim): the smallest jumps needed
    # to connect everything are the gaps.
    ends = [[parts[i][0] for i in c] + [parts[i][-1] for i in c] for c in components]
    connected = {0}
    gaps: list[dict[str, Any]] = []
    while len(connected) < len(components):
        best: tuple[float, int, list[float], list[float]] | None = None
        for i in connected:
            for j in range(len(components)):
                if j in connected:
                    continue
                for a in ends[i]:
                    for b in ends[j]:
                        d = _km(a, b)
                        if best is None or d < best[0]:
                            best = (d, j, a, b)
        assert best is not None
        distance, j, a, b = best
        connected.add(j)
        gaps.append({"distance_km": _round(distance), "from": _rounded(a), "to": _rounded(b)})
    gaps.sort(key=lambda g: g["distance_km"], reverse=True)
    return {
        "check": "gaps",
        "message": (
            f"Die Linien zerfallen in {len(components)} nicht verbundene Teile; "
            f"größte Lücke {gaps[0]['distance_km']} km."
        ),
        "components": len(components),
        "largest_gaps": gaps[:MAX_REPORTED_GAPS],
    }


def _rounded(position: list[float]) -> list[float]:
    return [round(position[0], 5), round(position[1], 5)]


def _station_findings(
    parts: list[list[list[float]]], stations: list[Station], max_distance_km: float
) -> list[dict[str, Any]]:
    vertices = [v for part in parts for v in part]
    findings = []
    for station in stations:
        position = [station.lon, station.lat]
        distance = min(_km(position, v) for v in vertices)
        if distance <= max_distance_km:
            continue
        label = "Anfang" if station.role == "start" else "Ende"
        findings.append(
            {
                "check": f"far_from_{station.role}",
                "message": (
                    f"{label} laut Projektname ist {station.name}"
                    f"{f' ({station.op_id})' if station.op_id else ''}, die Linie kommt ihr "
                    f"aber nur auf {distance:.1f} km nahe."
                ),
                "operational_point": station.name,
                "op_id": station.op_id,
                "distance_km": _round(distance),
            }
        )
    return findings


def _length_finding(stored_km: float | None, computed_km: float | None) -> dict[str, Any] | None:
    if computed_km is None:
        return None
    if stored_km is None or stored_km <= 0:
        return {
            "check": "length_missing",
            "message": f"Keine Länge gespeichert; aus der Geometrie ergeben sich {computed_km} km.",
            "computed_length_km": computed_km,
        }
    difference = abs(stored_km - computed_km)
    if difference <= max(LENGTH_TOLERANCE_KM, LENGTH_TOLERANCE_SHARE * computed_km):
        return None
    return {
        "check": "length_mismatch",
        "message": (
            f"Gespeicherte Länge {stored_km} km weicht von der berechneten "
            f"({computed_km} km) um {difference:.2f} km ab."
        ),
        "stored_length_km": stored_km,
        "computed_length_km": computed_km,
    }


def check_features(
    features: list[dict[str, Any]],
    *,
    stored_length_km: float | None,
    stations: list[Station] = (),
    gap_tolerance_km: float = DEFAULT_GAP_TOLERANCE_KM,
    max_station_distance_km: float = DEFAULT_STATION_DISTANCE_KM,
) -> list[dict[str, Any]]:
    """All findings for one geometry; an empty list means nothing stood out."""
    if not features:
        return [{"check": "no_geometry", "message": "Keine Geometrie."}]
    parts = line_parts(features)
    if not parts:
        return [{"check": "no_line", "message": "Die Geometrie enthält nur Punkte, keine Linie."}]

    total_km = sum(_part_length_km(p) for p in parts)
    computed_km = round(total_km, 2) if total_km > 0 else None
    findings = [
        f
        for f in (
            _chord_finding(parts, total_km),
            _gap_finding(parts, gap_tolerance_km),
        )
        if f is not None
    ]
    findings.extend(_station_findings(parts, list(stations), max_station_distance_km))
    length = _length_finding(stored_length_km, computed_km)
    if length is not None:
        findings.append(length)
    return findings
