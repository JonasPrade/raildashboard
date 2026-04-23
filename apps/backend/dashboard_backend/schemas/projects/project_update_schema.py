from __future__ import annotations

from typing import Optional

from .project_fields_base import ProjectFieldsBase


class ProjectUpdate(ProjectFieldsBase):
    """Partial update schema for Project (PATCH semantics — all fields optional)."""

    geojson_representation: Optional[str] = None
