"""Project geometry tools: inspect, route over the rail network, edit by hand.

The same building blocks as the GeometryEditor in the UI: a GraphHopper route
between operational points (plus the stations as points), hand-made lines and
points from coordinates, operational points as points, and deleting single
features. Every write goes through ``update_project`` with a changelog entry, so
it can be reverted in the project history like a geometry saved in the UI.

Coordinates are GeoJSON order ``[lon, lat]`` (WGS84). Outputs stay compact: a
summary per feature by default, the full GeoJSON only on request.
"""

from __future__ import annotations

import json
import math
from typing import Any, Literal

import anyio.from_thread
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from dashboard_backend.crud.changelog import create_changelog_for_patch
from dashboard_backend.crud.projects.projects import (
    extract_features,
    has_subprojects,
    update_project as update_project_crud,
)
from dashboard_backend.crud.routes import list_routes_for_project
from dashboard_backend.mcp.context import (
    get_principal,
    load_user,
    require,
    route_service,
    tool_session,
)
from dashboard_backend.mcp.tools.projects import DESTRUCTIVE, READ_ONLY, _project_or_error
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.railway_infrastructure.operational_point import OperationalPoint
from dashboard_backend.services.exceptions import RoutingNoPathError, RoutingUpstreamError
from dashboard_backend.services.geo_length import compute_geojson_length_km

ROUTING_PROFILE = "rail_default"
# 5 decimals of a degree ≈ 1 m: enough for every map, a third of the characters.
COORD_PRECISION = 5
MAX_SEARCH_LIMIT = 50
_LINE_TYPES = {"LineString", "MultiLineString"}
_POINT_TYPES = {"Point", "MultiPoint"}
# Generous box around Germany; a coordinate outside it is most often lat/lon swapped.
_PLAUSIBLE_LON = (2.0, 20.0)
_PLAUSIBLE_LAT = (45.0, 57.0)


class Coordinate(BaseModel):
    """A free waypoint (WGS84)."""

    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)


# --- helpers -----------------------------------------------------------------


def _round(value: float) -> float:
    return round(float(value), COORD_PRECISION)


def _round_coords(node: Any) -> Any:
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return _round(node)
    if isinstance(node, list):
        return [_round_coords(item) for item in node]
    return node


def _op_dict(op: OperationalPoint) -> dict[str, Any]:
    return {
        "id": op.id,
        "op_id": op.op_id,
        "name": op.name,
        "type": op.type,
        "lat": op.latitude,
        "lon": op.longitude,
    }


def _op_feature(op: OperationalPoint) -> dict[str, Any]:
    # Same shape as the stations the GeometryEditor writes.
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [op.longitude, op.latitude]},
        "properties": {"name": op.name, "op_id": op.op_id, "feature_type": "operational_point"},
    }


def _collection_text(features: list[dict[str, Any]]) -> str | None:
    if not features:
        return None
    return json.dumps({"type": "FeatureCollection", "features": features})


def _bbox(features: list[dict[str, Any]]) -> list[float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, list) and len(node) >= 2 and all(
            isinstance(v, (int, float)) for v in node[:2]
        ):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for feature in features:
        walk((feature.get("geometry") or {}).get("coordinates"))
    if not xs:
        return None
    return [_round(min(xs)), _round(min(ys)), _round(max(xs)), _round(max(ys))]


def _vertex_count(geometry: dict[str, Any]) -> int:
    coords = geometry.get("coordinates")
    kind = geometry.get("type")
    if kind == "Point":
        return 1
    if kind in {"MultiPoint", "LineString"}:
        return len(coords or [])
    if kind == "MultiLineString":
        return sum(len(part) for part in coords or [])
    return 0


def _feature_summary(index: int, feature: dict[str, Any]) -> dict[str, Any]:
    geometry = feature.get("geometry") or {}
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    entry: dict[str, Any] = {"index": index, "type": kind, "vertices": _vertex_count(geometry)}
    properties = feature.get("properties") or {}
    for key in ("name", "op_id", "feature_type"):
        if properties.get(key) is not None:
            entry[key] = properties[key]
    if kind in _LINE_TYPES:
        entry["length_km"] = compute_geojson_length_km(json.dumps(geometry))
        parts = [coords] if kind == "LineString" else coords
        if parts and parts[0] and parts[-1]:
            entry["start"] = _round_coords(parts[0][0])
            entry["end"] = _round_coords(parts[-1][-1])
    elif kind == "Point":
        entry["coordinates"] = _round_coords(coords)
    return entry


