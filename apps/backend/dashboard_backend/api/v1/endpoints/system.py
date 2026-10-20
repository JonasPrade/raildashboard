"""System status beyond the Celery workers — currently the routing service."""

from fastapi import APIRouter, Depends

from dashboard_backend.core.security import require_permission
from dashboard_backend.schemas.system import RoutingHealthSchema
from dashboard_backend.services.routing_health import routing_health

router = APIRouter()


@router.get("/routing", response_model=RoutingHealthSchema)
def get_routing_health(_user=Depends(require_permission("settings.manage"))):
    """Is GraphHopper reachable right now? Probed on every call (one bounded request)."""
    return routing_health()
