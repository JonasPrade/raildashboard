from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def test_post_route_requires_auth(client, monkeypatch):
    def mock_find_route_in_db(db, start_op, end_op):
        return [1, 2, 3]

    import dashboard_backend.api.v1.endpoints.route

    monkeypatch.setattr(dashboard_backend.api.v1.endpoints.route, "find_route_section_of_lines", mock_find_route_in_db)

    response = client.post("/api/v1/route/", json={"start_op": "A", "end_op": "B"})
    assert response.status_code == 401


def test_post_route_with_credentials(client, create_user, monkeypatch):
    def mock_find_route_in_db(db, start_op, end_op):
        return [1, 2, 3]

    import dashboard_backend.api.v1.endpoints.route

    monkeypatch.setattr(dashboard_backend.api.v1.endpoints.route, "find_route_section_of_lines", mock_find_route_in_db)

    create_user("viewer", "secret123", UserRole.viewer)

    headers = basic_auth_header("viewer", "secret123")
    response = client.post("/api/v1/route/", json={"start_op": "A", "end_op": "B"}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"sectionofline_ids": [1, 2, 3]}

