from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProjectTextTypeSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ProjectTextTypeCreate(BaseModel):
    name: str


class ProjectTextSchema(BaseModel):
    id: int
    header: str
    weblink: Optional[str] = None
    text: Optional[str] = None
    type: int
    logo_url: Optional[str] = None
    created_at: int
    updated_at: int
    text_type: ProjectTextTypeSchema

    model_config = ConfigDict(from_attributes=True)


class ProjectTextCreate(BaseModel):
    header: str
    weblink: Optional[str] = None
    text: Optional[str] = None
    type: int
    logo_url: Optional[str] = None


class ProjectTextUpdate(BaseModel):
    header: Optional[str] = None
    weblink: Optional[str] = None
    text: Optional[str] = None
    type: Optional[int] = None
    logo_url: Optional[str] = None
