from typing import Any
from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # PENDING | STARTED | SUCCESS | FAILURE | REVOKED
    result: Any = None
    error: str | None = None


class TaskLaunchResponse(BaseModel):
    task_id: str


class DebugTaskRequest(BaseModel):
    x: int
    y: int
