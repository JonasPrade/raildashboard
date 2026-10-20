"""Data-maintenance tools across many projects (issue #175, stage A).

``list_data_gaps`` finds missing data in one query instead of one get_* call per
project; ``check_geometry`` runs the plausibility checks from
``services/geometry_check.py`` for one project or a whole group. Both are
read-only: fixes go through the existing write tools (route_project_geometry,
edit_project_geometry, compute_project_length, update_project, …).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy import and_, exists, func, not_, or_, select
from sqlalchemy.orm import Session, aliased, selectinload

from dashboard_backend.crud import infraplan_import as infraplan_crud
from dashboard_backend.crud.projects.projects import extract_features, has_subprojects
from dashboard_backend.mcp.context import get_principal, tool_session
from dashboard_backend.mcp.tools.projects import (
    MAX_LIMIT,
    READ_ONLY,
    _group_filter,
    _project_or_error,
    has_geometry_expr,
    has_length_expr,
    is_known_expr,
)
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.railway_infrastructure.operational_point import OperationalPoint
from dashboard_backend.models.routes import Route
from dashboard_backend.services.geometry_check import (
    DEFAULT_GAP_TOLERANCE_KM,
    DEFAULT_STATION_DISTANCE_KM,
    Station,
    check_features,
    place_names_from_project_name,
)

GapLiteral = Literal[
    "no_geometry",
    "no_route",
    "no_length",
    "unknown_phase",
    "no_description",
    "no_project_number",
    "stale_observation",
    "infraplan_unassigned",
]
ALL_GAPS: tuple[str, ...] = GapLiteral.__args__
# Not a gap of a project but of the data: rows of the newest Infraplan year
# without a project. Reported next to the project list.
ENTRY_GAPS = ("infraplan_unassigned",)
_MAX_ENTRY_SAMPLE = 50
DEFAULT_STALE_YEARS = 3


def _blank(column):
    return or_(column.is_(None), func.trim(column) == "")


def _resolve_group(db: Session, project_group: str) -> ProjectGroup:
    group = db.query(ProjectGroup).filter(_group_filter(project_group)).first()
    if group is None:
        raise ToolError(f"Projektgruppe '{project_group}' nicht gefunden.")
    return group


def _today() -> date:
    return date.today()


def list_data_gaps(
    project_group: str | None = None,
    gaps: list[GapLiteral] | None = None,
    stale_years: int = DEFAULT_STALE_YEARS,
    limit: int = 50,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Projects with missing or outdated data (drafts excluded), with the gaps
    that apply to each — one call instead of reading every project.

    - project_group: id, short name or name (see list_project_groups); default all
    - gaps: which gaps to look for (default all); a project is listed when at
      least one of them applies:
      no_geometry (no line or point stored), no_route (geometry but no saved
      GraphHopper route — sketched or hand-drawn; projects whose geometry comes
      from their subprojects are skipped), no_length, unknown_phase (planning
      state not backed by an observation or override), no_description,
      no_project_number, stale_observation (newest observation older than
      ``stale_years``; forecasts are ignored), infraplan_unassigned (rows of
      the newest Infraplan year without a project — returned separately as
      ``infraplan_unassigned``, fix with assign_infraplan_row)
    Returns ``counts`` per gap over all matches plus one page of projects.
    Follow up with check_geometry, compute_project_length, update_project, …
    """
    get_principal(ctx)
    requested = list(dict.fromkeys(gaps or ALL_GAPS))
    wanted = [g for g in requested if g not in ENTRY_GAPS]
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    stale_years = max(1, stale_years)
    today = _today()
    try:
        cutoff = today.replace(year=today.year - stale_years)
    except ValueError:  # 29 February
        cutoff = today.replace(year=today.year - stale_years, day=28)

    child = aliased(Project)
    aggregating = and_(
        Project.geojson_from_subprojects.is_(True),
        exists().where(child.superior_project_id == Project.id),
    )
    has_route = exists().where(Route.project_id == Project.id)
    last_observation = (
        select(func.max(ProgressObservation.observed_date))
        .where(
            ProgressObservation.project_id == Project.id,
            ProgressObservation.is_expected.is_(False),
        )
        .correlate(Project)
        .scalar_subquery()
    )
    has_geometry = has_geometry_expr()
    flags = {
        "no_geometry": not_(has_geometry),
        "no_route": and_(has_geometry, not_(has_route), not_(aggregating)),
        "no_length": not_(has_length_expr()),
        "unknown_phase": not_(is_known_expr()),
        "no_description": _blank(Project.description),
        "no_project_number": _blank(Project.project_number),
        "stale_observation": and_(last_observation.isnot(None), last_observation < cutoff),
    }

    with tool_session(ctx) as db:
        extra: dict[str, Any] = {}
        if "infraplan_unassigned" in requested:
            open_entries = infraplan_crud.unassigned_entries(db)
            extra["infraplan_unassigned"] = {
                "year": open_entries[0][1] if open_entries else None,
                "draft_id": _draft_of_newest_year(db),
                "count": len(open_entries),
                "entries": [
                    {
                        "entry_id": e.id,
                        "row_key": f"{e.section}-{e.lfd_nr}",
                        "primary_number": e.primary_number,
                        "bezeichnung": e.bezeichnung,
                        "massnahme": e.massnahme,
                    }
                    for e, _year in open_entries[:_MAX_ENTRY_SAMPLE]
                ],
            }
            if not wanted:
                return {"total": 0, "offset": offset, "limit": limit, "counts": {}, "projects": [], **extra}
        query = (
            db.query(Project.id, *(flags[g].label(g) for g in wanted))
            .outerjoin(ProjectProgress, ProjectProgress.project_id == Project.id)
            .filter(Project.is_draft.is_(False))
            .filter(or_(*(flags[g] for g in wanted)))
            .order_by(Project.name, Project.id)
        )
        if project_group:
            group = _resolve_group(db, project_group)
            query = query.filter(Project.project_groups.any(ProjectGroup.id == group.id))
        rows = query.all()

        counts = {g: sum(1 for row in rows if getattr(row, g)) for g in wanted}
        page = rows[offset : offset + limit]
        projects = {
            p.id: p
            for p in db.query(Project)
            .options(selectinload(Project.project_groups))
            .filter(Project.id.in_([row.id for row in page]))
            .all()
        }
        return {
            "total": len(rows),
            "offset": offset,
            "limit": limit,
            "counts": counts,
            "stale_before": cutoff.isoformat() if "stale_observation" in wanted else None,
            "projects": [
                {
                    "id": row.id,
                    "name": projects[row.id].name,
                    "project_number": projects[row.id].project_number,
                    "superior_project_id": projects[row.id].superior_project_id,
                    "project_groups": [g.short_name for g in projects[row.id].project_groups],
                    "gaps": [g for g in wanted if getattr(row, g)],
                }
                for row in page
            ],
            **extra,
        }