def _geometry_summary(features: list[dict[str, Any]]) -> dict[str, Any]:
    text = _collection_text(features)
    return {
        "feature_count": len(features),
        "line_count": sum(
            1 for f in features if (f.get("geometry") or {}).get("type") in _LINE_TYPES
        ),
        "point_count": sum(
            1 for f in features if (f.get("geometry") or {}).get("type") in _POINT_TYPES
        ),
        "length_km": compute_geojson_length_km(text),
        "bbox": _bbox(features),
    }


def _ensure_owns_geometry(db: Session, project: Project) -> None:
    """Mirror of the REST check: an aggregating parent does not own its geometry."""
    if project.geojson_from_subprojects and has_subprojects(db, project.id):
        raise ToolError(
            "Die Geometrie dieses Projekts wird automatisch aus seinen Unterprojekten "
            "zusammengesetzt. Entweder die Unterprojekte bearbeiten oder zuerst mit "
            'update_project {"geojson_from_subprojects": false} eine eigene Geometrie '
            "zulassen."
        )


def _write_geometry(
    db: Session, ctx: Context, project: Project, features: list[dict[str, Any]]
) -> Project:
    # Compare parsed features, not text: a re-serialized but equal geometry is no change.
    if features == extract_features(project.geojson_representation):
        return project
    update_data = {"geojson_representation": _collection_text(features)}
    user = load_user(db, get_principal(ctx))
    create_changelog_for_patch(db, project, update_data, user.id, user.username)
    return update_project_crud(db, project.id, update_data, project=project)


def _write_result(project: Project, features: list[dict[str, Any]], applied: bool) -> dict:
    summary = _geometry_summary(features)
    return {
        "project_id": project.id,
        "applied": applied,
        "geometry": summary,
        "stored_length_km": project.length,
        "hint": (
            "length übernehmen mit compute_project_length(apply=true)"
            if applied and summary["length_km"] is not None and summary["length_km"] != project.length
            else None
        ),
    }


def _lookup_operational_point(db: Session, value: int | str) -> OperationalPoint:
    """Resolve an operational point by database id (int), or by op_id / name (str):
    exact op_id, then exact name, then a unique substring of the name."""
    if isinstance(value, int):
        op = db.query(OperationalPoint).filter(OperationalPoint.id == value).first()
        if op is None:
            raise ToolError(f"Betriebsstelle mit id {value} nicht gefunden.")
        return op

    text = value.strip()
    if not text:
        raise ToolError("Leere Betriebsstellen-Angabe.")
    lowered = text.lower()
    candidates: list[OperationalPoint] = (
        db.query(OperationalPoint).filter(func.lower(OperationalPoint.op_id) == lowered).all()
        or db.query(OperationalPoint).filter(func.lower(OperationalPoint.name) == lowered).all()
        or db.query(OperationalPoint)
        .filter(
            or_(OperationalPoint.name.ilike(f"%{text}%"), OperationalPoint.op_id.ilike(f"%{text}%"))
        )
        .limit(6)
        .all()
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ToolError(
            f"Betriebsstelle '{text}' nicht gefunden (search_operational_points hilft)."
        )
    listed = "; ".join(f"id {c.id}: {c.name} ({c.op_id})" for c in candidates[:5])
    raise ToolError(
        f"Betriebsstelle '{text}' ist mehrdeutig — bitte per id angeben: {listed}"
    )


def _resolve_operational_point(db: Session, value: int | str) -> OperationalPoint:
    op = _lookup_operational_point(db, value)
    if op.latitude is None or op.longitude is None:
        raise ToolError(f"Betriebsstelle {op.name} ({op.op_id}) hat keine Koordinaten.")
    return op


def _check_position(position: Any, where: str, warnings: list[str]) -> list[float]:
    if (
        not isinstance(position, list)
        or len(position) < 2
        or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in position[:2])
    ):
        raise ToolError(f"{where}: Koordinate muss [lon, lat] sein, nicht {position!r}.")
    lon, lat = float(position[0]), float(position[1])
    if not (-180 <= lon <= 180 and -90 <= lat <= 90) or not all(map(math.isfinite, (lon, lat))):
        raise ToolError(f"{where}: Koordinate {position!r} liegt außerhalb von WGS84.")
    if not (
        _PLAUSIBLE_LON[0] <= lon <= _PLAUSIBLE_LON[1]
        and _PLAUSIBLE_LAT[0] <= lat <= _PLAUSIBLE_LAT[1]
    ):
        warnings.append(
            f"{where}: [{lon}, {lat}] liegt nicht in Deutschland — lon/lat vertauscht?"
        )
    return [lon, lat]


