from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_roles
from dashboard_backend.crud.changelog import (
    create_text_changelog_for_create,
    create_text_changelog_for_delete,
    create_text_changelog_for_patch,
    get_project_text_changelog,
)
from dashboard_backend.crud.projects.projects import get_project_by_id
from dashboard_backend.crud.projects.texts import (
    create_text_for_project,
    create_text_type,
    delete_project_text,
    get_text_types,
    get_texts_for_project,
    update_project_text,
)
from dashboard_backend.database import get_db
from dashboard_backend.models.associations.text_to_project import TextToProject
from dashboard_backend.models.projects.project_text import ProjectText
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.changelog import TextChangeLogRead
from dashboard_backend.schemas.projects.project_text_schema import (
    ProjectTextCreate,
    ProjectTextSchema,
    ProjectTextTypeCreate,
    ProjectTextTypeSchema,
    ProjectTextUpdate,
)
from dashboard_backend.schemas.users import UserRole

router = AuthRouter()


def _get_project_id_for_text(db: Session, text_id: int) -> int | None:
    """Look up the project context for a text via the text_to_project association."""
    assoc = db.query(TextToProject).filter(TextToProject.text_id == text_id).first()
    return assoc.project_id if assoc else None


@router.get("/text_types", response_model=list[ProjectTextTypeSchema], tags=["texts"])
def list_text_types(db: Session = Depends(get_db)):
    """Return all available project text types."""
    return get_text_types(db)


@router.post("/text_types", response_model=ProjectTextTypeSchema, status_code=201, tags=["texts"])
def create_project_text_type(
    body: ProjectTextTypeCreate,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Create a new project text type. Requires editor or admin role."""
    return create_text_type(db, body.name)


@router.get("/projects/{project_id}/texts", response_model=list[ProjectTextSchema], tags=["texts"])
def list_project_texts(project_id: int, db: Session = Depends(get_db)):
    """Return all texts linked to a project."""
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return get_texts_for_project(db, project_id)


@router.get(
    "/projects/{project_id}/texts/changelog",
    response_model=list[TextChangeLogRead],
    tags=["texts"],
)
def get_texts_changelog(
    project_id: int,
    current_user: User = Depends(require_roles(UserRole.viewer, UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Return the text change history for a project. Requires authentication."""
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return get_project_text_changelog(db, project_id)


@router.post(
    "/projects/{project_id}/texts",
    response_model=ProjectTextSchema,
    status_code=201,
    tags=["texts"],
)
def create_project_text(
    project_id: int,
    body: ProjectTextCreate,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Create a new text and link it to a project. Requires editor or admin role."""
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    text = create_text_for_project(db, project_id, body.model_dump())
    # Log CREATE in a second commit (text is already committed by create_text_for_project)
    create_text_changelog_for_create(db, text, project_id, current_user.id, current_user.username)
    db.commit()
    return text


@router.patch("/projects/texts/{text_id}", response_model=ProjectTextSchema, tags=["texts"])
def update_text(
    text_id: int,
    body: ProjectTextUpdate,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Update an existing project text. Requires editor or admin role."""
    text = db.query(ProjectText).filter(ProjectText.id == text_id).first()
    if not text:
        raise HTTPException(status_code=404, detail="Text not found")

    update_data = body.model_dump(exclude_unset=True)
    project_id = _get_project_id_for_text(db, text_id)

    # Add changelog to session before committing — update_project_text commits both together
    create_text_changelog_for_patch(db, text, update_data, project_id, current_user.id, current_user.username)
    return update_project_text(db, text_id, update_data)


@router.delete("/projects/texts/{text_id}", status_code=204, tags=["texts"])
def delete_text(
    text_id: int,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Delete a project text. Requires editor or admin role."""
    text = db.query(ProjectText).filter(ProjectText.id == text_id).first()
    if not text:
        raise HTTPException(status_code=404, detail="Text not found")

    project_id = _get_project_id_for_text(db, text_id)

    # Add changelog to session before deletion — delete_project_text commits both together.
    # The DB SET NULL rule will null out text_change_log.text_id after the text row is removed.
    create_text_changelog_for_delete(db, text, project_id, current_user.id, current_user.username)
    delete_project_text(db, text_id)
