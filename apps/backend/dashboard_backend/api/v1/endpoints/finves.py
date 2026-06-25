from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_permission
from dashboard_backend.crud.finves import (
    list_finves,
    list_sammel_finves_progress,
    set_finve_progress_phase,
)
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.projects.progress_schema import (
    FinveProgressPhaseUpdate,
    SammelFinveProgressSchema,
)
from dashboard_backend.schemas.projects.project_schema import FinveListItemSchema

router = AuthRouter()


@router.get("/", response_model=list[FinveListItemSchema])
def get_finves(db: Session = Depends(get_db)):
    """Return all Finanzierungsvereinbarungen with linked project info."""
    return list_finves(db)


# NOTE: must be declared before any "/{finve_id}" route so "sammel-progress"
# is not captured as a finve id.
@router.get("/sammel-progress", response_model=list[SammelFinveProgressSchema])
def get_sammel_finve_progress(db: Session = Depends(get_db)):
    """Sammel-FinVes with auto-detected vs. manual planning-phase mapping."""
    return list_sammel_finves_progress(db)


@router.patch("/{finve_id}/progress-phase", response_model=list[SammelFinveProgressSchema])
def patch_finve_progress_phase(
    finve_id: int,
    body: FinveProgressPhaseUpdate,
    current_user: User = Depends(require_permission("progress.edit")),
    db: Session = Depends(get_db),
):
    """Set/clear a FinVe's manual planning-phase override; returns the refreshed list."""
    finve = set_finve_progress_phase(db, finve_id, body.progress_phase)
    if finve is None:
        raise HTTPException(status_code=404, detail="FinVe not found")
    return list_sammel_finves_progress(db)
