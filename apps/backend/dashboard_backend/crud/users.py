from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from dashboard_backend.models.users import User
from dashboard_backend.schemas.users import UserCreate


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).one_or_none()


def get_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.username).all()


def create_user(db: Session, user_in: UserCreate, password_hasher: Callable[[str], str]) -> User:
    hashed = password_hasher(user_in.password)
    db_user = User(username=user_in.username, hashed_password=hashed, role=user_in.role.value)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def count_users(db: Session) -> int:
    return db.query(User).count()

