from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def _admin_headers(create_user):
    create_user("admin", "adminpass", UserRole.admin)
    return basic_auth_header("admin", "adminpass")


def test_list_roles_returns_system_roles(client, create_user):
    headers = _admin_headers(create_user)
    response = client.get("/api/v1/roles/", headers=headers)
    assert response.status_code == 200
    names = {r["name"] for r in response.json()}
    assert {"viewer", "editor", "admin"} <= names
    editor = next(r for r in response.json() if r["name"] == "editor")
    assert editor["is_system"] is True
    assert "project.edit" in editor["permissions"]


def test_list_roles_requires_role_manage(client, create_user):
    create_user("editor", "pass1234", UserRole.editor)
    response = client.get("/api/v1/roles/", headers=basic_auth_header("editor", "pass1234"))
    assert response.status_code == 403


def test_list_roles_requires_auth(client):
    assert client.get("/api/v1/roles/").status_code == 401


def test_create_role_with_permissions(client, create_user):
    headers = _admin_headers(create_user)
    response = client.post(
        "/api/v1/roles/",
        json={"name": "reviewer", "description": "Read & comment", "permissions": ["project.edit"]},
        headers=headers,
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "reviewer"
    assert payload["is_system"] is False
    assert payload["permissions"] == ["project.edit"]


def test_create_role_rejects_unknown_permission(client, create_user):
    headers = _admin_headers(create_user)
    response = client.post(
        "/api/v1/roles/",
        json={"name": "bogus", "permissions": ["does.not.exist"]},
        headers=headers,
    )
    assert response.status_code == 400


def test_create_role_rejects_duplicate_name(client, create_user):
    headers = _admin_headers(create_user)
    response = client.post("/api/v1/roles/", json={"name": "editor"}, headers=headers)
    assert response.status_code == 409


def test_update_role_permissions(client, create_user):
    headers = _admin_headers(create_user)
    created = client.post("/api/v1/roles/", json={"name": "reviewer"}, headers=headers).json()

    response = client.patch(
        f"/api/v1/roles/{created['id']}",
        json={"permissions": ["project.edit", "projecttext.edit"]},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["permissions"] == ["project.edit", "projecttext.edit"]


def test_system_role_cannot_be_renamed(client, create_user, db_session):
    from dashboard_backend.crud import roles as roles_crud

    headers = _admin_headers(create_user)
    editor = roles_crud.get_role_by_name(db_session, "editor")
    response = client.patch(
        f"/api/v1/roles/{editor.id}", json={"name": "redactor"}, headers=headers
    )
    assert response.status_code == 400


def test_system_role_permissions_are_editable(client, create_user, db_session):
    from dashboard_backend.crud import roles as roles_crud

    headers = _admin_headers(create_user)
    viewer = roles_crud.get_role_by_name(db_session, "viewer")
    response = client.patch(
        f"/api/v1/roles/{viewer.id}", json={"permissions": ["project.edit"]}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["permissions"] == ["project.edit"]


def test_system_role_cannot_be_deleted(client, create_user, db_session):
    from dashboard_backend.crud import roles as roles_crud

    headers = _admin_headers(create_user)
    editor = roles_crud.get_role_by_name(db_session, "editor")
    response = client.delete(f"/api/v1/roles/{editor.id}", headers=headers)
    assert response.status_code == 400


def test_delete_role_assigned_to_user_returns_409(client, create_user, db_session):
    headers = _admin_headers(create_user)
    created = client.post("/api/v1/roles/", json={"name": "reviewer"}, headers=headers).json()
    # Assign the new role to a user.
    client.post(
        "/api/v1/users/",
        json={"username": "rev", "password": "password123", "role": "reviewer"},
        headers=headers,
    )
    response = client.delete(f"/api/v1/roles/{created['id']}", headers=headers)
    assert response.status_code == 409


def test_delete_unassigned_role(client, create_user):
    headers = _admin_headers(create_user)
    created = client.post("/api/v1/roles/", json={"name": "temp"}, headers=headers).json()
    response = client.delete(f"/api/v1/roles/{created['id']}", headers=headers)
    assert response.status_code == 204


def test_permissions_catalog(client, create_user):
    headers = _admin_headers(create_user)
    response = client.get("/api/v1/permissions/", headers=headers)
    assert response.status_code == 200
    keys = {p["key"] for p in response.json()}
    assert "project.edit" in keys
    assert "role.manage" in keys
    # Every entry carries a label and a group for the UI.
    for entry in response.json():
        assert entry["label"]
        assert entry["group"]


def test_permissions_catalog_requires_role_manage(client, create_user):
    create_user("editor", "pass1234", UserRole.editor)
    response = client.get("/api/v1/permissions/", headers=basic_auth_header("editor", "pass1234"))
    assert response.status_code == 403
