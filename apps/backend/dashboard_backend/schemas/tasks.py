from typing import Any, Literal

from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # PENDING | STARTED | SUCCESS | FAILURE | REVOKED
    result: Any = None
    error: str | None = None
    # What to do about this status — set while a task waits without a worker and
    # when one failed, so the poller can say more than "es läuft noch".
    hint: str | None = None


class TaskLaunchResponse(BaseModel):
    task_id: str


class DebugTaskRequest(BaseModel):
    x: int
    y: int


class WorkerSchema(BaseModel):
    """One Celery worker that answered the broadcast ping."""

    name: str
    active_tasks: int
    active_task_names: list[str] = []
    concurrency: int | None = None


class WorkerHealthSchema(BaseModel):
    """Broker and workers at one moment — the answer to "läuft da überhaupt was?"."""

    status: Literal["ok", "no_workers", "broker_unreachable"]
    broker_reachable: bool
    # Host only; the credentials of the broker URL are never handed out.
    broker_url: str
    workers: list[WorkerSchema] = []
    # Jobs waiting in the default queue — Redis brokers only, None elsewhere.
    queued_tasks: int | None = None
    # German, and it names the next step rather than only the state.
    message: str
    # Transport/inspection error behind a bad status, for the admin view.
    detail: str | None = None
    checked_at: float
