from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_permission
from dashboard_backend.crud.finve_links import (
    FinveLinkConflict,
    FinveLinkError,
    permanent_projects,
    update_finve_projects,
)
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
from dashboard_backend.schemas.projects.link_finves_schema import (
    FinveProjectsSchema,
    FinveProjectsUpdate,
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


@router.patch("/{finve_id}/projects", response_model=FinveProjectsSchema)
def patch_finve_projects(
    finve_id: int,
    body: FinveProjectsUpdate,
    current_user: User = Depends(require_permission("finve.edit")),
    db: Session = Depends(get_db),
):
    """Add and/or remove permanent project links of a FinVe (Sammel-FinVe year
    links stay). Each changed project gets a changelog entry ``finve_ids`` and a
    recomputed planning state."""
    if not body.add_project_ids and not body.remove_project_ids:
        raise HTTPException(status_code=422, detail="Keine Projekte übergeben.")
    try:
        changed = update_finve_projects(
            db,
            finve_id,
            add_project_ids=body.add_project_ids,
            remove_project_ids=body.remove_project_ids,
            user=current_user,
        )
    except FinveLinkConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FinveLinkError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FinveProjectsSchema(
        finve_id=finve_id,
        projects=[{"id": p.id, "name": p.name} for p in permanent_projects(db, finve_id)],
        changed_project_ids=changed,
    )
