from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from dashboard_backend.core.permissions import is_valid_permission
from dashboard_backend.core.security import require_permission
from dashboard_backend.crud import roles as roles_crud
from dashboard_backend.database import get_db
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.roles import RoleCreate, RoleRead, RoleUpdate


router = AuthRouter()

_require_role_manage = Depends(require_permission("role.manage"))


def _validate_permission_keys(keys: list[str]) -> None:
    unknown = [key for key in keys if not is_valid_permission(key)]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown permission keys: {', '.join(sorted(set(unknown)))}",
        )


@router.get("/", response_model=list[RoleRead])
def list_roles(
    _: None = _require_role_manage,
    db: Session = Depends(get_db),
):
    return roles_crud.list_roles(db)


@router.post("/", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(
    body: RoleCreate,
    _: None = _require_role_manage,
    db: Session = Depends(get_db),
):
    if roles_crud.get_role_by_name(db, body.name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role name already exists")
    _validate_permission_keys(body.permissions)
    return roles_crud.create_role(
        db,
        name=body.name,
        description=body.description,
        permission_keys=body.permissions,
    )


@router.patch("/{role_id}", response_model=RoleRead)
def update_role(
    role_id: int,
    body: RoleUpdate,
    _: None = _require_role_manage,
    db: Session = Depends(get_db),
):
    role = roles_crud.get_role_by_id(db, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    data = body.model_dump(exclude_unset=True)

    if role.is_system:
        if "name" in data and data["name"] != role.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot rename a system role",
            )
        if "description" in data and data["description"] != role.description:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change the description of a system role",
            )

    if "name" in data and data["name"] != role.name:
        if roles_crud.get_role_by_name(db, data["name"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Role name already exists"
            )

    if "permissions" in data:
        _validate_permission_keys(data["permissions"])

    kwargs = {}
    if "name" in data:
        kwargs["name"] = data["name"]
    if "description" in data:
        kwargs["description"] = data["description"]
    if "permissions" in data:
        kwargs["permission_keys"] = data["permissions"]

    return roles_crud.update_role(db, role, **kwargs)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    _: None = _require_role_manage,
    db: Session = Depends(get_db),
):
    role = roles_crud.get_role_by_id(db, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a system role",
        )
    if roles_crud.count_users_with_role(db, role_id) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a role that is still assigned to users",
        )
    roles_crud.delete_role(db, role)