def _check_line(coords: Any, where: str, warnings: list[str]) -> list[list[float]]:
    if not isinstance(coords, list) or len(coords) < 2:
        raise ToolError(f"{where}: eine Linie braucht mindestens zwei Koordinaten.")
    return [_check_position(p, where, warnings) for p in coords]


def _normalize_geometry(geometry: Any, where: str, warnings: list[str]) -> dict[str, Any]:
    if not isinstance(geometry, dict):
        raise ToolError(f"{where}: Geometrie fehlt.")
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "Point":
        return {"type": kind, "coordinates": _check_position(coords, where, warnings)}
    if kind == "MultiPoint":
        if not isinstance(coords, list) or not coords:
            raise ToolError(f"{where}: MultiPoint ohne Koordinaten.")
        return {"type": kind, "coordinates": [_check_position(p, where, warnings) for p in coords]}
    if kind == "LineString":
        return {"type": kind, "coordinates": _check_line(coords, where, warnings)}
    if kind == "MultiLineString":
        if not isinstance(coords, list) or not coords:
            raise ToolError(f"{where}: MultiLineString ohne Linien.")
        return {"type": kind, "coordinates": [_check_line(c, where, warnings) for c in coords]}
    raise ToolError(
        f"{where}: Geometrietyp {kind!r} wird nicht unterstützt "
        "(Point, MultiPoint, LineString, MultiLineString)."
    )


def _normalize_features(items: list[dict[str, Any]], warnings: list[str]) -> list[dict[str, Any]]:
    """Accept Features, bare geometries and FeatureCollections; return flat Features."""
    flat: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict) and item.get("type") == "FeatureCollection":
            flat.extend(item.get("features") or [])
        else:
            flat.append(item)

    features = []
    for number, item in enumerate(flat, start=1):
        where = f"add_features[{number}]"
        if not isinstance(item, dict):
            raise ToolError(f"{where}: GeoJSON-Objekt erwartet.")
        if item.get("type") == "Feature":
            geometry = _normalize_geometry(item.get("geometry"), where, warnings)
            properties = item.get("properties")
            if properties is not None and not isinstance(properties, dict):
                raise ToolError(f"{where}: properties muss ein Objekt sein.")
        else:
            geometry = _normalize_geometry(item, where, warnings)
            properties = None
        features.append({"type": "Feature", "geometry": geometry, "properties": properties or {}})
    return features


def _existing_op_ids(features: list[dict[str, Any]]) -> set[str]:
    return {
        (f.get("properties") or {}).get("op_id")
        for f in features
        if (f.get("properties") or {}).get("op_id")
    }


def _append_stations(features: list[dict[str, Any]], ops: list[OperationalPoint]) -> None:
    """Append operational points as points, skipping those already present (by op_id)."""
    seen = _existing_op_ids(features)
    seen_ids: set[int] = set()
    for op in ops:
        if op.id in seen_ids or (op.op_id and op.op_id in seen):
            continue
        seen_ids.add(op.id)
        if op.op_id:
            seen.add(op.op_id)
        features.append(_op_feature(op))


# --- tools -------------------------------------------------------------------


