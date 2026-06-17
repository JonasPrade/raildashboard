from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from dashboard_backend.core.permissions import (
    SYSTEM_ROLE_DESCRIPTIONS,
    SYSTEM_ROLE_NAMES,
    SYSTEM_ROLE_PERMISSIONS,
)
from dashboard_backend.models.roles import Role, RolePermission
from dashboard_backend.models.users import User


_UNSET = object()


def get_role_by_name(db: Session, name: str) -> Role | None:
    return db.query(Role).filter(Role.name == name).one_or_none()


def get_role_by_id(db: Session, role_id: int) -> Role | None:
    return db.query(Role).filter(Role.id == role_id).one_or_none()


def list_roles(db: Session) -> list[Role]:
    return db.query(Role).order_by(Role.name).all()


def count_users_with_role(db: Session, role_id: int) -> int:
    return db.query(User).filter(User.role_id == role_id).count()


def create_role(
    db: Session,
    *,
    name: str,
    description: str | None,
    permission_keys: Iterable[str],
) -> Role:
    role = Role(name=name, description=description, is_system=False)
    role.permissions = [
        RolePermission(permission_key=key) for key in dict.fromkeys(permission_keys)
    ]
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def update_role(
    db: Session,
    role: Role,
    *,
    name: object = _UNSET,
    description: object = _UNSET,
    permission_keys: object = _UNSET,
) -> Role:
    if name is not _UNSET:
        role.name = name  # type: ignore[assignment]
    if description is not _UNSET:
        role.description = description  # type: ignore[assignment]
    if permission_keys is not _UNSET:
        role.permissions = [
            RolePermission(permission_key=key)
            for key in dict.fromkeys(permission_keys)  # type: ignore[arg-type]
        ]
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role: Role) -> None:
    db.delete(role)
    db.commit()


def seed_system_roles(db: Session) -> None:
    """Create the viewer/editor/admin system roles and their permissions.

    Idempotent: existing roles keep their identity, missing permission rows are
    added. Mirrors the seed performed by the database migration so test setups
    (which build the schema from model metadata) reproduce production behaviour.
    """

    for name in SYSTEM_ROLE_NAMES:
        role = get_role_by_name(db, name)
        if role is None:
            role = Role(
                name=name,
                description=SYSTEM_ROLE_DESCRIPTIONS[name],
                is_system=True,
            )
            db.add(role)
            db.flush()
        existing_keys = role.permission_keys
        for key in SYSTEM_ROLE_PERMISSIONS[name]:
            if key not in existing_keys:
                db.add(RolePermission(role_id=role.id, permission_key=key))
    db.commit()
