from __future__ import annotations

from sqlalchemy.orm import Session

from dashboard_backend.core.permissions import (
    SYSTEM_ROLE_DESCRIPTIONS,
    SYSTEM_ROLE_NAMES,
    SYSTEM_ROLE_PERMISSIONS,
)
from dashboard_backend.models.roles import Role, RolePermission


def get_role_by_name(db: Session, name: str) -> Role | None:
    return db.query(Role).filter(Role.name == name).one_or_none()


def get_role_by_id(db: Session, role_id: int) -> Role | None:
    return db.query(Role).filter(Role.id == role_id).one_or_none()


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
