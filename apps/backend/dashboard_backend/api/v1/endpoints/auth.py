from __future__ import annotations

from fastapi import Depends, HTTPException, Response, status
from fastapi.routing import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dashboard_backend.core.security import (
    _SESSION_COOKIE,
    _SESSION_MAX_AGE,
    create_session_token,
    require_session,
    verify_password,
)
from dashboard_backend.crud import users as users_crud
from dashboard_backend.database import get_db
from dashboard_backend.core.config import settings

router = APIRouter()


class SessionCredentials(BaseModel):
    username: str
    password: str


@router.post("/session", status_code=status.HTTP_204_NO_CONTENT)
def create_session(
    body: SessionCredentials,
    response: Response,
    db: Session = Depends(get_db),
):
    """Validate credentials and issue an httpOnly session cookie."""
    user = users_crud.get_user_by_username(db, body.username)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_session_token(user.id)
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="strict",
        max_age=_SESSION_MAX_AGE,
    )


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    response: Response,
    _=Depends(require_session()),
):
    """Clear the session cookie (logout)."""
    response.delete_cookie(key=_SESSION_COOKIE, httponly=True, samesite="strict")
