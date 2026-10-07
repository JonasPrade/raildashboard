from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from dashboard_backend.core import api_keys as api_key_core
from dashboard_backend.models.api_keys import ApiKey
from dashboard_backend.models.roles import Role
from dashboard_backend.models.users import User

# ``last_used_at`` is written at most once per interval per key, so a burst of
# agent tool calls does not turn every request into a database write.
LAST_USED_WRITE_INTERVAL = timedelta(minutes=1)

_KEY_EAGER = joinedload(ApiKey.user).joinedload(User.role).joinedload(Role.permissions)


def create_api_key(
    db: Session,
    user: User,
    name: str,
    scopes: list[str] | None,
    now: datetime | None = None,
) -> tuple[ApiKey, str]:
    """Create a key and return it together with the clear-text token (shown once)."""

    now = now or datetime.utcnow()
    generated = api_key_core.generate_key()
    api_key = ApiKey(
        user_id=user.id,
        name=name,
        prefix=generated.prefix,
        key_hash=generated.key_hash,
        scopes=scopes,
        created_at=now,
        expires_at=now + api_key_core.DEFAULT_KEY_LIFETIME,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key, generated.token


def list_api_keys(db: Session, user_id: int | None = None) -> list[ApiKey]:
    """Keys of one user, or of every user when ``user_id`` is None; newest first."""

    query = db.query(ApiKey).options(joinedload(ApiKey.user))
    if user_id is not None:
        query = query.filter(ApiKey.user_id == user_id)
    return query.order_by(ApiKey.created_at.desc(), ApiKey.id.desc()).all()


def get_api_key(db: Session, key_id: int) -> ApiKey | None:
    return db.query(ApiKey).filter(ApiKey.id == key_id).one_or_none()


def revoke_api_key(db: Session, api_key: ApiKey, now: datetime | None = None) -> ApiKey:
    if api_key.revoked_at is None:
        api_key.revoked_at = now or datetime.utcnow()
        db.commit()
        db.refresh(api_key)
    return api_key


def authenticate_token(db: Session, token: str, now: datetime | None = None) -> ApiKey | None:
    """Resolve a bearer token to an active key (owner eager-loaded) or None."""

    parsed = api_key_core.parse_token(token)
    if parsed is None:
        return None
    prefix, secret = parsed
    api_key = db.query(ApiKey).options(_KEY_EAGER).filter(ApiKey.prefix == prefix).one_or_none()
    if api_key is None or not api_key_core.secret_matches(secret, api_key.key_hash):
        return None
    now = now or datetime.utcnow()
    if not api_key.is_active(now):
        return None
    if api_key.last_used_at is None or now - api_key.last_used_at >= LAST_USED_WRITE_INTERVAL:
        api_key.last_used_at = now
        db.commit()
    return api_key


def effective_key_permissions(api_key: ApiKey) -> set[str]:
    return api_key_core.key_permissions(api_key.user.effective_permissions, api_key.scopes)
