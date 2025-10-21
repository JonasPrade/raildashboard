# tests/api/test_project_groups.py
import pytest
from fastapi.testclient import TestClient
from main import app
from dashboard_backend.database import get_db

# Mock data
mock_project_groups = [
    {"id": 1, "name": "Gruppe A"},
    {"id": 2, "name": "Gruppe B"},
]

class MockQuery:
    def __init__(self, data):
        # data is a list of dicts representing rows
        self._data = data

    # Return all items
    def all(self):
        return self._data

    # Simple filter_by implementation for equality matches
    def filter_by(self, **kwargs):
        filtered = [
            row for row in self._data
            if all(row.get(k) == v for k, v in kwargs.items())
        ]
        return MockQuery(filtered)

    # First item or None
    def first(self):
        return self._data[0] if self._data else None


class MockDBSession:
    def __init__(self):
        # keep a copy per session
        self._data = mock_project_groups.copy()

    # Mimic SQLAlchemy's Session.query(Model). We ignore Model and return a query on our list.
    def query(self, *args, **kwargs):
        return MockQuery(self._data)

    # Mimic SQLAlchemy 2.0 Session.get(Model, pk)
    def get(self, _model, pk):
        for row in self._data:
            if row.get("id") == pk:
                return row
        return None


def override_get_db():
    # Yield a fresh mock session
    db = MockDBSession()
    try:
        yield db
    finally:
        pass

# Correctly register override: map the callable to the override callable
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_read_project_groups():
    resp = client.get("/api/v1/project-groups/")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # optional: ensure mock content is returned
    assert body == mock_project_groups

def test_read_project_group_by_id():
    resp = client.get("/api/v1/project-groups/1")
    assert resp.status_code == 200
    assert resp.json() == {"id": 1, "name": "Gruppe A"}

def test_read_project_group_not_found():
    resp = client.get("/api/v1/project-groups/99999")
    assert resp.status_code == 404
