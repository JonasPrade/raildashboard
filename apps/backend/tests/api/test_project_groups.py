import pytest
from sqlalchemy.orm.attributes import set_committed_value

import dashboard_backend.api.v1.endpoints.project_groups as pg_route
from dashboard_backend.crud.projects import project_groups as pg_crud
from dashboard_backend.schemas.projects.project_group_schema import ProjectGroupSchema
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def _to_schema(grp: object) -> ProjectGroupSchema:
    """Build a response schema without touching the ``projects`` relationship.

    The SQLite test DB has no ``project`` table (its geometry column relies on
    PostGIS), so serialising the lazy-loaded ``projects`` collection would fail.
    Freshly created/edited groups are exercised with ``projects=[]``.
    """
    return ProjectGroupSchema(
        id=grp.id,
        name=grp.name,
        short_name=grp.short_name,
        description=grp.description,
        public=grp.public,
        color=grp.color,
        plot_only_superior_projects=grp.plot_only_superior_projects,
        is_visible=grp.is_visible,
        is_default_selected=grp.is_default_selected,
        id_old=grp.id_old,
        projects=[],
    )


@pytest.fixture(autouse=True)
def _stub_projects_serialization(monkeypatch):
    """Run real create/update CRUD, but return a projects-free response schema."""

    def wrapped_create(db, data):
        return _to_schema(pg_crud.create_project_group(db, data))

    def wrapped_update(db, group_id, updates):
        grp = pg_crud.update_project_group(db, group_id, updates)
        return _to_schema(grp) if grp else None

    def wrapped_delete(db, group_id):
        grp = pg_crud.get_project_group_by_id(db, group_id)
        if grp is None:
            return None
        # Deleting a m:n parent would lazy-load ``projects`` (to clear the
        # association rows); the SQLite test DB has no ``project`` table, so we
        # mark the (empty) collection as loaded to skip that query.
        set_committed_value(grp, "projects", [])
        db.delete(grp)
        db.commit()
        return grp

    monkeypatch.setattr(pg_route, "create_project_group", wrapped_create)
    monkeypatch.setattr(pg_route, "update_project_group", wrapped_update)
    monkeypatch.setattr(pg_route, "delete_project_group", wrapped_delete)


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


# ---------------------------------------------------------------------------
# POST /api/v1/project_groups/  (admin only) — create
# ---------------------------------------------------------------------------


