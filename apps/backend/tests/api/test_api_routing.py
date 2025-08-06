from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_route_success(monkeypatch):
    def mock_find_route_in_db(db, start_op, end_op):
        return [1, 2, 3]
    import dashboard_backend.api.v1.endpoints.route
    monkeypatch.setattr(dashboard_backend.api.v1.endpoints.route, "find_route_in_db", mock_find_route_in_db)

    response = client.post("/api/v1/route/", json={"start_op": "A", "end_op": "B"})
    assert response.status_code == 200
    assert response.json() == {"sectionofline_ids": [1, 2, 3]}