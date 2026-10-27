"""Projects whose lines run along the same track, and their lanes on the map.

docs/features/feature-map-overlapping-geometries.md → B1. Two projects overlap
when their lines run within ``BUFFER_M`` of each other over a shared length of
at least ``MIN_SHARED_KM`` — or, for short projects, over at least
``MIN_SHARE`` of the shorter line (and ``MIN_SHARED_KM_SHORT``). The pairs are
materialised in ``project_overlap``; each project gets a stored lane that its
overlap partners do not hold. The overview map recolours only the projects it
shows, using the stored lane as the preferred order.

Why Shapely and not PostGIS: the project geometry is GeoJSON text, there is no
geometry column to index, so PostGIS would parse both texts per pair just like
Python does. Shapely runs on SQLite too, which keeps the logic testable in
``make test``. Distances are measured in a local equirectangular projection
around the pair — exact enough for 25 m.

Recomputed wherever the constituency links are (``refresh_derived_geometry`` in
``crud/projects/projects.py``): a request never pays for it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any, Iterable, Iterator, Optional

import shapely
from shapely.geometry import MultiLineString
from shapely.geometry.base import BaseGeometry
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_map_geometry import (
    ProjectMapGeometry,
    ProjectOverlap,
)

logger = logging.getLogger(__name__)

# Two routings of the same track, or the two tracks of a double-track line, lie
# a few metres apart; separate parallel lines on their own formation usually
# more than 25 m.
BUFFER_M = 25.0
# Shared length from which two projects overlap (W4) ...
MIN_SHARED_KM = 0.5
# ... or, for a short project, this share of the shorter line ...
MIN_SHARE = 0.5
# ... as long as at least this much is shared.
MIN_SHARED_KM_SHORT = 0.1

_M_PER_DEG_LAT = 110_574.0
_M_PER_DEG_LON_EQUATOR = 111_320.0

_CACHE_MAX_ENTRIES = 4096
_line_cache: "OrderedDict[str, Optional[BaseGeometry]]" = OrderedDict()
_cache_lock = Lock()


# ── geometry ────────────────────────────────────────────────────────────────


def geometry_hash(geojson_text: str) -> str:
    return hashlib.sha1(geojson_text.encode("utf-8")).hexdigest()


def _iter_geometries(node: Any) -> Iterator[dict]:
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


def _clean_part(coords: Any) -> Optional[list[tuple[float, float]]]:
    if not isinstance(coords, list):
        return None
    clean = []
    for coord in coords:
        if not isinstance(coord, (list, tuple)) or len(coord) < 2:
            continue
        x, y = coord[0], coord[1]
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and math.isfinite(x) and math.isfinite(y):
            clean.append((float(x), float(y)))
    return clean if len(clean) >= 2 else None


def _parse_lines(geojson_text: str) -> Optional[BaseGeometry]:
    try:
        document = json.loads(geojson_text)
    except (TypeError, ValueError):
        return None
    parts: list[list[tuple[float, float]]] = []
    for geometry in _iter_geometries(document):
        coords = geometry.get("coordinates")
        if geometry.get("type") == "LineString":
            candidates = [coords]
        elif geometry.get("type") == "MultiLineString" and isinstance(coords, list):
            candidates = coords
        else:
            continue
        for candidate in candidates:
            part = _clean_part(candidate)
            if part is not None:
                parts.append(part)
    if not parts:
        return None
    # A parent holds the union of its subprojects, and the same section may be
    # stored twice; the union collapses repeats so nothing is counted double.
    lines = shapely.unary_union(MultiLineString(parts))
    return None if lines.is_empty or lines.length == 0 else lines


def project_lines(geojson_text: Optional[str]) -> Optional[BaseGeometry]:
    """The project's lines in lon/lat (2D, unioned), or None. Memoised by text hash."""
    if not geojson_text:
        return None
    key = geometry_hash(geojson_text)
    with _cache_lock:
        if key in _line_cache:
            _line_cache.move_to_end(key)
            return _line_cache[key]
    lines = _parse_lines(geojson_text)
    with _cache_lock:
        _line_cache[key] = lines
        if len(_line_cache) > _CACHE_MAX_ENTRIES:
            _line_cache.popitem(last=False)
    return lines


