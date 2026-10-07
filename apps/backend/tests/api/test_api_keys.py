"""Personal API keys: management endpoints and Bearer auth in the REST chain."""

from __future__ import annotations

from datetime import datetime, timedelta

from dashboard_backend.core import api_keys as api_key_core
from dashboard_backend.core.security import hash_password
from dashboard_backend.crud import api_keys as api_keys_crud
from dashboard_backend.models.api_keys import ApiKey
from dashboard_backend.models.roles import Role, RolePermission
from dashboard_backend.models.users import User
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _make_role_user(db, username: str, permission_keys: list[str]) -> User:
    role = Role(name=f"role-{username}", description=None, is_system=False)
    role.permissions = [RolePermission(permission_key=key) for key in permission_keys]
    db.add(role)
    db.flush()
    user = User(username=username, hashed_password=hash_password("password123"), role_id=role.id)
    db.add(user)
    db.commit()
    return user


def _create_key(client, headers, name="Laptop", scopes=None):
    body = {"name": name}
    if scopes is not None:
        body["scopes"] = scopes
    return client.post("/api/v1/api-keys/", json=body, headers=headers)


# --- Token format ------------------------------------------------------------


def test_generated_token_round_trips():
    generated = api_key_core.generate_key()
    assert generated.token.startswith("rdb_")
    prefix, secret = api_key_core.parse_token(generated.token)
    assert prefix == generated.prefix
    assert len(prefix) == api_key_core.PREFIX_LENGTH
    assert api_key_core.secret_matches(secret, generated.key_hash)
    assert not api_key_core.secret_matches(secret + "x", generated.key_hash)


def test_parse_token_rejects_foreign_formats():
    assert api_key_core.parse_token("abc") is None
    assert api_key_core.parse_token("rdb_short_secret") is None
    assert api_key_core.parse_token("rdb_abcdefghijkl_") is None


def test_key_permissions_intersect_scopes_without_bypass():
    owner = {"project.edit", "mcp.access"}
    assert api_key_core.key_permissions(owner, None) == owner
    assert api_key_core.key_permissions(owner, ["mcp.access", "user.manage"]) == {"mcp.access"}


# --- Management endpoints ----------------------------------------------------


def test_admin_creates_key_token_shown_once(client, create_user, db_session):
    create_user("admin", "adminpass", UserRole.admin)
    headers = basic_auth_header("admin", "adminpass")

    created = _create_key(client, headers, name="Claude Code")
    assert created.status_code == 201
    body = created.json()
    assert body["token"].startswith(f"rdb_{body['prefix']}_")
    assert body["scopes"] is None
    expires = datetime.fromisoformat(body["expires_at"])
    assert timedelta(days=89) < expires - datetime.utcnow() <= timedelta(days=90)

    listed = client.get("/api/v1/api-keys/", headers=headers)
    assert listed.status_code == 200
    assert [k["name"] for k in listed.json()] == ["Claude Code"]
    assert "token" not in listed.json()[0]
    assert "key_hash" not in listed.json()[0]

    stored = db_session.query(ApiKey).one()
    assert body["token"].split("_", 2)[2] not in stored.key_hash


def test_editor_cannot_create_key(client, create_user):
    create_user("editor", "pass1234", UserRole.editor)
    response = _create_key(client, basic_auth_header("editor", "pass1234"))
    assert response.status_code == 403


def test_custom_role_with_mcp_access_can_create_key(client, db_session):
    _make_role_user(db_session, "agentuser", ["mcp.access"])
    response = _create_key(client, basic_auth_header("agentuser", "password123"))
    assert response.status_code == 201


def test_unknown_scope_is_rejected(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)
    response = _create_key(client, basic_auth_header("admin", "adminpass"), scopes=["nope"])
    assert response.status_code == 400


def test_key_cannot_manage_keys(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)
    token = _create_key(client, basic_auth_header("admin", "adminpass")).json()["token"]

    assert client.get("/api/v1/api-keys/", headers=_bearer(token)).status_code == 403
    assert _create_key(client, _bearer(token)).status_code == 403
    assert client.get("/api/v1/api-keys/all", headers=_bearer(token)).status_code == 403


