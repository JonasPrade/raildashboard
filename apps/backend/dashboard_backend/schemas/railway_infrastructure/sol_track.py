from pydantic import BaseModel
from typing import Optional
from datetime import date

class SOLTrackSchema(BaseModel):
    id: Optional[int] = None
    track_validity_date_start: Optional[date] = None
    track_validity_date_end: Optional[date] = None
    sol_track_identification: Optional[str] = None
    sol_track_direction: Optional[str] = None
    section_id: Optional[int] = None

    class Config:
        from_attributes = True
        populate_by_name = True
