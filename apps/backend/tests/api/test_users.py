from dashboard_backend.crud import users as users_crud
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def test_me_returns_current_user(client, create_user):
    create_user("alice", "pass123", UserRole.editor)

    response = client.get("/api/v1/users/me", headers=basic_auth_header("alice", "pass123"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "alice"
    assert payload["role"] == UserRole.editor.value


def test_me_requires_authentication(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_me_rejects_wrong_password(client, create_user):
    create_user("alice", "correct", UserRole.viewer)

    response = client.get("/api/v1/users/me", headers=basic_auth_header("alice", "wrong"))
    assert response.status_code == 401


def test_list_users_requires_admin(client, create_user, db_session):
    create_user("viewer", "secret123", UserRole.viewer)
    create_user("admin", "adminpass", UserRole.admin)

    response = client.get("/api/v1/users/", headers=basic_auth_header("viewer", "secret123"))
    assert response.status_code == 403

    response = client.get("/api/v1/users/", headers=basic_auth_header("admin", "adminpass"))
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_create_user_requires_admin(client, create_user):
    create_user("viewer", "secret123", UserRole.viewer)

    response = client.post(
        "/api/v1/users/",
        json={"username": "new", "password": "password123", "role": UserRole.viewer.value},
        headers=basic_auth_header("viewer", "secret123"),
    )
    assert response.status_code == 403


def test_create_user_success(client, create_user, db_session):
    create_user("admin", "adminpass", UserRole.admin)

    response = client.post(
        "/api/v1/users/",
        json={"username": "newuser", "password": "password123", "role": UserRole.editor.value},
        headers=basic_auth_header("admin", "adminpass"),
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["username"] == "newuser"
    assert payload["role"] == UserRole.editor.value

    created = users_crud.get_user_by_username(db_session, "newuser")
    assert created is not None
    assert created.hashed_password != "password123"


def test_update_user_role_success(client, create_user):
    admin = create_user("admin", "adminpass", UserRole.admin)
    target = create_user("editor", "editorpass", UserRole.editor)

    response = client.patch(
        f"/api/v1/users/{target.id}",
        json={"role": UserRole.viewer.value},
        headers=basic_auth_header("admin", "adminpass"),
    )
    assert response.status_code == 200
    assert response.json()["role"] == UserRole.viewer.value


def test_update_user_role_prevents_self_change(client, create_user):
    admin = create_user("admin", "adminpass", UserRole.admin)

    response = client.patch(
        f"/api/v1/users/{admin.id}",
        json={"role": UserRole.viewer.value},
        headers=basic_auth_header("admin", "adminpass"),
    )
    assert response.status_code == 400


def test_update_user_role_requires_admin(client, create_user):
    create_user("viewer", "viewerpass", UserRole.viewer)
    target = create_user("editor", "editorpass", UserRole.editor)

    response = client.patch(
        f"/api/v1/users/{target.id}",
        json={"role": UserRole.viewer.value},
        headers=basic_auth_header("viewer", "viewerpass"),
    )
    assert response.status_code == 403


def test_delete_user_success(client, create_user, db_session):
    create_user("admin", "adminpass", UserRole.admin)
    target = create_user("tobedeleted", "pass123", UserRole.viewer)

    response = client.delete(
        f"/api/v1/users/{target.id}",
        headers=basic_auth_header("admin", "adminpass"),
    )
    assert response.status_code == 204
    assert users_crud.get_user_by_username(db_session, "tobedeleted") is None


def test_delete_user_prevents_self_deletion(client, create_user):
    admin = create_user("admin", "adminpass", UserRole.admin)

    response = client.delete(
        f"/api/v1/users/{admin.id}",
        headers=basic_auth_header("admin", "adminpass"),
    )
    assert response.status_code == 400


def test_delete_user_requires_admin(client, create_user):
    create_user("viewer", "viewerpass", UserRole.viewer)
    target = create_user("editor", "editorpass", UserRole.editor)

    response = client.delete(
        f"/api/v1/users/{target.id}",
        headers=basic_auth_header("viewer", "viewerpass"),
    )
    assert response.status_code == 403


def test_set_password_success(client, create_user, db_session):
    create_user("admin", "adminpass", UserRole.admin)
    target = create_user("target", "oldpassword", UserRole.viewer)

    response = client.patch(
        f"/api/v1/users/{target.id}/password",
        json={"password": "newpassword123"},
        headers=basic_auth_header("admin", "adminpass"),
    )
    assert response.status_code == 204

    # Verify the new password works for login
    response = client.get("/api/v1/users/me", headers=basic_auth_header("target", "newpassword123"))
    assert response.status_code == 200


def test_set_password_requires_admin(client, create_user):
    create_user("viewer", "viewerpass", UserRole.viewer)
    target = create_user("editor", "editorpass", UserRole.editor)

    response = client.patch(
        f"/api/v1/users/{target.id}/password",
        json={"password": "newpassword123"},
        headers=basic_auth_header("viewer", "viewerpass"),
    )
    assert response.status_code == 403


def test_set_password_user_not_found(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)

    response = client.patch(
        "/api/v1/users/99999/password",
        json={"password": "newpassword123"},
        headers=basic_auth_header("admin", "adminpass"),
    )
    assert response.status_code == 404

