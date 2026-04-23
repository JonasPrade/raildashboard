from __future__ import annotations

from pydantic import BaseModel, Field


class LinkFinvesInput(BaseModel):
    finve_ids: list[int] = Field(default_factory=list)