def clear_cache() -> None:
    with _cache_lock:
        _line_cache.clear()


def _to_metres(geometry: BaseGeometry, lat0: float) -> BaseGeometry:
    scale_x = _M_PER_DEG_LON_EQUATOR * math.cos(math.radians(lat0))
    return shapely.transform(geometry, lambda c: c * [scale_x, _M_PER_DEG_LAT])


def line_km(lines: BaseGeometry) -> float:
    min_lon, min_lat, max_lon, max_lat = lines.bounds
    return _to_metres(lines, (min_lat + max_lat) / 2).length / 1000.0


@dataclass(frozen=True)
class Overlap:
    shared_km: float
    share_a: float
    share_b: float


def measure_overlap(a: BaseGeometry, b: BaseGeometry) -> Overlap:
    """Length the two lines share within ``BUFFER_M``, in km and as shares.

    Measured both ways and the smaller taken: a line that merely touches the
    other's buffer at a crossing must not count as running along it.
    """
    lat0 = (a.bounds[1] + a.bounds[3] + b.bounds[1] + b.bounds[3]) / 4
    am, bm = _to_metres(a, lat0), _to_metres(b, lat0)
    shared_m = min(
        bm.intersection(am.buffer(BUFFER_M)).length,
        am.intersection(bm.buffer(BUFFER_M)).length,
    )
    length_a, length_b = am.length, bm.length
    return Overlap(
        shared_km=shared_m / 1000.0,
        share_a=min(1.0, shared_m / length_a) if length_a else 0.0,
        share_b=min(1.0, shared_m / length_b) if length_b else 0.0,
    )


def is_overlap(overlap: Overlap) -> bool:
    """The threshold (W4): 500 m shared, or half of the shorter line (≥ 100 m)."""
    if overlap.shared_km >= MIN_SHARED_KM:
        return True
    return (
        overlap.shared_km >= MIN_SHARED_KM_SHORT
        and max(overlap.share_a, overlap.share_b) >= MIN_SHARE
    )


