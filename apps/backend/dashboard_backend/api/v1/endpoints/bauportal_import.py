"""DB-Bauportal importer endpoints (#47).

Mounted under ``/import/bauportal``. All actions require ``progress.edit``:
fetching queues the Celery task ``refresh_bauportal`` (the same one the nightly
scheduler runs, feature-routine-abrufe.md) and answers ``202`` with its task
id, or ``409`` while a run is going; the entry list
backs the review UI, and confirming a match links a Bauportal record to one of
our projects (which materialises a derived BAUPORTAL observation).
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_permission
from dashboard_backend.crud import bauportal as bauportal_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.routine_job_run import JOB_BAUPORTAL
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.bauportal import (
    BauportalConfirmSummary,
    BauportalEntrySchema,
    BauportalUpdateInput,
)
from dashboard_backend.schemas.tasks import TaskLaunchResponse
from dashboard_backend.services import job_lock, routine_jobs

router = AuthRouter()

_require_edit = Depends(require_permission("progress.edit"))


@router.post(
    "/fetch",
    response_model=TaskLaunchResponse,
    status_code=202,
    responses={409: {"description": "Ein Bauportal-Abruf läuft bereits."}},
)
def fetch_bauportal(current_user: User = Depends(require_permission("progress.edit"))):
    """Queue a fetch of the public Bauportal project list (Celery).

    The task result is a ``BauportalImportSummary``; poll it via
    ``GET /tasks/{task_id}``.
    """
    try:
        task_id = routine_jobs.launch(JOB_BAUPORTAL, user_id=current_user.id)
    except job_lock.JobAlreadyRunning as exc:
        raise HTTPException(
            status_code=409, detail=routine_jobs.already_running_detail(exc)
        ) from exc
    return TaskLaunchResponse(task_id=task_id)


@router.get("/entries", response_model=list[BauportalEntrySchema], dependencies=[_require_edit])
def list_bauportal_entries(
    only_unconfirmed: bool = Query(False),
    db: Session = Depends(get_db),
):
    """List fetched Bauportal entries with suggested / confirmed matches."""
    return bauportal_crud.list_entries(db, only_unconfirmed=only_unconfirmed)


@router.post(
    "/confirm-all",
    response_model=BauportalConfirmSummary,
    dependencies=[_require_edit],
)
def confirm_all_bauportal(db: Session = Depends(get_db)):
    """Confirm all assigned, still-open entries in one step."""
    return {"confirmed": bauportal_crud.confirm_all(db)}


@router.patch("/entries/{entry_id}", response_model=BauportalEntrySchema, dependencies=[_require_edit])
def update_bauportal_entry(
    entry_id: int,
    body: BauportalUpdateInput,
    db: Session = Depends(get_db),
):
    """Set the assigned project and/or confirm the match for one entry."""
    try:
        entry = bauportal_crud.update_entry(db, entry_id, body.model_dump(exclude_unset=True))
    except bauportal_crud.ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if entry is None:
        raise HTTPException(status_code=404, detail="Bauportal-Eintrag nicht gefunden")
    return entry
