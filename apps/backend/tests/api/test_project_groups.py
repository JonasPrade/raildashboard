from dashboard_backend.schemas.projects.project_group_schema import ProjectGroupSchema


MOCK_GROUPS = [
    ProjectGroupSchema(id=1, name="Gruppe A", short_name="A", projects=[]),
    ProjectGroupSchema(id=2, name="Gruppe B", short_name="B", projects=[]),
]


def test_read_project_groups(client, monkeypatch):
    def mock_get_groups(db):
        return MOCK_GROUPS

    import dashboard_backend.api.v1.endpoints.project_groups as route

    monkeypatch.setattr(route, "get_project_groups", mock_get_groups)

    resp = client.get("/api/v1/project_groups/")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert {item["id"] for item in body} == {1, 2}


def test_read_project_group_by_id(client, monkeypatch):
    def mock_get_group(db, group_id: int):
        return next((group for group in MOCK_GROUPS if group.id == group_id), None)

    import dashboard_backend.api.v1.endpoints.project_groups as route

    monkeypatch.setattr(route, "get_project_group_by_id", mock_get_group)

    resp = client.get("/api/v1/project_groups/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == 1


def test_read_project_group_not_found(client, monkeypatch):
    import dashboard_backend.api.v1.endpoints.project_groups as route

    monkeypatch.setattr(route, "get_project_group_by_id", lambda db, group_id: None)

    resp = client.get("/api/v1/project_groups/999")
    assert resp.status_code == 404