def _expanded_bounds(bounds: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    min_lon, min_lat, max_lon, max_lat = bounds
    d_lat = BUFFER_M / _M_PER_DEG_LAT
    cos_lat = max(0.1, math.cos(math.radians(max(abs(min_lat), abs(max_lat)))))
    d_lon = BUFFER_M / (_M_PER_DEG_LON_EQUATOR * cos_lat)
    return min_lon - d_lon, min_lat - d_lat, max_lon + d_lon, max_lat + d_lat


# ── lanes ───────────────────────────────────────────────────────────────────


def smallest_free_lane(taken: Iterable[int], preferred: Optional[int] = None) -> int:
    """*preferred* when no partner holds it, else the smallest lane nobody holds."""
    taken_set = set(taken)
    if preferred is not None and preferred not in taken_set:
        return preferred
    lane = 0
    while lane in taken_set:
        lane += 1
    return lane


def color_graph(nodes: Iterable[int], edges: Iterable[tuple[int, int]]) -> dict[int, int]:
    """Greedy colouring by descending degree (ties by id): a lane per node that
    none of its neighbours holds. Used for the initial fill."""
    neighbours: dict[int, set[int]] = {node: set() for node in nodes}
    for a, b in edges:
        neighbours.setdefault(a, set()).add(b)
        neighbours.setdefault(b, set()).add(a)
    lanes: dict[int, int] = {}
    for node in sorted(neighbours, key=lambda n: (-len(neighbours[n]), n)):
        lanes[node] = smallest_free_lane(lanes[n] for n in neighbours[node] if n in lanes)
    return lanes


# ── persistence ─────────────────────────────────────────────────────────────


def _is_drawn(project: Project) -> bool:
    return not project.is_draft and not project.is_archived


def _drawn_projects():
    return (Project.is_draft.is_(False), Project.is_archived.is_(False))


def _forget(db: Session, project_id: int) -> None:
    db.query(ProjectOverlap).filter(
        or_(ProjectOverlap.project_a_id == project_id, ProjectOverlap.project_b_id == project_id)
    ).delete(synchronize_session=False)
    db.query(ProjectMapGeometry).filter(ProjectMapGeometry.project_id == project_id).delete(
        synchronize_session=False
    )


def partner_ids(db: Session, project_id: int) -> list[int]:
    rows = (
        db.query(ProjectOverlap.project_a_id, ProjectOverlap.project_b_id)
        .filter(
            or_(ProjectOverlap.project_a_id == project_id, ProjectOverlap.project_b_id == project_id)
        )
        .all()
    )
    return [b if a == project_id else a for a, b in rows]


def _write_pair(db: Session, p: int, q: int, overlap: Overlap, now: datetime) -> None:
    a, b = (p, q) if p < q else (q, p)
    share_a, share_b = (overlap.share_a, overlap.share_b) if p < q else (overlap.share_b, overlap.share_a)
    db.add(
        ProjectOverlap(
            project_a_id=a,
            project_b_id=b,
            shared_km=round(overlap.shared_km, 3),
            share_a=round(share_a, 4),
            share_b=round(share_b, 4),
            computed_at=now,
        )
    )


def compute_overlaps_for_project(db: Session, project: Project) -> None:
    """Refresh the map row, the overlap pairs and the lane of one project.

    Partners keep their lanes; the project keeps its own unless a partner holds
    it (W3). Does not commit.
    """
    lines = project_lines(project.geojson_representation) if _is_drawn(project) else None
    if lines is None:
        _forget(db, project.id)
        return

    digest = geometry_hash(project.geojson_representation)
    row = db.get(ProjectMapGeometry, project.id)
    if row is not None and row.geometry_hash == digest:
        return

    now = datetime.utcnow()
    min_lon, min_lat, max_lon, max_lat = lines.bounds
    if row is None:
        row = ProjectMapGeometry(project_id=project.id, lane=0)
        db.add(row)
    row.min_lon, row.min_lat, row.max_lon, row.max_lat = min_lon, min_lat, max_lon, max_lat
    row.line_km = round(line_km(lines), 3)
    row.geometry_hash = digest
    row.computed_at = now

    db.query(ProjectOverlap).filter(
        or_(ProjectOverlap.project_a_id == project.id, ProjectOverlap.project_b_id == project.id)
    ).delete(synchronize_session=False)

    e_min_lon, e_min_lat, e_max_lon, e_max_lat = _expanded_bounds(lines.bounds)
    candidates = (
        db.query(Project.id, Project.geojson_representation)
        .join(ProjectMapGeometry, ProjectMapGeometry.project_id == Project.id)
        .filter(
            Project.id != project.id,
            *_drawn_projects(),
            ProjectMapGeometry.max_lon >= e_min_lon,
            ProjectMapGeometry.min_lon <= e_max_lon,
            ProjectMapGeometry.max_lat >= e_min_lat,
            ProjectMapGeometry.min_lat <= e_max_lat,
        )
        .all()
    )
    partners: list[int] = []
    for candidate_id, candidate_text in candidates:
        candidate_lines = project_lines(candidate_text)
        if candidate_lines is None:
            continue
        overlap = measure_overlap(lines, candidate_lines)
        if is_overlap(overlap):
            _write_pair(db, project.id, candidate_id, overlap, now)
            partners.append(candidate_id)

    taken = [
        lane
        for (lane,) in db.query(ProjectMapGeometry.lane)
        .filter(ProjectMapGeometry.project_id.in_(partners))
        .all()
    ] if partners else []
    row.lane = smallest_free_lane(taken, preferred=row.lane)


def recompute_overlaps_for_project_ids(db: Session, project_ids: Iterable[int]) -> None:
    """Refresh the given projects and commit.

    A savepoint per project: a geometry Shapely cannot digest must not turn
    saving a project into an error — that project is left as it was, and the
    log says why.
    """
    ids = [pid for pid in dict.fromkeys(project_ids) if pid is not None]
    if not ids:
        return
    for project in db.query(Project).filter(Project.id.in_(ids)).all():
        try:
            with db.begin_nested():
                compute_overlaps_for_project(db, project)
        except (SQLAlchemyError, ValueError, shapely.errors.GEOSException):
            logger.warning("overlap matching failed for project %s", project.id, exc_info=True)
    db.commit()


@dataclass
class RecomputeStats:
    projects_with_lines: int = 0
    pairs: int = 0
    max_lane: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "projects_with_lines": self.projects_with_lines,
            "pairs": self.pairs,
            "max_lane": self.max_lane,
        }


