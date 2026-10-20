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


class UnassignedInfraplanEntrySchema(BaseModel):
    id: int
    report_year: int
    section: str
    lfd_nr: int
    page: int | None
    primary_number: str | None
    bezeichnung: str | None
    massnahme: str | None
    laender: str | None
    state_raw: str | None
    ibn_raw: str | None
    cost_mio: float | None


class AssignProjectsInput(BaseModel):
    project_ids: list[int]