def test_create_project_group_success(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)

    resp = client.post(
        "/api/v1/project_groups/",
        json={
            "name": "Neue Gruppe",
            "short_name": "NG",
            "description": "Beschreibung",
            "color": "#00FF00",
            "public": True,
            "plot_only_superior_projects": False,
            "is_visible": True,
            "is_default_selected": True,
        },
        headers=basic_auth_header("admin", "adminpass"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Neue Gruppe"
    assert body["short_name"] == "NG"
    assert body["description"] == "Beschreibung"
    assert body["color"] == "#00FF00"
    assert body["public"] is True
    assert body["plot_only_superior_projects"] is False
    assert body["is_visible"] is True
    assert body["is_default_selected"] is True
    assert body["id"] is not None


def test_create_project_group_duplicate_short_name(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)
    headers = basic_auth_header("admin", "adminpass")

    first = client.post(
        "/api/v1/project_groups/",
        json={"name": "Gruppe", "short_name": "DUP"},
        headers=headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/project_groups/",
        json={"name": "Andere Gruppe", "short_name": "DUP"},
        headers=headers,
    )
    assert second.status_code == 409


def test_create_project_group_requires_admin(client, create_user):
    create_user("editor", "pass123", UserRole.editor)
    create_user("viewer", "pass123", UserRole.viewer)

    payload = {"name": "Gruppe", "short_name": "X"}

    resp_editor = client.post(
        "/api/v1/project_groups/",
        json=payload,
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp_editor.status_code == 403

    resp_viewer = client.post(
        "/api/v1/project_groups/",
        json=payload,
        headers=basic_auth_header("viewer", "pass123"),
    )
    assert resp_viewer.status_code == 403

    resp_anon = client.post("/api/v1/project_groups/", json=payload)
    assert resp_anon.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/v1/project_groups/{id}  (admin only) — edit all fields
# ---------------------------------------------------------------------------


def test_patch_project_group_all_fields(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)
    headers = basic_auth_header("admin", "adminpass")

    created = client.post(
        "/api/v1/project_groups/",
        json={"name": "Alt", "short_name": "ALT"},
        headers=headers,
    ).json()

    resp = client.patch(
        f"/api/v1/project_groups/{created['id']}",
        json={
            "name": "Neu",
            "short_name": "NEU",
            "description": "Neue Beschreibung",
            "color": "#123456",
            "public": True,
            "plot_only_superior_projects": False,
            "is_visible": False,
            "is_default_selected": True,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Neu"
    assert body["short_name"] == "NEU"
    assert body["description"] == "Neue Beschreibung"
    assert body["color"] == "#123456"
    assert body["public"] is True
    assert body["plot_only_superior_projects"] is False
    assert body["is_visible"] is False
    assert body["is_default_selected"] is True


def test_patch_project_group_duplicate_short_name(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)
    headers = basic_auth_header("admin", "adminpass")

    client.post(
        "/api/v1/project_groups/",
        json={"name": "Erste", "short_name": "ONE"},
        headers=headers,
    )
    second = client.post(
        "/api/v1/project_groups/",
        json={"name": "Zweite", "short_name": "TWO"},
        headers=headers,
    ).json()

    resp = client.patch(
        f"/api/v1/project_groups/{second['id']}",
        json={"short_name": "ONE"},
        headers=headers,
    )
    assert resp.status_code == 409


def test_patch_project_group_same_short_name_allowed(client, create_user):
    """Patching a group with its own short_name must not 409."""
    create_user("admin", "adminpass", UserRole.admin)
    headers = basic_auth_header("admin", "adminpass")

    created = client.post(
        "/api/v1/project_groups/",
        json={"name": "Gruppe", "short_name": "SAME"},
        headers=headers,
    ).json()

    resp = client.patch(
        f"/api/v1/project_groups/{created['id']}",
        json={"short_name": "SAME", "name": "Umbenannt"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Umbenannt"


def test_patch_project_group_requires_admin(client, create_user):
    create_user("editor", "pass123", UserRole.editor)

    resp = client.patch(
        "/api/v1/project_groups/1",
        json={"name": "X"},
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /api/v1/project_groups/{id}  (admin only)
# ---------------------------------------------------------------------------


def test_delete_project_group_success(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)
    headers = basic_auth_header("admin", "adminpass")

    created = client.post(
        "/api/v1/project_groups/",
        json={"name": "Weg damit", "short_name": "DEL"},
        headers=headers,
    ).json()

    resp = client.delete(
        f"/api/v1/project_groups/{created['id']}",
        headers=headers,
    )
    assert resp.status_code == 204

    after = client.get(f"/api/v1/project_groups/{created['id']}")
    assert after.status_code == 404


def test_delete_project_group_not_found(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)

    resp = client.delete(
        "/api/v1/project_groups/999999",
        headers=basic_auth_header("admin", "adminpass"),
    )
    assert resp.status_code == 404


def test_delete_project_group_requires_admin(client, create_user):
    create_user("editor", "pass123", UserRole.editor)
    create_user("viewer", "pass123", UserRole.viewer)

    resp_editor = client.delete(
        "/api/v1/project_groups/1",
        headers=basic_auth_header("editor", "pass123"),
    )
    assert resp_editor.status_code == 403

    resp_viewer = client.delete(
        "/api/v1/project_groups/1",
        headers=basic_auth_header("viewer", "pass123"),
    )
    assert resp_viewer.status_code == 403

    resp_anon = client.delete("/api/v1/project_groups/1")
    assert resp_anon.status_code == 401