def _draft_of_newest_year(db: Session) -> int | None:
    report = infraplan_crud.newest_report(db)
    return report.parse_result_id if report is not None else None


class _StationResolver:
    """Find the operational point a place name in a project name stands for:
    the exact name, else "<name> Hbf". Results are cached across one tool call."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._cache: dict[str, OperationalPoint | None] = {}

    def _lookup(self, text: str) -> OperationalPoint | None:
        lowered = text.lower()
        if lowered not in self._cache:
            match = None
            for candidate in (lowered, f"{lowered} hbf"):
                match = (
                    self._db.query(OperationalPoint)
                    .filter(
                        func.lower(OperationalPoint.name) == candidate,
                        OperationalPoint.latitude.isnot(None),
                        OperationalPoint.longitude.isnot(None),
                    )
                    .order_by(OperationalPoint.id)
                    .first()
                )
                if match is not None:
                    break
            self._cache[lowered] = match
        return self._cache[lowered]

    def resolve(self, role: str, candidates: list[str]) -> tuple[Station | None, str | None]:
        """The station for the longest matching candidate, else the unmatched place."""
        for text in candidates:
            op = self._lookup(text)
            if op is not None:
                return (
                    Station(
                        role=role,
                        query=text,
                        name=op.name,
                        op_id=op.op_id,
                        lon=op.longitude,
                        lat=op.latitude,
                    ),
                    None,
                )
        return None, candidates[-1] if candidates else None


def _check_project(
    db: Session,
    project: Project,
    resolver: _StationResolver,
    gap_tolerance_km: float,
    max_station_distance_km: float,
) -> dict[str, Any]:
    starts, ends = place_names_from_project_name(project.name)
    stations: list[Station] = []
    unresolved: list[str] = []
    for role, candidates in (("start", starts), ("end", ends)):
        station, missing = resolver.resolve(role, candidates)
        if station is not None:
            stations.append(station)
        elif missing:
            unresolved.append(missing)

    findings = check_features(
        extract_features(project.geojson_representation),
        stored_length_km=project.length,
        stations=stations,
        gap_tolerance_km=gap_tolerance_km,
        max_station_distance_km=max_station_distance_km,
    )
    has_route = db.query(exists().where(Route.project_id == project.id)).scalar()
    return {
        "id": project.id,
        "name": project.name,
        "aggregated_from_subprojects": bool(project.geojson_from_subprojects)
        and has_subprojects(db, project.id),
        "has_saved_route": bool(has_route),
        "stations_from_name": [
            {"role": s.role, "name": s.name, "op_id": s.op_id} for s in stations
        ],
        "unresolved_places": unresolved,
        "findings": findings,
    }


def check_geometry(
    project_id: int | None = None,
    project_group: str | None = None,
    only_findings: bool = True,
    gap_tolerance_km: float = DEFAULT_GAP_TOLERANCE_KM,
    max_station_distance_km: float = DEFAULT_STATION_DISTANCE_KM,
    limit: int = 50,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Plausibility check of project geometries — for one project (project_id)
    or all projects of a group (project_group: id, short name or name). Read-only.

    Findings per project (``check``):
    - chords: mostly straight two-point segments — sketched, not routed
    - gaps: lines fall apart into unconnected parts (largest gaps with coordinates;
      line ends within ``gap_tolerance_km`` count as connected)
    - far_from_start / far_from_end: the first/last place in the project name
      ("Stuttgart – Ulm") resolves to an operational point (exact name, else
      "<name> Hbf") more than ``max_station_distance_km`` away from the line
    - length_mismatch / length_missing: stored length vs. length from geometry
    - no_geometry / no_line
    Places in the name that match no operational point are listed as
    ``unresolved_places`` (not a finding). For a group, ``only_findings`` (default)
    lists only projects with findings; ``total`` counts them. Fix with
    route_project_geometry, edit_project_geometry or compute_project_length.
    """
    get_principal(ctx)
    if (project_id is None) == (project_group is None):
        raise ToolError("Genau eines angeben: project_id oder project_group.")
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    gap_tolerance_km = max(0.0, gap_tolerance_km)
    max_station_distance_km = max(0.0, max_station_distance_km)

    with tool_session(ctx) as db:
        resolver = _StationResolver(db)
        if project_id is not None:
            project = _project_or_error(db, project_id)
            return _check_project(db, project, resolver, gap_tolerance_km, max_station_distance_km)

        group = _resolve_group(db, project_group)
        projects = (
            db.query(Project)
            .filter(Project.is_draft.is_(False))
            .filter(Project.project_groups.any(ProjectGroup.id == group.id))
            .order_by(Project.name, Project.id)
            .all()
        )
        results = [
            _check_project(db, p, resolver, gap_tolerance_km, max_station_distance_km)
            for p in projects
        ]
        counts: dict[str, int] = {}
        for result in results:
            for finding in result["findings"]:
                counts[finding["check"]] = counts.get(finding["check"], 0) + 1
        listed = [r for r in results if r["findings"]] if only_findings else results
        return {
            "project_group": group.short_name,
            "checked": len(results),
            "total": len(listed),
            "offset": offset,
            "limit": limit,
            "counts": counts,
            "projects": listed[offset : offset + limit],
        }


def register(server: MCPServer) -> None:
    server.add_tool(list_data_gaps, annotations=READ_ONLY)
    server.add_tool(check_geometry, annotations=READ_ONLY)
