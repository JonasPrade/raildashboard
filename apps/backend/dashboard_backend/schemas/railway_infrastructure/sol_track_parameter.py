from pydantic import BaseModel
from typing import Optional

class SOLTrackParameterSchema(BaseModel):
    id: Optional[int] = None
    parameter_id: Optional[str] = None
    is_applicable: Optional[str] = None
    value: Optional[str] = None
    optional_value: Optional[str] = None
    track_id: Optional[int] = None
    manual_added: Optional[bool] = None

    class Config:
        from_attributes = True
        populate_by_name = True