def test_revoke_own_key(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)
    headers = basic_auth_header("admin", "adminpass")
    created = _create_key(client, headers).json()

    assert client.get("/api/v1/users/me", headers=_bearer(created["token"])).status_code == 200
    assert client.delete(f"/api/v1/api-keys/{created['id']}", headers=headers).status_code == 204
    revoked = client.get("/api/v1/users/me", headers=_bearer(created["token"]))
    assert revoked.status_code == 401
    assert revoked.headers["www-authenticate"] == "Bearer"
    listed = client.get("/api/v1/api-keys/", headers=headers).json()
    assert listed[0]["revoked_at"] is not None


def test_foreign_keys_need_user_manage(client, create_user, db_session):
    create_user("admin", "adminpass", UserRole.admin)
    owner = _make_role_user(db_session, "agentuser", ["mcp.access"])
    owner_headers = basic_auth_header("agentuser", "password123")
    key_id = _create_key(client, owner_headers).json()["id"]

    other = _make_role_user(db_session, "other", ["mcp.access"])
    assert other.id != owner.id
    other_headers = basic_auth_header("other", "password123")
    assert client.delete(f"/api/v1/api-keys/{key_id}", headers=other_headers).status_code == 404
    assert client.get("/api/v1/api-keys/all", headers=other_headers).status_code == 403

    admin_headers = basic_auth_header("admin", "adminpass")
    all_keys = client.get("/api/v1/api-keys/all", headers=admin_headers).json()
    assert [k["username"] for k in all_keys] == ["agentuser"]
    assert client.delete(f"/api/v1/api-keys/{key_id}", headers=admin_headers).status_code == 204


# --- Bearer auth in the REST chain --------------------------------------------


def test_bearer_key_authenticates_rest_api(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)
    token = _create_key(client, basic_auth_header("admin", "adminpass")).json()["token"]

    me = client.get("/api/v1/users/me", headers=_bearer(token))
    assert me.status_code == 200
    assert me.json()["username"] == "admin"
    patched = client.patch(
        "/api/v1/settings/", json={"map_group_mode": "all"}, headers=_bearer(token)
    )
    assert patched.status_code == 200


def test_scopes_restrict_admin_key(client, create_user):
    # No super-admin bypass for keys: a read-only admin key may not edit settings.
    create_user("admin", "adminpass", UserRole.admin)
    token = _create_key(
        client, basic_auth_header("admin", "adminpass"), scopes=["mcp.access"]
    ).json()["token"]
    response = client.patch(
        "/api/v1/settings/", json={"map_group_mode": "all"}, headers=_bearer(token)
    )
    assert response.status_code == 403


def test_invalid_tokens_are_401(client, create_user):
    create_user("admin", "adminpass", UserRole.admin)
    token = _create_key(client, basic_auth_header("admin", "adminpass")).json()["token"]
    prefix = token.split("_")[1]

    for bad in ("garbage", f"rdb_{'x' * 12}_secret", f"rdb_{prefix}_wrongsecret"):
        response = client.get("/api/v1/users/me", headers=_bearer(bad))
        assert response.status_code == 401, bad


def test_expired_key_is_401(client, create_user, db_session):
    create_user("admin", "adminpass", UserRole.admin)
    created = _create_key(client, basic_auth_header("admin", "adminpass")).json()
    api_key = db_session.query(ApiKey).filter(ApiKey.id == created["id"]).one()
    api_key.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()

    assert client.get("/api/v1/users/me", headers=_bearer(created["token"])).status_code == 401


def test_last_used_is_throttled(create_user, db_session):
    user = create_user("admin", "adminpass", UserRole.admin)
    api_key, token = api_keys_crud.create_api_key(db_session, user, "k", None)
    start = datetime(2026, 1, 1, 12, 0, 0)

    api_keys_crud.authenticate_token(db_session, token, now=start)
    assert api_key.last_used_at == start
    api_keys_crud.authenticate_token(db_session, token, now=start + timedelta(seconds=30))
    assert api_key.last_used_at == start
    later = start + timedelta(minutes=2)
    api_keys_crud.authenticate_token(db_session, token, now=later)
    assert api_key.last_used_at == later


def test_cookie_and_basic_unchanged(client, create_user):
    create_user("editor", "pass1234", UserRole.editor)
    assert client.get("/api/v1/users/me", headers=basic_auth_header("editor", "pass1234")).status_code == 200
    assert client.post(
        "/api/v1/auth/session", json={"username": "editor", "password": "pass1234"}
    ).status_code == 204
    assert client.get("/api/v1/users/me").status_code == 200
