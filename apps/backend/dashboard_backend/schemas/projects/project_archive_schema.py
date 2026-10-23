"""Archive / restore a project (docs/features/feature-project-archive.md)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from dashboard_backend.schemas.projects.project_schema import ProjectSchema


class ProjectArchiveRequest(BaseModel):
    reason: str = Field(min_length=1, description="Why the project is archived (mandatory).")


class ProjectUnarchiveRequest(BaseModel):
    reason: Optional[str] = Field(
        default=None, description="Optional note for the changelog."
    )


class ProjectArchiveResult(BaseModel):
    project: ProjectSchema
    kept_links: dict[str, int] = Field(
        default_factory=dict,
        description="Historical source links the project keeps (VIB, PFA, Infraplan, "
        "Fulda, Bauportal, media) — they no longer reach the parent.",
    )


class ArchivedProjectSchema(BaseModel):
    """One row of the admin archive page."""

    id: int
    name: str
    project_number: Optional[str] = None
    archived_reason: Optional[str] = None
    archived_at: Optional[datetime] = None
    superior_project_id: Optional[int] = None
    superior_project_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
