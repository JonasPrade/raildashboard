"""Schemas for guide-section overrides ("Anleitungen" editing)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GuideOverrideSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guide_slug: str
    section_key: str
    body_markdown: str
    updated_at: datetime | None = None
    username_snapshot: str | None = None


class GuideOverrideInput(BaseModel):
    """Replace one section's markdown body. An empty body is rejected —
    resetting to the bundled default is a DELETE, not an empty save."""

    body_markdown: str = Field(min_length=1, max_length=20_000)
