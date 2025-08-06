from pydantic import BaseModel
from typing import List

class RouteRequest(BaseModel):
    start_op: str
    end_op: str

class RouteResponse(BaseModel):
    sectionofline_ids: List[int]