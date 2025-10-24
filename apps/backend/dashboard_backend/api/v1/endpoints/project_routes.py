from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import Depends, HTTPException, Query
from geoalchemy2.shape import to_shape
from shapely.geometry import LineString
from sqlalchemy.orm import Session

from dashboard_backend.crud.routes import get_route_by_id
from dashboard_backend.database import get_db
from dashboard_backend.dependencies.routes import get_route_service
from dashboard_backend.models.routes import Route
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.routes import RouteIn, RouteOut
from dashboard_backend.services.exceptions import RoutingNoPathError, RoutingUpstreamError
from dashboard_backend.services.route_service import RouteService

router = AuthRouter()


def _to_route_out(route: Route) -> RouteOut:
    geom_shape = to_shape(route.geom)
    if not isinstance(geom_shape, LineString):
        raise HTTPException(status_code=500, detail="route geometry invalid")
    bbox_shape = to_shape(route.bbox) if route.bbox is not None else geom_shape.envelope
    minx, miny, maxx, maxy = bbox_shape.bounds
    return RouteOut(
        route_id=route.id,
        project_id=route.project_id,
        distance_m=float(route.distance_m),
        duration_ms=int(route.duration_ms),
        bbox=[float(minx), float(miny), float(maxx), float(maxy)],
        geom_geojson={
            "type": "LineString",
            "coordinates": [[float(x), float(y)] for x, y in geom_shape.coords],
        },
        details=route.details or {},
    )


@router.post(
    "/projects/{project_id}/routes",
    response_model=RouteOut,
    status_code=201,
)
async def create_route(
    project_id: UUID,
    request: RouteIn,
    db: Session = Depends(get_db),
    service: RouteService = Depends(get_route_service),
) -> RouteOut:
    waypoints = [waypoint.model_dump() for waypoint in request.waypoints]

    try:
        route = await service.create_and_store(db, project_id, waypoints, request.profile, request.options)
    except RoutingNoPathError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RoutingUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return _to_route_out(route)


@router.get(
    "/projects/{project_id}/routes",
    response_model=List[RouteOut],
)
async def list_routes(
    project_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    service: RouteService = Depends(get_route_service),
) -> List[RouteOut]:
    routes = await service.list_for_project(db, project_id, limit=limit, offset=offset)
    return [_to_route_out(route) for route in routes]


@router.get("/routes/{route_id}", response_model=RouteOut)
async def get_route(route_id: UUID, db: Session = Depends(get_db)) -> RouteOut:
    route = get_route_by_id(db, route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="route not found")
    return _to_route_out(route)
