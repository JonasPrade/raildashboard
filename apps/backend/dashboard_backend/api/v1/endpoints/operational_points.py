from fastapi import Depends, Query
from sqlalchemy.orm import Session
from typing import List

from dashboard_backend.crud.operational_points import search_operational_points
from dashboard_backend.database import get_db
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.railway_infrastructure.operational_point import OperationalPointRef

router = AuthRouter()


@router.get("/", response_model=List[OperationalPointRef])
def search_ops(
    q: str = Query("", description="Search by name or op_id"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search operational points (stations/stops) by name or ID. Public endpoint."""
    return search_operational_points(db, q, limit)
