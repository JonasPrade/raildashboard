from __future__ import annotations

from fastapi import Depends

from dashboard_backend.core.permissions import PERMISSIONS
from dashboard_backend.core.security import require_permission
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.roles import PermissionSchema


router = AuthRouter()


@router.get("/", response_model=list[PermissionSchema])
def list_permissions(
    _: None = Depends(require_permission("role.manage")),
):
    """Return the capability catalog (keys + labels + groups) for the admin UI."""

    return [
        PermissionSchema(key=perm.key, label=perm.label, group=perm.group)
        for perm in PERMISSIONS
    ]
