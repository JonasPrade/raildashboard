"""Capability-based gating: a role holding a capability passes the gate, a role
without it gets 403, admin bypasses, and unauthenticated requests get 401.

Uses ``/settings`` (gated by ``settings.manage``) and ``/users`` (gated by
``user.manage``) — endpoints whose responses don't touch tables outside the
in-memory test schema.
"""

from dashboard_backend.core.security import hash_password
from dashboard_backend.models.roles import Role, RolePermission
from dashboard_backend.models.users import User
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def _make_role_user(db, username: str, password: str, permission_keys: list[str]) -> User:
    role = Role(name=f"role-{username}", description=None, is_system=False)
    role.permissions = [RolePermission(permission_key=key) for key in permission_keys]
    db.add(role)
    db.flush()
    user = User(username=username, hashed_password=hash_password(password), role_id=role.id)
    db.add(user)
    db.commit()
    return user


def _patch_settings(client, username, password):
    return client.patch(
        "/api/v1/settings/",
        json={"map_group_mode": "all"},
        headers=basic_auth_header(username, password),
    )


def test_capability_grants_access(client, db_session):
    _make_role_user(db_session, "settingsmgr", "password123", ["settings.manage"])
    assert _patch_settings(client, "settingsmgr", "password123").status_code == 200


def test_missing_capability_is_forbidden(client, db_session):
    _make_role_user(db_session, "nobody", "password123", ["project.edit"])
    assert _patch_settings(client, "nobody", "password123").status_code == 403


def test_admin_bypasses_permission_check(client, create_user):
    # The admin system role holds no explicit settings.manage row, yet may edit.
    create_user("admin", "adminpass", UserRole.admin)
    assert _patch_settings(client, "admin", "adminpass").status_code == 200


def test_unauthenticated_is_401(client):
    response = client.patch("/api/v1/settings/", json={"map_group_mode": "all"})
    assert response.status_code == 401


def test_user_manage_capability_gates_user_admin(client, db_session):
    _make_role_user(db_session, "usermgr", "password123", ["user.manage"])
    ok = client.get("/api/v1/users/", headers=basic_auth_header("usermgr", "password123"))
    assert ok.status_code == 200

    _make_role_user(db_session, "plain", "password123", ["project.edit"])
    forbidden = client.get("/api/v1/users/", headers=basic_auth_header("plain", "password123"))
    assert forbidden.status_code == 403
