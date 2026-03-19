from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from collections.abc import Iterable
from typing import Callable

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional
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


_SESSION_COOKIE = "session"
_SESSION_MAX_AGE = 7 * 24 * 3600  # 7 days in seconds


def _get_secret_key() -> bytes:
    from dashboard_backend.core.config import settings  # local import to avoid circular
    return settings.session_secret_key.encode("utf-8")


def create_session_token(user_id: int) -> str:
    """Return a signed session token: base64url(payload).base64url(signature)."""
    payload = f"{user_id}:{int(time.time())}".encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    sig = hmac.new(_get_secret_key(), payload_b64.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    return f"{payload_b64}.{sig_b64}"


def verify_session_token(token: str) -> int | None:
    """Verify signature and expiry. Returns user_id or None."""
    try:
        payload_b64, sig_b64 = token.rsplit(".", 1)
    except ValueError:
        return None

    expected_sig = hmac.new(_get_secret_key(), payload_b64.encode("ascii"), hashlib.sha256).digest()
    expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b"=").decode("ascii")
    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        return None

    try:
        padding = 4 - len(payload_b64) % 4
        payload = base64.urlsafe_b64decode(payload_b64 + "=" * padding).decode("utf-8")
        user_id_str, ts_str = payload.split(":", 1)
        user_id = int(user_id_str)
        ts = int(ts_str)
    except (ValueError, UnicodeDecodeError):
        return None

    if time.time() - ts > _SESSION_MAX_AGE:
        return None

    return user_id


def require_session():
    """FastAPI dependency: reads session cookie, returns User or raises 401."""
    def dependency(
        session: str | None = Cookie(default=None, alias=_SESSION_COOKIE),
        db: Session = Depends(get_db),
    ):
        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        user_id = verify_session_token(session)
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
        user = users_crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user

    return dependency


_optional_security = HTTPBasic(auto_error=False)


def require_auth():
    """FastAPI dependency: accepts either session cookie or HTTP Basic Auth."""
    def dependency(
        session: Optional[str] = Cookie(default=None, alias=_SESSION_COOKIE),
        credentials: Optional[HTTPBasicCredentials] = Depends(_optional_security),
        db: Session = Depends(get_db),
    ):
        if session:
            user_id = verify_session_token(session)
            if user_id is not None:
                user = users_crud.get_user_by_id(db, user_id)
                if user:
                    return user
        if credentials:
            return _authenticate(credentials, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )

    return dependency


def has_role_dependency(dependency) -> bool:
    return getattr(dependency, "__is_role_dependency__", False)


def ensure_authenticated_dependency(dependencies: Iterable[DependsParam]) -> bool:
    for dep in dependencies:
        if isinstance(dep, DependsParam) and has_role_dependency(dep.dependency):
            return True
    return False

