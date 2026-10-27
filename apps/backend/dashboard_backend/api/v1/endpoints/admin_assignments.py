from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_permission
from dashboard_backend.crud.finve_links import FinveLinkConflict, FinveLinkError
from dashboard_backend.crud.admin_assignments import (
    assign_finve_to_projects,
    assign_vib_entry_to_projects,
    get_finve,
    get_vib_entry,
    list_unassigned_finves,
    list_unassigned_vib_entries,
)
from dashboard_backend.crud import gvfg as gvfg_crud
from dashboard_backend.crud.projects.progress import list_progress_conflicts
from dashboard_backend.crud import infraplan_import as infraplan_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.gvfg import GvfgEntry
from dashboard_backend.models.infraplan import InfraplanEntry
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.admin_assignments import (
    AssignProjectsInput,
    UnassignedFinveSchema,
    UnassignedInfraplanEntrySchema,
    UnassignedVibEntrySchema,
)
from dashboard_backend.schemas.gvfg import GvfgEntrySchema
from dashboard_backend.schemas.projects.progress_schema import ProgressConflictRowSchema
from dashboard_backend.schemas.tasks import TaskLaunchResponse
router = AuthRouter()

_require_editor = Depends(require_permission("assignment.manage"))


@router.get("/progress-conflicts", response_model=list[ProgressConflictRowSchema])
def get_progress_conflicts(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("progress.edit")),
) -> list[dict]:
    """Projects whose planning state has a set-back conflict (newer report with
    a lower phase than older information)."""
    return list_progress_conflicts(db)


@router.post("/progress-recompute", response_model=TaskLaunchResponse, status_code=202)
def start_progress_recompute(
    _current_user: User = Depends(require_permission("progress.edit")),
) -> TaskLaunchResponse:
    """Recompute the planning state of every project (Celery) — needed after a
    deploy that changes the derivation; the lazy resync only covers projects
    that are read."""
    from dashboard_backend.tasks.progress import recompute_all_progress_task

    task = recompute_all_progress_task.delay()
    return TaskLaunchResponse(task_id=task.id)


@router.post("/overlap-recompute", response_model=TaskLaunchResponse, status_code=202)
def start_overlap_recompute(
    _current_user: User = Depends(require_permission("project.edit")),
) -> TaskLaunchResponse:
    """Rebuild the map overlaps and lanes of every project (Celery). Saving a
    project keeps them current; this is for a full rebuild, e.g. after a bulk
    geometry import."""
    from dashboard_backend.tasks.project_overlap import recompute_all_overlaps_task

    task = recompute_all_overlaps_task.delay()
    return TaskLaunchResponse(task_id=task.id)


@router.get("/unassigned-finves", response_model=list[UnassignedFinveSchema])
def get_unassigned_finves(
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> list[UnassignedFinveSchema]:
    return list_unassigned_finves(db)


@router.get("/unassigned-vib-entries", response_model=list[UnassignedVibEntrySchema])
def get_unassigned_vib_entries(
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> list[UnassignedVibEntrySchema]:
    return list_unassigned_vib_entries(db)


@router.patch("/unassigned-finves/{finve_id}/assign", response_model=None, status_code=204)
def assign_finve(
    finve_id: int,
    body: AssignProjectsInput,
    db: Session = Depends(get_db),
    current_user: User = _require_editor,
) -> None:
    finve = get_finve(db, finve_id)
    if not finve:
        raise HTTPException(status_code=404, detail="FinVe not found")
    if not body.project_ids:
        raise HTTPException(status_code=422, detail="project_ids must not be empty")
    try:
        assign_finve_to_projects(db, finve_id, body.project_ids, current_user)
    except FinveLinkConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FinveLinkError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/unassigned-vib-entries/{entry_id}/assign", response_model=None, status_code=204)
def assign_vib_entry(
    entry_id: int,
    body: AssignProjectsInput,
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> None:
    entry = get_vib_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="VIB entry not found")
    if not body.project_ids:
        raise HTTPException(status_code=422, detail="project_ids must not be empty")
    assign_vib_entry_to_projects(db, entry_id, body.project_ids)
    db.commit()


@router.get("/unassigned-gvfg-entries", response_model=list[GvfgEntrySchema])
def get_unassigned_gvfg_entries(
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> list[GvfgEntry]:
    """GVFG Vorhaben of the newest edition without a project."""
    return gvfg_crud.unassigned_entries(db)


@router.patch("/unassigned-gvfg-entries/{entry_id}/assign", response_model=None, status_code=204)
def assign_gvfg_entry(
    entry_id: int,
    body: AssignProjectsInput,
    db: Session = Depends(get_db),
    current_user: User = _require_editor,
) -> None:
    entry = db.get(GvfgEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="GVFG entry not found")
    if not body.project_ids:
        raise HTTPException(status_code=422, detail="project_ids must not be empty")
    try:
        gvfg_crud.assign_entry(db, entry, body.project_ids, current_user)
    except gvfg_crud.GvfgConfirmError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/unassigned-infraplan-entries", response_model=list[UnassignedInfraplanEntrySchema])
def get_unassigned_infraplan_entries(
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> list[UnassignedInfraplanEntrySchema]:
    """Infraplan entries of the newest year without a project."""
    return [
        UnassignedInfraplanEntrySchema(
            id=entry.id,
            report_year=year,
            section=entry.section,
            lfd_nr=entry.lfd_nr,
            page=entry.page,
            primary_number=entry.primary_number,
            bezeichnung=entry.bezeichnung,
            massnahme=entry.massnahme,
            laender=entry.laender,
            state_raw=entry.state_raw,
            ibn_raw=entry.ibn_raw,
            cost_mio=float(entry.cost_mio) if entry.cost_mio is not None else None,
        )
        for entry, year in infraplan_crud.unassigned_entries(db)
    ]


@router.patch(
    "/unassigned-infraplan-entries/{entry_id}/assign", response_model=None, status_code=204
)
def assign_infraplan_entry(
    entry_id: int,
    body: AssignProjectsInput,
    db: Session = Depends(get_db),
    current_user: User = _require_editor,
) -> None:
    entry = db.get(InfraplanEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Infraplan entry not found")
    if not body.project_ids:
        raise HTTPException(status_code=422, detail="project_ids must not be empty")
    try:
        infraplan_crud.assign_entry(
            db, entry, body.project_ids, source="MANUAL", username=current_user.username
        )
    except infraplan_crud.InfraplanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
