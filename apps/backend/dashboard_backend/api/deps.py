"""Shared FastAPI endpoint dependencies (fetch-or-404, upload limits).

Endpoints declare e.g. ``project: Project = Depends(get_project_or_404)``
instead of repeating the fetch → ``if not`` → ``HTTPException(404)`` block.
The detail texts below are the single source of truth for the "not found"
messages of these resources, and the dependencies are the central hook for
future visibility rules. ``read_upload_within_limit`` is the same idea for
the file uploads: one place that decides how large a request body may get.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from dashboard_backend.crud.projects.projects import get_project_by_id
from dashboard_backend.crud.vib import get_draft_by_task_id
from dashboard_backend.database import get_db
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_text import ProjectText
from dashboard_backend.models.vib.vib_draft_report import VibDraftReport
from dashboard_backend.utils.file_storage import MAX_FILE_SIZE

PROJECT_NOT_FOUND = "Project not found"
TEXT_NOT_FOUND = "Text not found"
DRAFT_NOT_FOUND = "Entwurf nicht gefunden"
UPLOAD_TOO_LARGE = f"Datei zu groß. Maximal {MAX_FILE_SIZE // (1024 * 1024)} MB erlaubt."


def get_project_or_404(project_id: int, db: Session = Depends(get_db)) -> Project:
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=PROJECT_NOT_FOUND)
    return project


def get_text_or_404(text_id: int, db: Session = Depends(get_db)) -> ProjectText:
    text = db.query(ProjectText).filter(ProjectText.id == text_id).first()
    if text is None:
        raise HTTPException(status_code=404, detail=TEXT_NOT_FOUND)
    return text


def _draft_or_404(db: Session, task_id: str) -> VibDraftReport:
    draft = get_draft_by_task_id(db, task_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=DRAFT_NOT_FOUND)
    return draft


def get_draft_or_404(task_id: str, db: Session = Depends(get_db)) -> VibDraftReport:
    """Fetch-or-404 for VIB drafts on routes with a ``{task_id}`` path param."""
    return _draft_or_404(db, task_id)


def get_parse_draft_or_404(parse_task_id: str, db: Session = Depends(get_db)) -> VibDraftReport:
    """Same as :func:`get_draft_or_404` for routes named ``{parse_task_id}``."""
    return _draft_or_404(db, parse_task_id)


async def read_upload_within_limit(file: UploadFile) -> bytes:
    """Read an upload completely and reject anything above MAX_FILE_SIZE with 413.

    Every PDF importer reads its upload into memory before handing it on, so the
    ceiling lives here instead of being repeated per endpoint. The nginx in front
    of the app carries the same 50 MB limit (``apps/frontend/nginx.conf``), as
    must the TLS proxy on the server — see docs/production_setup.md. This check
    is the backstop for requests that reach the backend directly.
    """
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=UPLOAD_TOO_LARGE)
    return file_bytes
