from __future__ import annotations

import base64
import hashlib
import hmac
import os
from collections.abc import Iterable
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.params import Depends as DependsParam
from sqlalchemy.orm import Session

from dashboard_backend.crud import users as users_crud
from dashboard_backend.database import get_db
from dashboard_backend.schemas.users import UserRole


PasswordHasher = Callable[[str], str]


_security = HTTPBasic()
_ITERATIONS = 390_000


def _derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS, dklen=32)


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC with a random salt."""

    salt = os.urandom(16)
    key = _derive_key(password, salt)
    return f"{base64.b64encode(salt).decode()}:{base64.b64encode(key).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Validate a password against the stored hash value."""

    try:
        salt_b64, key_b64 = stored_hash.split(":", 1)
        salt = base64.b64decode(salt_b64.encode())
        expected_key = base64.b64decode(key_b64.encode())
    except (ValueError, TypeError, base64.binascii.Error):
        return False

    derived_key = _derive_key(password, salt)
    return hmac.compare_digest(derived_key, expected_key)


def _authenticate(credentials: HTTPBasicCredentials, db: Session):
    user = users_crud.get_user_by_username(db, credentials.username)
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user


def require_roles(*roles: UserRole):
    allowed_roles: set[str] | None = {role.value for role in roles} if roles else None

    def dependency(
        credentials: HTTPBasicCredentials = Depends(_security),
        db: Session = Depends(get_db),
    ):
        user = _authenticate(credentials, db)
        if allowed_roles is not None and user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough privileges",
            )
        return user

    dependency.__is_role_dependency__ = True  # type: ignore[attr-defined]
    dependency.__required_roles__ = allowed_roles  # type: ignore[attr-defined]
    return dependency


def has_role_dependency(dependency) -> bool:
    return getattr(dependency, "__is_role_dependency__", False)


def ensure_authenticated_dependency(dependencies: Iterable[DependsParam]) -> bool:
    for dep in dependencies:
        if isinstance(dep, DependsParam) and has_role_dependency(dep.dependency):
            return True
    return False