def search_operational_points(query: str, limit: int = 20, *, ctx: Context) -> dict[str, Any]:
    """Find operational points (Betriebsstellen: stations, junctions, sidings) by a
    case-insensitive substring of name or op_id (RL100/RINF code). Returns id,
    op_id, name, type and coordinates — the waypoints for route_project_geometry
    and the points for edit_project_geometry. Exact matches come first."""
    get_principal(ctx)
    text = query.strip()
    if len(text) < 2:
        raise ToolError("Bitte mindestens zwei Zeichen suchen.")
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))
    lowered = text.lower()
    exact = or_(func.lower(OperationalPoint.name) == lowered, func.lower(OperationalPoint.op_id) == lowered)
    with tool_session(ctx) as db:
        matches = (
            db.query(OperationalPoint)
            .filter(
                or_(OperationalPoint.name.ilike(f"%{text}%"), OperationalPoint.op_id.ilike(f"%{text}%"))
            )
            .order_by(exact.desc(), func.length(OperationalPoint.name), OperationalPoint.name)
            .limit(limit)
            .all()
        )
        return {"operational_points": [_op_dict(op) for op in matches]}


def get_project_geometry(
    project_id: int, include_geojson: bool = False, *, ctx: Context
) -> dict[str, Any]:
    """The project geometry: who owns it (own geometry or aggregated from the
    subprojects), totals (features, lines, points, length, bbox) and one entry per
    feature with its ``index`` (for edit_project_geometry ``remove_feature_indices``),
    type, vertex count, line length and start/end, or the point's coordinates and
    operational point. Saved GraphHopper routes are listed as well.
    ``include_geojson=true`` adds the full FeatureCollection (coordinates rounded to
    ~1 m) — large for long routes, so only when the coordinates are really needed."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        features = extract_features(project.geojson_representation)
        aggregated = bool(project.geojson_from_subprojects) and has_subprojects(db, project.id)
        result: dict[str, Any] = {
            "project_id": project.id,
            "name": project.name,
            "aggregated_from_subprojects": aggregated,
            "editable": not aggregated,
            "stored_length_km": project.length,
            **_geometry_summary(features),
            "features": [_feature_summary(i, f) for i, f in enumerate(features)],
            "saved_routes": [
                {
                    "route_id": str(route.id),
                    "distance_km": round(float(route.distance_m) / 1000, 2),
                    "profile": route.profile,
                }
                for route in list_routes_for_project(db, project.id, limit=20)
            ],
        }
        if include_geojson:
            for feature in features:
                geometry = feature.get("geometry") or {}
                if "coordinates" in geometry:
                    geometry["coordinates"] = _round_coords(geometry["coordinates"])
            result["geojson"] = {"type": "FeatureCollection", "features": features}
        return result


def route_project_geometry(
    project_id: int,
    waypoints: list[int | str | Coordinate],
    mode: Literal["append", "replace"] = "append",
    add_stations: bool = True,
    apply: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Route a line over the existing rail network (GraphHopper) — like "Route
    berechnen" in the geometry editor (requires ``project.edit``).

    - waypoints: start, optional via points, end (at least two). Each is an
      operational point — database id (int), op_id or exact name (str; see
      search_operational_points) — or a free coordinate {"lat": …, "lon": …}.
      Add via points to force the right corridor where several lines run.
    - mode: "append" adds the route to the existing geometry, "replace" swaps it.
    - add_stations: also add the operational-point waypoints as points
      (skipped when the op_id is already present).
    - apply: false (default) only calculates and reports distance, resolved
      waypoints and the resulting geometry; true writes it (changelog, revertible)
      and stores the route.
    New lines (Neubaustrecken) have no track to route on: draw them with
    edit_project_geometry instead. Projects whose geometry is aggregated from
    subprojects cannot be routed directly."""
    principal = get_principal(ctx)
    require(principal, "project.edit")
    if len(waypoints) < 2:
        raise ToolError("Mindestens zwei Wegpunkte (Start und Ziel) angeben.")

    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        _ensure_owns_geometry(db, project)

        resolved: list[dict[str, Any]] = []
        stations: list[OperationalPoint] = []
        for value in waypoints:
            if isinstance(value, Coordinate):
                resolved.append({"lat": value.lat, "lon": value.lon})
                continue
            op = _resolve_operational_point(db, value)
            stations.append(op)
            resolved.append(_op_dict(op))

        service = route_service(ctx)
        try:
            # Sync tools run in a worker thread; hop back to the event loop for the HTTP call.
            feature = anyio.from_thread.run(
                service.calculate_only,
                [{"lat": w["lat"], "lon": w["lon"]} for w in resolved],
                ROUTING_PROFILE,
                {},
            )
        except RoutingNoPathError as exc:
            raise ToolError(
                "Kein Pfad im Schienennetz gefunden. Liegen alle Wegpunkte an Gleisen? "
                "Neubaustrecken mit edit_project_geometry zeichnen."
            ) from exc
        except RoutingUpstreamError as exc:
            raise ToolError("Routing-Dienst nicht erreichbar.") from exc

        features = [] if mode == "replace" else extract_features(project.geojson_representation)
        features.append({"type": "Feature", "geometry": feature["geometry"], "properties": {}})
        if add_stations:
            _append_stations(features, stations)

        route_info = {
            "distance_km": round(feature["properties"]["distance_m"] / 1000, 2),
            "duration_min": round(feature["properties"]["duration_ms"] / 60000),
            "line_vertices": len(feature["geometry"]["coordinates"]),
            "bbox": [_round(v) for v in feature["properties"]["bbox"]],
            "waypoints": resolved,
        }
        if not apply:
            return {"route": route_info, **_write_result(project, features, applied=False)}

        project = _write_geometry(db, ctx, project, features)
        try:
            service.confirm_and_store(db, project.id, feature)
        except ValueError as exc:  # pragma: no cover - the feature comes from calculate_only
            raise ToolError(f"Route konnte nicht gespeichert werden: {exc}") from exc
        return {"route": route_info, **_write_result(project, features, applied=True)}


