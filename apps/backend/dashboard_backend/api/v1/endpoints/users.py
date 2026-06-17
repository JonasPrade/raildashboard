from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from dashboard_backend.core.permissions import ADMIN_ROLE_NAME
from dashboard_backend.core.security import hash_password, require_auth, require_permission
from dashboard_backend.crud import roles as roles_crud
from dashboard_backend.crud import users as users_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.users import UserCreate, UserPasswordUpdate, UserRead, UserUpdate


router = AuthRouter()


def _require_existing_role(db: Session, role_name: str) -> None:
    if roles_crud.get_role_by_name(db, role_name) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role")


@router.get("/me", response_model=UserRead)
def get_current_user_info(
    current_user: User = Depends(require_auth()),
):
    return current_user


@router.get("/", response_model=list[UserRead])
def list_users(
    _: None = Depends(require_permission("user.manage")),
    db: Session = Depends(get_db),
):
    return users_crud.get_users(db)


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    _: None = Depends(require_permission("user.manage")),
    db: Session = Depends(get_db),
):
    existing = users_crud.get_user_by_username(db, user_in.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    _require_existing_role(db, user_in.role)
    return users_crud.create_user(db, user_in, hash_password)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    body: UserUpdate,
    current_user: User = Depends(require_permission("user.manage")),
    db: Session = Depends(get_db),
):
    user = users_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.role is not None and user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role")

    if body.role is not None:
        _require_existing_role(db, body.role)
        # Protect against removing the final admin.
        if (
            user.role_name == ADMIN_ROLE_NAME
            and body.role != ADMIN_ROLE_NAME
            and users_crud.count_admins(db) <= 1
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the last admin",
            )

    new_username: str | None = None
    if body.username is not None and body.username != user.username:
        existing = users_crud.get_user_by_username(db, body.username)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
        new_username = body.username

    return users_crud.update_user(
        db,
        user,
        username=new_username,
        role=body.role,
    )


@router.patch("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def set_user_password(
    user_id: int,
    body: UserPasswordUpdate,
    current_user: User = Depends(require_permission("user.manage")),
    db: Session = Depends(get_db),
):
    user = users_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    users_crud.update_password(db, user, hash_password(body.password))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_permission("user.manage")),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    user = users_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role_name == ADMIN_ROLE_NAME and users_crud.count_admins(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete the last admin",
        )
    users_crud.delete_user(db, user)
