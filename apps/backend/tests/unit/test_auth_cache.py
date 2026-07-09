"""Basic-auth credential cache + eager-loaded user lookup (#92, option b)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from dashboard_backend.core import security
from dashboard_backend.crud import users as users_crud
from dashboard_backend.models.roles import Role, RolePermission
from dashboard_backend.models.users import User


@pytest.fixture(autouse=True)
def clean_cache():
    security._basic_cache.clear()
    yield
    security._basic_cache.clear()


@pytest.fixture()
def pbkdf2_counter(monkeypatch):
    counter = {"n": 0}
    original = security._derive_key

    def counted(password, salt):
        counter["n"] += 1
        return original(password, salt)

    monkeypatch.setattr(security, "_derive_key", counted)
    return counter


def test_second_verification_skips_pbkdf2(pbkdf2_counter):
    stored = security.hash_password("secret123")
    baseline = pbkdf2_counter["n"]  # hash_password itself derives once

    assert security._verify_password_cached("alice", "secret123", stored) is True
    assert pbkdf2_counter["n"] == baseline + 1  # full verify

    assert security._verify_password_cached("alice", "secret123", stored) is True
    assert pbkdf2_counter["n"] == baseline + 1  # cache hit — no PBKDF2


def test_wrong_password_fails_and_does_not_evict(pbkdf2_counter):
    stored = security.hash_password("secret123")
    assert security._verify_password_cached("alice", "secret123", stored) is True

    assert security._verify_password_cached("alice", "wrong", stored) is False
    # The legitimate cached credential must survive the failed attempt.
    before = pbkdf2_counter["n"]
    assert security._verify_password_cached("alice", "secret123", stored) is True
    assert pbkdf2_counter["n"] == before


def test_password_change_invalidates_cache():
    stored_old = security.hash_password("secret123")
    assert security._verify_password_cached("alice", "secret123", stored_old) is True

    stored_new = security.hash_password("newpass456")
    # Old password against the new stored hash: fingerprint mismatch → full
    # verify → False. New password verifies.
    assert security._verify_password_cached("alice", "secret123", stored_new) is False
    assert security._verify_password_cached("alice", "newpass456", stored_new) is True


def test_expired_entry_reverifies(monkeypatch, pbkdf2_counter):
    stored = security.hash_password("secret123")
    assert security._verify_password_cached("alice", "secret123", stored) is True
    before = pbkdf2_counter["n"]

    expiry, fingerprint = security._basic_cache["alice"]
    security._basic_cache["alice"] = (expiry - security._BASIC_CACHE_TTL_SECONDS - 1, fingerprint)

    assert security._verify_password_cached("alice", "secret123", stored) is True
    assert pbkdf2_counter["n"] == before + 1  # expired → full verify again


def test_user_lookup_loads_role_and_permissions_in_one_query():
    engine = create_engine("sqlite:///:memory:")
    for table in (Role.__table__, RolePermission.__table__, User.__table__):
        table.create(bind=engine)
    session = sessionmaker(bind=engine)()

    role = Role(name="editor", is_system=True)
    role.permissions = [RolePermission(permission_key="project.edit")]
    session.add(role)
    session.flush()
    session.add(User(username="alice", hashed_password="x:y", role_id=role.id))
    session.commit()
    session.expunge_all()

    counter = {"n": 0}

    def _count(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    event.listen(engine, "before_cursor_execute", _count)
    try:
        user = users_crud.get_user_by_username(session, "alice")
        assert user is not None
        assert user.has_permission("project.edit")
    finally:
        event.remove(engine, "before_cursor_execute", _count)

    assert counter["n"] == 1, f"expected a single eager-loaded query, got {counter['n']}"
    session.close()
    engine.dispose()
