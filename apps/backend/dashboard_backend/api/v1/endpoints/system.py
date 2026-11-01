"""System status beyond the Celery workers — the routing service and the
scheduled routine jobs."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_permission
from dashboard_backend.database import get_db
from dashboard_backend.schemas.system import RoutineJobsSchema, RoutingHealthSchema
from dashboard_backend.services.routine_jobs import routine_jobs_status
from dashboard_backend.services.routing_health import routing_health

router = APIRouter()


@router.get("/routing", response_model=RoutingHealthSchema)
def get_routing_health(_user=Depends(require_permission("settings.manage"))):
    """Is GraphHopper reachable right now? Probed on every call (one bounded request)."""
    return routing_health()


@router.get("/routine-jobs", response_model=RoutineJobsSchema)
def get_routine_jobs(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("settings.manage")),
):
    """Scheduled routine jobs: timetable, next slot, last run and whether one
    needs attention (feature-routine-abrufe.md, E3). Not part of /healthz."""
    return routine_jobs_status(db)