def recompute_all_overlaps(db: Session) -> RecomputeStats:
    """Full rebuild over the portfolio: rows, pairs and a fresh colouring.

    The initial fill after the deploy and the manual rebuild; in daily
    operation the per-project refresh keeps the tables current.
    """
    stats = RecomputeStats()
    projects = (
        db.query(Project.id, Project.geojson_representation)
        .filter(Project.geojson_representation.isnot(None), *_drawn_projects())
        .order_by(Project.id)
        .all()
    )
    lines_by_id: dict[int, BaseGeometry] = {}
    for project_id, geojson_text in projects:
        lines = project_lines(geojson_text)
        if lines is not None:
            lines_by_id[project_id] = lines
    stats.projects_with_lines = len(lines_by_id)

    ids = list(lines_by_id)
    boxes = [shapely.box(*_expanded_bounds(lines_by_id[pid].bounds)) for pid in ids]
    tree = shapely.STRtree(boxes)
    pairs: dict[tuple[int, int], Overlap] = {}
    for index, pid in enumerate(ids):
        for other in tree.query(boxes[index]):
            qid = ids[int(other)]
            if qid <= pid:
                continue
            overlap = measure_overlap(lines_by_id[pid], lines_by_id[qid])
            if is_overlap(overlap):
                pairs[(pid, qid)] = overlap
    lanes = color_graph(ids, pairs)

    now = datetime.utcnow()
    hashes = {pid: geometry_hash(text) for pid, text in projects if pid in lines_by_id}
    db.query(ProjectOverlap).delete(synchronize_session=False)
    db.query(ProjectMapGeometry).delete(synchronize_session=False)
    for pid in ids:
        min_lon, min_lat, max_lon, max_lat = lines_by_id[pid].bounds
        db.add(
            ProjectMapGeometry(
                project_id=pid,
                min_lon=min_lon,
                min_lat=min_lat,
                max_lon=max_lon,
                max_lat=max_lat,
                line_km=round(line_km(lines_by_id[pid]), 3),
                geometry_hash=hashes[pid],
                lane=lanes.get(pid, 0),
                computed_at=now,
            )
        )
    for (pid, qid), overlap in pairs.items():
        _write_pair(db, pid, qid, overlap, now)
    db.commit()
    stats.pairs = len(pairs)
    stats.max_lane = max(lanes.values(), default=0)
    return stats


def map_lanes(db: Session, project_ids: Iterable[int]) -> dict[int, dict[str, Any]]:
    """Stored lane and overlap partners of the given projects, for the map.

    Only projects with a lane above 0 or at least one partner are listed; the
    partners are all of them, not only those in the same group, so two groups
    shown together still separate (W1).
    """
    ids = list(dict.fromkeys(project_ids))
    if not ids:
        return {}
    result: dict[int, dict[str, Any]] = {}
    for project_id, lane in (
        db.query(ProjectMapGeometry.project_id, ProjectMapGeometry.lane)
        .filter(ProjectMapGeometry.project_id.in_(ids))
        .all()
    ):
        result[project_id] = {"lane": lane or 0, "overlaps": []}
    for a, b in (
        db.query(ProjectOverlap.project_a_id, ProjectOverlap.project_b_id)
        .filter(or_(ProjectOverlap.project_a_id.in_(ids), ProjectOverlap.project_b_id.in_(ids)))
        .order_by(ProjectOverlap.project_a_id, ProjectOverlap.project_b_id)
        .all()
    ):
        if a in result:
            result[a]["overlaps"].append(b)
        if b in result:
            result[b]["overlaps"].append(a)
    return {pid: entry for pid, entry in result.items() if entry["lane"] or entry["overlaps"]}


def is_empty(db: Session) -> bool:
    return db.query(ProjectMapGeometry.project_id).first() is None