def edit_project_geometry(
    project_id: int,
    add_features: list[dict[str, Any]] | None = None,
    add_operational_points: list[int | str] | None = None,
    remove_feature_indices: list[int] | None = None,
    replace: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Edit the project geometry by hand (requires ``project.edit``) — drawing,
    uploading and deleting in the geometry editor. Applied in this order:

    1. replace=true drops the whole existing geometry (alone it clears it);
       otherwise remove_feature_indices deletes single features (``index`` from
       get_project_geometry, read just before).
    2. add_features: GeoJSON Features, bare geometries or FeatureCollections —
       Point, MultiPoint, LineString, MultiLineString; coordinates are
       [lon, lat] (WGS84). Use it for new lines (Neubaustrecken), tram/metro,
       or a manual correction. Properties such as "name" are kept.
    3. add_operational_points: ids, op_ids or exact names (see
       search_operational_points), added as points unless already present.
    The change goes to the changelog and can be reverted in the UI. The result
    carries warnings for coordinates outside Germany (lat/lon swapped?)."""
    principal = get_principal(ctx)
    require(principal, "project.edit")
    add_features = add_features or []
    add_operational_points = add_operational_points or []
    remove_feature_indices = remove_feature_indices or []
    if replace and remove_feature_indices:
        raise ToolError("replace und remove_feature_indices schließen sich aus.")
    if not (replace or add_features or add_operational_points or remove_feature_indices):
        raise ToolError("Keine Änderung übergeben.")

    warnings: list[str] = []
    new_features = _normalize_features(add_features, warnings)

    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        _ensure_owns_geometry(db, project)
        features = [] if replace else extract_features(project.geojson_representation)

        out_of_range = sorted(i for i in set(remove_feature_indices) if not 0 <= i < len(features))
        if out_of_range:
            raise ToolError(
                f"Feature-Index {', '.join(map(str, out_of_range))} existiert nicht "
                f"(0–{len(features) - 1}); get_project_geometry zeigt die Indizes."
            )
        removed = set(remove_feature_indices)
        features = [f for i, f in enumerate(features) if i not in removed]
        features.extend(new_features)
        _append_stations(
            features, [_resolve_operational_point(db, value) for value in add_operational_points]
        )

        project = _write_geometry(db, ctx, project, features)
        return {**_write_result(project, features, applied=True), "warnings": warnings}


def register(server: MCPServer) -> None:
    server.add_tool(search_operational_points, annotations=READ_ONLY)
    server.add_tool(get_project_geometry, annotations=READ_ONLY)
    # Both can replace or delete existing geometry (revertible via the changelog).
    server.add_tool(route_project_geometry, annotations=DESTRUCTIVE)
    server.add_tool(edit_project_geometry, annotations=DESTRUCTIVE)
