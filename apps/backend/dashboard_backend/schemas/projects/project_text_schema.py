from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectTextTypeSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ProjectTextTypeCreate(BaseModel):
    name: str


# Fixed display styles of a text category (docs/features/feature-text-categories.md).
TextCategoryStyle = Literal["neutral", "info", "warning", "critical"]


class ProjectTextCategorySchema(BaseModel):
    id: int
    name: str
    style: TextCategoryStyle

    model_config = ConfigDict(from_attributes=True)


class ProjectTextCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    style: TextCategoryStyle


class TextAttachmentSchema(BaseModel):
    id: int
    text_id: int
    filename: str
    mime_type: str
    file_size: int
    uploaded_at: datetime
    uploaded_by_user_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


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
    category_id: Optional[int] = None
    # Null only for texts written by code from before categories; shown as the default.
    category: Optional[ProjectTextCategorySchema] = None
    is_public: bool = True
    attachments: list[TextAttachmentSchema] = []

    model_config = ConfigDict(from_attributes=True)


class ProjectTextCreate(BaseModel):
    header: str
    weblink: Optional[str] = None
    text: Optional[str] = None
    type: int
    logo_url: Optional[str] = None
    # Omitted → default category („Info“).
    category_id: Optional[int] = None
    is_public: bool = True


class ProjectTextUpdate(BaseModel):
    header: Optional[str] = None
    weblink: Optional[str] = None
    text: Optional[str] = None
    type: Optional[int] = None
    logo_url: Optional[str] = None
    category_id: Optional[int] = None
    is_public: Optional[bool] = None
