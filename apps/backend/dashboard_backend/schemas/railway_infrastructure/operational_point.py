from pydantic import BaseModel, Field
from typing import Optional

class OperationalPointSchema(BaseModel):
    id: Optional[int] = None
    op_id: Optional[str]
    name: Optional[str]
    type: Optional[str]
    country_code: Optional[str] = Field(max_length=2)
    latitude: Optional[float]
    longitude: Optional[float]
    validity_date_start: Optional[str]
    validity_date_end: Optional[str]
    railway_location: Optional[str]
    railway_location_km: Optional[float]

    class Config:
        from_attributes = True
        populate_by_name = True