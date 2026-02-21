from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    viewer = "viewer"
    editor = "editor"
    admin = "admin"


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    role: UserRole


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRead(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    role: UserRole


class UserPasswordUpdate(BaseModel):
    password: str = Field(min_length=8, max_length=128)

