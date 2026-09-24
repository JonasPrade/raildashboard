"""Status of the background (Celery) jobs the import pages start.

``PENDING`` is Celery's answer both for "queued, will start in a moment" and for
"nobody is there to run this" — the second is the one that leaves an import
spinning forever.  The status endpoint therefore looks at the workers whenever a
job is still pending and returns a ``hint`` saying which of the two it is; the
``/workers`` endpoint behind it is the same check on demand for the admin area.
"""

import re

from fastapi import APIRouter, Depends

from dashboard_backend.celery_app import celery_app
from dashboard_backend.core.security import require_auth, require_permission
from dashboard_backend.schemas.tasks import (
    DebugTaskRequest,
    TaskLaunchResponse,
    TaskStatusResponse,
    WorkerHealthSchema,
)
from dashboard_backend.services.worker_health import (
    cached_worker_health,
    reset_cache,
    worker_health,
)
from dashboard_backend.tasks.debug import add

router = APIRouter()

_require_login = Depends(require_auth())

# 'File "/app/dashboard_backend/tasks/haushalt.py", line 912, in _extract_pages'
_TRACEBACK_FRAME_RE = re.compile(r'File "([^"]+)", line (\d+), in (\S+)')

# The closing line of a traceback: 'sqlalchemy.exc.OperationalError: no such …'
_EXCEPTION_LINE_RE = re.compile(r"^(\w[\w.]*(?:Error|Exception|Exit|Interrupt|Warning)):\s*(.+)$")

# Our own code, as opposed to the library frame an exception is finally raised
# in — "haushalt.py:912" is a lead, "sqlalchemy/engine/default.py:952" is not.
_OWN_CODE_MARKER = "dashboard_backend"


def _exception_line(traceback: str | None, exc) -> str:
    """"OperationalError: no such function" — the exception as the worker saw it.

    With the JSON result serializer Celery cannot rebuild the original class and
    hands back a plain ``Exception`` whose text is the repr of the real one; the
    closing line of the worker's traceback still carries the true name, so it
    wins whenever it is there. The module path is dropped — the class name is
    what a reader searches for.
    """
    for line in reversed((traceback or "").strip().splitlines()):
        match = _EXCEPTION_LINE_RE.match(line.strip())
        if match:
            name, message = match.group(1).split(".")[-1], match.group(2)
            return f"{name}: {message}"
    if exc is None:
        return "Unbekannter Fehler"
    return f"{type(exc).__name__}: {exc}"


def _failure_location(traceback: str | None) -> str:
    """The deepest frame of our own code — where the search starts."""
    frames = _TRACEBACK_FRAME_RE.findall(traceback or "")
    if not frames:
        return ""
    own = [frame for frame in frames if _OWN_CODE_MARKER in frame[0]]
    path, line, func = (own or frames)[-1]
    return f"Aufgetreten in {path.split('/')[-1]}:{line} ({func}). "


def _describe_failure(result) -> tuple[str, str | None]:
    """The exception and where it was raised — enough to start looking.

    The class name alone ("KeyError") says nothing without the value, and the
    value alone says nothing without the place, so a failed import reports both
    instead of "Unbekannter Fehler".
    """
    error = _exception_line(result.traceback, result.result)
    return error[:500], (
        f"{_failure_location(result.traceback)}Vollständiger Traceback im Worker-Log: "
        "`docker compose logs --tail=100 worker`."
    )


def _pending_hint() -> str | None:
    """Why a job has not started yet — the worker state decides the wording."""
    health = cached_worker_health()
    if health.status == "ok":
        return None
    return health.message


@router.get("/workers", response_model=WorkerHealthSchema)
def get_worker_health(
    refresh: bool = False,
    _user=Depends(require_permission("settings.manage")),
):
    """Broker and Celery workers right now — the admin area's health check.

    ``refresh=true`` bypasses the short-lived cache the status polling shares,
    so the "Erneut prüfen" button really re-probes.
    """
    if refresh:
        reset_cache()
        return worker_health()
    return cached_worker_health()


@router.get("/{task_id}", response_model=TaskStatusResponse, dependencies=[_require_login])
def get_task_status(task_id: str):
    """Return the current status and result of a Celery task."""
    result = celery_app.AsyncResult(task_id)

    error = None
    hint = None
    if result.status == "FAILURE":
        error, hint = _describe_failure(result)
    elif result.status == "PENDING":
        hint = _pending_hint()

    return TaskStatusResponse(
        task_id=task_id,
        status=result.status,
        result=result.result if result.status in ("SUCCESS", "PROGRESS") else None,
        error=error,
        hint=hint,
    )


@router.post("/debug", response_model=TaskLaunchResponse, dependencies=[_require_login])
def start_debug_task(payload: DebugTaskRequest):
    """Start the debug add-task and return its task_id for polling."""
    result = add.delay(payload.x, payload.y)
    return TaskLaunchResponse(task_id=result.id)
