"""Project planning-state (Planungsstand) endpoints.

Mounted under ``/projects`` so paths read ``/projects/{id}/progress``. GET is
public (like BVWP data); all mutations require the ``progress.edit`` capability.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from dashboard_backend.api.deps import get_project_or_404
from dashboard_backend.core.security import require_permission
from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.projects.progress_schema import (
    LinkDocumentInput,
    ProgressObservationCreate,
    ProjectProgressSchema,
    ProjectProgressUpdate,
)

router = AuthRouter()

_DOCUMENT_TRACKS = {"PF", "PARL"}


def _view(db: Session, project_id: int) -> dict:
    """Build the progress view. The project's existence is guaranteed by
    :func:`get_project_or_404`, so ``get_progress_view`` cannot return None."""
    return progress_crud.get_progress_view(db, project_id)


@router.get("/{project_id}/progress", response_model=ProjectProgressSchema)
def read_progress(
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Public: derived planning state for a project (lazy-recomputed)."""
    return _view(db, project.id)


@router.patch("/{project_id}/progress", response_model=ProjectProgressSchema)
def patch_progress(
    body: ProjectProgressUpdate,
    current_user: User = Depends(require_permission("progress.edit")),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Update flags, lifecycle and manual overrides."""
    progress_crud.update_progress(db, project.id, body.model_dump(exclude_unset=True))
    return _view(db, project.id)


@router.post(
    "/{project_id}/progress/observations",
    response_model=ProjectProgressSchema,
    status_code=201,
)
def add_observation(
    body: ProgressObservationCreate,
    current_user: User = Depends(require_permission("progress.edit")),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Add a manual observation (always ``is_derived=False``)."""
    progress_crud.create_observation(
        db, project.id, body.model_dump(exclude_unset=True), current_user
    )
    return _view(db, project.id)


@router.delete(
    "/{project_id}/progress/observations/{observation_id}",
    response_model=ProjectProgressSchema,
)
def remove_observation(
    observation_id: int,
    current_user: User = Depends(require_permission("progress.edit")),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Delete a manual observation. Derived observations are protected (409)."""
    try:
        result = progress_crud.delete_observation(db, project.id, observation_id)
    except progress_crud.DerivedObservationDeleteError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Observation not found")
    return _view(db, project.id)


@router.post(
    "/{project_id}/progress/tracks/{track}/documents",
    response_model=ProjectProgressSchema,
    status_code=201,
)
def link_document(
    track: str,
    body: LinkDocumentInput,
    current_user: User = Depends(require_permission("progress.edit")),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Link a document behind the PF / parliamentary track."""
    track = track.upper()
    if track not in _DOCUMENT_TRACKS:
        raise HTTPException(status_code=400, detail="Documents may only be linked to PF or PARL")
    link = progress_crud.link_track_document(db, project.id, track, body.document_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Project or document not found")
    return _view(db, project.id)


@router.delete(
    "/{project_id}/progress/tracks/{track}/documents/{document_id}",
    response_model=ProjectProgressSchema,
)
def unlink_document(
    track: str,
    document_id: int,
    current_user: User = Depends(require_permission("progress.edit")),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Remove a document link from the PF / parliamentary track."""
    track = track.upper()
    if track not in _DOCUMENT_TRACKS:
        raise HTTPException(status_code=400, detail="Documents may only be linked to PF or PARL")
    removed = progress_crud.unlink_track_document(db, project.id, track, document_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Document link not found")
    return _view(db, project.id)


@router.post("/{project_id}/progress/recompute", response_model=ProjectProgressSchema)
def recompute(
    current_user: User = Depends(require_permission("progress.edit")),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Force a recomputation of the cached headline."""
    progress_crud.recompute_progress(db, project.id)
    return _view(db, project.id)
