# dashboard_backend/api/v1/endpoints/route.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dashboard_backend.routing.schemas import RouteRequest, RouteResponse
from dashboard_backend.database import get_db
from dashboard_backend.routing.core import find_route_section_of_lines

router = APIRouter()

@router.post("/", response_model=RouteResponse)
def get_route(request: RouteRequest, db: Session = Depends(get_db)):
    result = find_route_section_of_lines(db, request.start_op, request.end_op)
    if not result:
        raise HTTPException(status_code=404, detail="Keine Route gefunden")
    return RouteResponse(sectionofline_ids=result)
