from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dashboard_backend.models.routes import Route


def get_route_by_cache_key(db: Session, cache_key: str) -> Optional[Route]:
    statement = select(Route).where(Route.cache_key == cache_key)
    return db.execute(statement).scalar_one_or_none()


def get_route_by_id(db: Session, route_id: UUID) -> Optional[Route]:
    statement = select(Route).where(Route.id == route_id)
    return db.execute(statement).scalar_one_or_none()


def list_routes_for_project(
    db: Session,
    project_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> List[Route]:
    statement = (
        select(Route)
        .where(Route.project_id == project_id)
        .order_by(Route.distance_m)
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(statement).scalars())


def persist_route(db: Session, route: Route) -> Route:
    db.add(route)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_route_by_cache_key(db, route.cache_key)
        if existing is not None:
            return existing
        raise
    db.refresh(route)
    return route


def update_route(db: Session, route_id: UUID, project_id: UUID, **fields) -> Optional[Route]:
    """Replace an existing route's geometry and metadata in-place.

    Returns None if no route with that id/project_id combination exists.
    """
    route = get_route_by_id(db, route_id)
    if route is None or route.project_id != project_id:
        return None
    for key, value in fields.items():
        setattr(route, key, value)
    db.commit()
    db.refresh(route)
    return route
