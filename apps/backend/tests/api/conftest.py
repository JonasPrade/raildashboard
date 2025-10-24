from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dashboard_backend.core.security import hash_password
from dashboard_backend.database import get_db
from dashboard_backend.dependencies.routes import get_route_service
from dashboard_backend.models.users import User
from dashboard_backend.models.routes import Route
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.schemas.users import UserRole
from dashboard_backend.services.route_service import RouteService
from main import app


SQLITE_URL = "sqlite:///:memory:"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


TABLES = [User.__table__, ProjectGroup.__table__, Route.__table__]


class RoutingClientStub:
    def __init__(self) -> None:
        self.next_exception: Exception | None = None
        self.next_response = {
            "paths": [
                {
                    "distance": 1200.5,
                    "time": 480000,
                    "points": {
                        "coordinates": [[7.0, 51.0], [7.5, 51.5]],
                    },
                }
            ]
        }
        self.calls = 0

    async def route(self, waypoints, profile, options):  # pragma: no cover - exercised via tests
        self.calls += 1
        if self.next_exception is not None:
            exception = self.next_exception
            self.next_exception = None
            raise exception
        return self.next_response


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    for table in TABLES:
        table.create(bind=engine, checkfirst=True)
    yield
    for table in reversed(TABLES):
        table.drop(bind=engine, checkfirst=True)


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def override_dependency(db_session):
    def _get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def routing_stub() -> RoutingClientStub:
    return RoutingClientStub()


@pytest.fixture()
def route_service(routing_stub: RoutingClientStub) -> RouteService:
    return RouteService(routing_stub, graph_version="test-graph")


@pytest.fixture(autouse=True)
def override_route_service_dependency(route_service: RouteService):
    app.dependency_overrides[get_route_service] = lambda: route_service
    yield
    app.dependency_overrides.pop(get_route_service, None)


@pytest.fixture()
def client(db_session):
    return TestClient(app)


@pytest.fixture()
def create_user(db_session):
    def _create_user(username: str, password: str, role: UserRole) -> User:
        user = User(username=username, hashed_password=hash_password(password), role=role.value)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_user


def basic_auth_header(username: str, password: str) -> dict[str, str]:
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}

