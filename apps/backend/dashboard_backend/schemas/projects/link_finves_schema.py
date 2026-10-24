from __future__ import annotations

from pydantic import BaseModel, Field


class LinkFinvesInput(BaseModel):
    finve_ids: list[int] = Field(default_factory=list)


class FinveProjectsUpdate(BaseModel):
    """Add/remove permanent project links of one FinVe."""

    add_project_ids: list[int] = Field(default_factory=list)
    remove_project_ids: list[int] = Field(default_factory=list)


class FinveProjectRef(BaseModel):
    id: int
    name: str


class FinveProjectsSchema(BaseModel):
    """The FinVe's permanent project links after a change."""

    finve_id: int
    projects: list[FinveProjectRef]
    changed_project_ids: list[int] = Field(default_factory=list)
