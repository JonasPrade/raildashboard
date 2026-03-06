from fastapi import APIRouter, Depends

from dashboard_backend.celery_app import celery_app
from dashboard_backend.core.security import require_roles
from dashboard_backend.schemas.tasks import DebugTaskRequest, TaskLaunchResponse, TaskStatusResponse
from dashboard_backend.tasks.debug import add

router = APIRouter()

_require_login = Depends(require_roles())


@router.get("/{task_id}", response_model=TaskStatusResponse, dependencies=[_require_login])
def get_task_status(task_id: str):
    """Return the current status and result of a Celery task."""
    result = celery_app.AsyncResult(task_id)

    error = None
    if result.status == "FAILURE":
        error = str(result.result)

    return TaskStatusResponse(
        task_id=task_id,
        status=result.status,
        result=result.result if result.status == "SUCCESS" else None,
        error=error,
    )


@router.post("/debug", response_model=TaskLaunchResponse, dependencies=[_require_login])
def start_debug_task(payload: DebugTaskRequest):
    """Start the debug add-task and return its task_id for polling."""
    result = add.delay(payload.x, payload.y)
    return TaskLaunchResponse(task_id=result.id)
