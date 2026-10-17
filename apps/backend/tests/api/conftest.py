from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from dashboard_backend.core.security import hash_password
from dashboard_backend.crud import roles as roles_crud
from dashboard_backend.database import get_db
from dashboard_backend.dependencies.routes import get_route_service
from dashboard_backend.models.api_keys import ApiKey
from dashboard_backend.models.app_settings import AppSettings
from dashboard_backend.models.change_tracking import ChangeLog, ChangeLogEntry
from dashboard_backend.models.associations.project_to_constituency import (
    ProjectToConstituency,
)
from dashboard_backend.models.associations.text_to_project import TextToProject
from dashboard_backend.models.associations.project_to_project_group import (
    ProjectToProjectGroup,
)
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.guides import GuideSectionOverride
from dashboard_backend.models.haushalt.budget_titel_entry import BudgetTitelEntry
from dashboard_backend.models.haushalt.haushalt_titel import HaushaltTitel
from dashboard_backend.models.infraplan import InfraplanParseResult
from dashboard_backend.models.gvfg import (
    GvfgEntry,
    GvfgEntryAmount,
    GvfgParseResult,
    GvfgProgram,
    gvfg_entry_project,
)
from dashboard_backend.models.parliament import (
    Committee,
    CommitteeMembership,
    Constituency,
    Mandate,
    ParliamentImportRun,
    ParliamentPeriod,
    Politician,
)
from dashboard_backend.models.projects.budget import Budget
from dashboard_backend.models.projects.bvwp_project_data import BvwpProjectData
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.projects.project_redirect import ProjectRedirect
from dashboard_backend.models.projects.project_text import ProjectText
from dashboard_backend.models.projects.project_text_type import ProjectTextType
from dashboard_backend.models.roles import Role, RolePermission
from dashboard_backend.models.todos.todo import Todo, TodoAssignee
from dashboard_backend.models.users import User
from dashboard_backend.models.vib.vib_entry import VibEntry, vib_entry_project
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry
from dashboard_backend.models.vib.vib_report import VibReport
from dashboard_backend.models.associations.fulda_announcement_to_project import (
    fulda_announcement_to_project,
)
from dashboard_backend.models.projects.fulda_announcement import FuldaAnnouncement
from dashboard_backend.models.projects.fulda_document import FuldaDocument
from dashboard_backend.models.projects.bauportal_status import BauportalStatus
from dashboard_backend.models.projects.media_report import MediaReport
from dashboard_backend.models.projects.document import Document
from dashboard_backend.models.associations.progress_track_document import ProgressTrackDocument
from dashboard_backend.models.railway_infrastructure.operational_point import OperationalPoint
from dashboard_backend.models.routes import Route
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.schemas.users import UserRole
from dashboard_backend.services.route_service import RouteService
from main import app


SQLITE_URL = "sqlite:///:memory:"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# geoalchemy2 wraps geometry params in spatial functions; register pass-through
# stand-ins so plain SQLite accepts them (geometry values stay NULL here).
@event.listens_for(engine, "connect")
def _register_spatial_stubs(dbapi_conn, _record):
    for name, nargs in (("GeomFromEWKT", 1), ("ST_AsEWKB", 1), ("AsEWKB", 1)):
        dbapi_conn.create_function(name, nargs, lambda value: value)


# Endpoints that join project rows (e.g. the constituency links) need the table.
PROJECT_TABLE = Project.__table__


TABLES = [
    PROJECT_TABLE,
    Role.__table__,  # must precede User (FK dependency)
    RolePermission.__table__,
    User.__table__,
    ApiKey.__table__,  # must follow User (FK dependency)
    ProjectGroup.__table__,
    Route.__table__,
    OperationalPoint.__table__,  # MCP geometry tools (waypoints, station points)
    AppSettings.__table__,
    ProjectTextType.__table__,  # must precede ProjectText (FK dependency)
    ProjectText.__table__,
    Todo.__table__,  # FK to project (absent here) is unenforced in SQLite
    TodoAssignee.__table__,  # must follow Todo (FK dependency)
    GuideSectionOverride.__table__,
    ParliamentPeriod.__table__,  # must precede Constituency/Mandate (FK dependency)
    Politician.__table__,
    Constituency.__table__,
    Committee.__table__,
    Mandate.__table__,
    CommitteeMembership.__table__,
    ParliamentImportRun.__table__,
    ProjectToConstituency.__table__,  # FK to project (absent here) is unenforced in SQLite
    ProjectToProjectGroup.__table__,  # must follow project + project_group (FK dependency)
    ProjectProgress.__table__,  # FK to project; read by the MCP list_projects phase filter
    ProgressObservation.__table__,  # read by the group timeline
    VibReport.__table__,  # joined by the forecast/timeline (report date = recency)
    VibEntry.__table__,  # must follow vib_report (FK dependency)
    vib_entry_project,  # must follow project + vib_entry (FK dependency)
    VibPfaEntry.__table__,  # must follow vib_entry (FK dependency)
    BvwpProjectData.__table__,  # FK to project; read by the MCP get_project tool
    ChangeLog.__table__,  # FK to project + users; written by the MCP update_project tool
    ChangeLogEntry.__table__,  # must follow ChangeLog (FK dependency)
    ProgressObservation.__table__,  # FKs to imported sources unenforced; MCP observation tools
    TextToProject.__table__,  # must follow project + project_text; moved by the project merge
    ProjectRedirect.__table__,  # must follow project + users; written by the project merge
    InfraplanParseResult.__table__,  # must follow users; Infraplan import drafts
    GvfgProgram.__table__,  # GVFG import (must precede its entries)
    GvfgEntry.__table__,
    GvfgEntryAmount.__table__,
    gvfg_entry_project,
    GvfgParseResult.__table__,
    Finve.__table__,  # MCP FinVe search + sync_derived_observations (Fulda MCP flow)
    FinveToProject.__table__,  # must follow project + finve (FK dependency)
    Budget.__table__,  # must follow finve (FK dependency)
    HaushaltTitel.__table__,  # must precede BudgetTitelEntry (FK dependency)
    BudgetTitelEntry.__table__,  # must follow budgets + haushalt_titel
    BauportalStatus.__table__,  # read by sync_derived_observations
    MediaReport.__table__,
    Document.__table__,  # progress view (PF/parl documents)
    ProgressTrackDocument.__table__,
    FuldaDocument.__table__,  # Fulda import (must precede its entries)
    FuldaAnnouncement.__table__,
    fulda_announcement_to_project,
]


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
    # Seed the system roles once; committed here so they survive the per-test
    # transaction rollback (matches the production migration seed).
    seed_session = TestingSessionLocal(bind=engine)
    try:
        roles_crud.seed_system_roles(seed_session)
    finally:
        seed_session.close()
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
        role_obj = db_session.query(Role).filter(Role.name == role.value).one()
        user = User(username=username, hashed_password=hash_password(password), role_id=role_obj.id)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_user


def basic_auth_header(username: str, password: str) -> dict[str, str]:
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}

