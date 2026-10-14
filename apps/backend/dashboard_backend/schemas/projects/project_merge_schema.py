from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ProjectMergeRequest(BaseModel):
    """Merge ``merged_id`` into ``survivor_id`` (see feature-project-merge.md)."""

    survivor_id: int
    merged_id: int
    geometry_from: Literal["survivor", "merged"] = "survivor"
    # False: only return the plan, write nothing.
    apply: bool = False


class ProjectMergeLinkCount(BaseModel):
    moved: int
    dropped: int


class ProjectMergeSide(BaseModel):
    id: int
    name: str
    project_number: str | None = None


class ProjectMergeResult(BaseModel):
    survivor: ProjectMergeSide
    merged: ProjectMergeSide
    geometry_from: Literal["survivor", "merged"]
    field_changes: dict[str, dict[str, Any]]
    geometry_changed: bool
    progress_changes: list[str]
    links: dict[str, ProjectMergeLinkCount]
    subprojects_moved: list[int]
    warnings: list[str]
    applied: bool
