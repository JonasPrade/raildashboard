from __future__ import annotations

from pydantic import BaseModel


class UnassignedFinveSchema(BaseModel):
    id: int
    name: str | None
    is_sammel_finve: bool
    starting_year: int | None

    model_config = {"from_attributes": True}


class UnassignedVibEntrySchema(BaseModel):
    id: int
    vib_name_raw: str
    vib_section: str | None
    category: str
    report_year: int

    model_config = {"from_attributes": True}


class AssignProjectsInput(BaseModel):
    project_ids: list[int]
