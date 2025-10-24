from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from dashboard_backend.models.routes import Route
from dashboard_backend.services.route_service import RouteService


class RoutingStub:
    def __init__(self) -> None:
        self.calls = 0

    async def route(self, waypoints, profile, options):
        self.calls += 1
        return {
            "paths": [
                {
                    "distance": 1500.0,
                    "time": 600000,
                    "points": {
                        "coordinates": [
                            [7.0, 51.0],
                            [7.5, 51.5],
                        ]
                    },
                }
            ]
        }


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Route.__table__.create(engine)
    SessionLocal = sessionmaker(bind=engine)
    try:
        with SessionLocal() as session:
            yield session
    finally:
        Route.__table__.drop(engine)


def test_route_service_persists_route(session: Session):
    service = RouteService(RoutingStub(), graph_version="test-graph")
    project_id = uuid4()
    waypoints = [
        {"lat": 51.0, "lon": 7.0},
        {"lat": 51.5, "lon": 7.5},
    ]

    route = asyncio.run(service.create_and_store(session, project_id, waypoints, "rail_default", {}))
    assert route.project_id == project_id
    assert route.graph_version == "test-graph"
    assert route.geom is not None
    assert getattr(route.geom, "srid", 4326) == 4326
    assert route.bbox is not None
    assert getattr(route.bbox, "srid", 4326) == 4326

    fetched = session.query(Route).filter(Route.id == route.id).one()
    assert fetched.distance_m == pytest.approx(1500.0)
    assert fetched.duration_ms == 600000
    assert fetched.cache_key == route.cache_key


def test_route_service_returns_cached_route(session: Session):
    stub = RoutingStub()
    service = RouteService(stub, graph_version="test-graph")
    project_id = uuid4()
    waypoints = [
        {"lat": 51.0, "lon": 7.0},
        {"lat": 51.5, "lon": 7.5},
    ]

    first = asyncio.run(service.create_and_store(session, project_id, waypoints, "rail_default", {}))
    second = asyncio.run(service.create_and_store(session, project_id, waypoints, "rail_default", {}))
    assert first.id == second.id
    assert stub.calls == 1
