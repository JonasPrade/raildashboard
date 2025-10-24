from dashboard_backend.crud import users as users_crud
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


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

