from pydantic import BaseModel
from typing import Optional
from datetime import date

class SectionOfLineSchema(BaseModel):
    id: Optional[int] = None
    validity_date_start: Optional[date] = None
    validity_date_end: Optional[date] = None
    solim_code: Optional[str] = None
    sol_line_identification: Optional[str] = None
    sol_op_start: Optional[str] = None
    sol_op_end: Optional[str] = None
    sol_length: Optional[float] = None
    sol_nature: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True
