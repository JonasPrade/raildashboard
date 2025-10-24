from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dashboard_backend.core.security import hash_password
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.schemas.users import UserRole
from main import app


SQLITE_URL = "sqlite:///:memory:"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


TABLES = [User.__table__, ProjectGroup.__table__]


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

