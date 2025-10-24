from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from dashboard_backend.core.security import hash_password, require_roles
from dashboard_backend.crud import users as users_crud
from dashboard_backend.database import get_db
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.users import UserCreate, UserRead, UserRole


router = AuthRouter()


@router.get("/", response_model=list[UserRead])
def list_users(
    _: None = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
):
    return users_crud.get_users(db)


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    _: None = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
):
    existing = users_crud.get_user_by_username(db, user_in.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    return users_crud.create_user(db, user_in, hash_password)

