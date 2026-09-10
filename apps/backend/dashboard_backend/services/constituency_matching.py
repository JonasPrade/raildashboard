"""Intersection of project geometries with constituency outlines.

The result is materialised in ``project_to_constituency``: a request never pays
for a ``ST_Intersection`` over the whole portfolio, and the rows are refreshed
wherever the project geometry is refreshed (see ``crud/projects/projects.py``).

Weighting rather than a binary link, because the difference carries the argument:
51 km in one constituency and 3 km in another are not the same thing in a
conversation. Point geometries (a station project has no kilometres, only a
location) are weighted by their share of the project's points instead.

Everything here is PostGIS. The API test suite runs on SQLite, which has no
spatial functions at all — on any non-PostgreSQL dialect the recompute is a
documented no-op so that saving a project keeps working.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from dashboard_backend.models.associations.project_to_constituency import (
    OVERLAP_KIND_LINE,
    OVERLAP_KIND_POINT,
    ProjectToConstituency,
)
from dashboard_backend.models.projects import Project

logger = logging.getLogger(__name__)

_LINE_TYPES = {"LineString", "MultiLineString", "Polygon", "MultiPolygon"}
_POINT_TYPES = {"Point", "MultiPoint"}

# One statement per project. The GiST index on ``constituency.geom`` carries the
# ``&&`` prefilter, so only the handful of constituencies whose bounding box
# overlaps is ever measured.
#
# ``::geography`` gives true metres on the ellipsoid without reprojecting, and
# ``ST_UnaryUnion`` collapses lines that appear twice in an aggregated
# FeatureCollection (a parent project holds the union of its subprojects, and the
# same section may be stored on two of them) so they are not counted twice.
_INTERSECT_SQL = text(
    """
    WITH proj AS (
        SELECT
            ST_UnaryUnion(ST_SetSRID(ST_GeomFromGeoJSON(:lines), 4326)) AS lines,
            ST_SetSRID(ST_GeomFromGeoJSON(:points), 4326) AS points
    ),
    totals AS (
        SELECT
            COALESCE(ST_Length(lines::geography), 0.0) AS total_length_m,
            COALESCE(ST_NPoints(points), 0) AS total_points
        FROM proj
    )
    SELECT
        c.id AS constituency_id,
        COALESCE(ST_Length(ST_Intersection(p.lines, c.geom)::geography), 0.0) AS length_m,
        COALESCE(ST_NPoints(ST_Intersection(p.points, c.geom)), 0) AS point_count,
        t.total_length_m,
        t.total_points
    FROM constituency c
    JOIN parliament_period pp ON pp.id = c.parliament_period_id AND pp.is_current
    CROSS JOIN proj p
    CROSS JOIN totals t
    WHERE c.geom IS NOT NULL
      AND ST_Collect(p.lines, p.points) && c.geom
      AND ST_Intersects(ST_Collect(p.lines, p.points), c.geom)
    """
)


@dataclass
class RecomputeStats:
    projects_total: int = 0
    projects_with_geometry: int = 0
    projects_linked: int = 0
    links_written: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "projects_total": self.projects_total,
            "projects_with_geometry": self.projects_with_geometry,
            "projects_linked": self.projects_linked,
            "links_written": self.links_written,
        }


def is_spatial_backend(db: Session) -> bool:
    """True on PostgreSQL/PostGIS — the only place the intersection can run."""
    bind = db.get_bind()
    return bool(bind is not None and bind.dialect.name == "postgresql")


def split_geometries(geojson_str: str | None) -> tuple[list[dict], list[dict]]:
    """Split a ``geojson_representation`` into line-ish and point geometries.

    Polygons are treated like lines (their outline is measured); in the portfolio
    they barely occur, but they must not silently disappear.
    """
    if not geojson_str:
        return [], []
    try:
        parsed = json.loads(geojson_str)
    except (json.JSONDecodeError, TypeError):
        return [], []

    geometries: list[dict] = []

    def collect(node: Any) -> None:
        if not isinstance(node, dict):
            return
        node_type = node.get("type")
        if node_type == "FeatureCollection":
            for feature in node.get("features") or []:
                collect(feature)
        elif node_type == "Feature":
            collect(node.get("geometry"))
        elif node_type == "GeometryCollection":
            for geometry in node.get("geometries") or []:
                collect(geometry)
        elif node_type in _LINE_TYPES or node_type in _POINT_TYPES:
            if node.get("coordinates"):
                geometries.append(node)

    collect(parsed)
    lines = [g for g in geometries if g["type"] in _LINE_TYPES]
    points = [g for g in geometries if g["type"] in _POINT_TYPES]
    return lines, points


def _geometry_collection(geometries: Sequence[dict]) -> str | None:
    if not geometries:
        return None
    return json.dumps({"type": "GeometryCollection", "geometries": list(geometries)})


def compute_links_for_project(db: Session, project: Project) -> int:
    """Rewrite the constituency links of one project. Returns the row count.

    A project without geometry simply ends up with no rows — that is the honest
    answer, and the UI says so instead of showing an empty list.
    """
    db.query(ProjectToConstituency).filter(
        ProjectToConstituency.project_id == project.id
    ).delete(synchronize_session=False)

    lines, points = split_geometries(project.geojson_representation)
    if not lines and not points:
        return 0
    if not is_spatial_backend(db):
        logger.debug(
            "skipping constituency matching for project %s: no PostGIS backend", project.id
        )
        return 0

    rows = db.execute(
        _INTERSECT_SQL,
        {"lines": _geometry_collection(lines), "points": _geometry_collection(points)},
    ).mappings().all()

    now = datetime.utcnow()
    written = 0
    for row in rows:
        length_km = round((row["length_m"] or 0.0) / 1000.0, 3)
        total_length_m = row["total_length_m"] or 0.0
        total_points = row["total_points"] or 0
        point_count = row["point_count"] or 0

        if length_km > 0 and total_length_m > 0:
            kind = OVERLAP_KIND_LINE
            share = (row["length_m"] or 0.0) / total_length_m
        elif point_count > 0 and total_points > 0:
            kind = OVERLAP_KIND_POINT
            share = point_count / total_points
        else:
            # Touches the outline without covering length or a point — not a
            # statement anyone could use in a conversation.
            continue

        db.add(
            ProjectToConstituency(
                project_id=project.id,
                constituency_id=row["constituency_id"],
                length_km=length_km,
                share=round(min(share, 1.0), 6),
                overlap_kind=kind,
                computed_at=now,
            )
        )
        written += 1
    return written


def recompute_links_for_project_ids(db: Session, project_ids: Iterable[int]) -> int:
    """Recompute the links of the given projects and commit."""
    ids = [pid for pid in dict.fromkeys(project_ids) if pid is not None]
    if not ids:
        return 0
    written = 0
    for project in db.query(Project).filter(Project.id.in_(ids)).all():
        written += compute_links_for_project(db, project)
    db.commit()
    return written


def recompute_all_links(db: Session) -> RecomputeStats:
    """Full rebuild over the whole portfolio.

    Needed after a geometry import or a new legislative period — not in daily
    operation, where the per-project recompute keeps the table current.
    """
    stats = RecomputeStats()
    stats.projects_total = db.query(Project.id).count()
    projects = (
        db.query(Project)
        .filter(Project.geojson_representation.isnot(None))
        .order_by(Project.id)
        .all()
    )
    stats.projects_with_geometry = len(projects)
    for project in projects:
        written = compute_links_for_project(db, project)
        if written:
            stats.projects_linked += 1
            stats.links_written += written
    db.commit()
    return stats


def coverage(db: Session) -> dict[str, int]:
    """How much of the portfolio the feature can actually speak about."""
    projects_total = db.query(Project.id).count()
    with_geometry = (
        db.query(Project.id).filter(Project.geojson_representation.isnot(None)).count()
    )
    linked = db.query(ProjectToConstituency.project_id).distinct().count()
    return {
        "projects_total": projects_total,
        "projects_with_geometry": with_geometry,
        "projects_without_geometry": projects_total - with_geometry,
        "projects_linked": linked,
    }
