from __future__ import annotations

from pydantic import Field

from .project_fields_base import ProjectFieldsBase


class ProjectCreate(ProjectFieldsBase):
    """Create schema for Project. Only `name` is required."""

    name: str = Field(min_length=1)
