from __future__ import annotations

import urllib.parse

from fastapi import Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from dashboard_backend.api.deps import (
    TEXT_NOT_FOUND,
    get_project_or_404,
    get_text_or_404,
    read_upload_within_limit,
)
from dashboard_backend.core.security import optional_auth, require_auth, require_permission
from dashboard_backend.crud.changelog import (
    create_text_changelog_for_create,
    create_text_changelog_for_delete,
    create_text_changelog_for_patch,
    get_project_text_changelog,
)
from dashboard_backend.crud.projects.text_attachments import (
    create_text_attachment,
    delete_text_attachment,
    get_text_attachment,
    get_text_attachments,
)
from dashboard_backend.crud.projects.texts import (
    create_text_category,
    create_text_for_project,
    create_text_type,
    delete_project_text,
    get_text_categories,
    get_text_category,
    get_text_category_by_name,
    get_text_types,
    get_texts_for_project,
    update_project_text,
)
from dashboard_backend.database import get_db
from dashboard_backend.models.associations.text_to_project import TextToProject
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_text import ProjectText
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.changelog import TextChangeLogRead
from dashboard_backend.schemas.projects.project_text_schema import (
    ProjectTextCategoryCreate,
    ProjectTextCategorySchema,
    ProjectTextCreate,
    ProjectTextSchema,
    ProjectTextTypeCreate,
    ProjectTextTypeSchema,
    ProjectTextUpdate,
    TextAttachmentSchema,
)
from dashboard_backend.utils.file_storage import (
    delete_attachment_file,
    get_attachment_path,
    save_attachment,
    validate_mime,
)

router = AuthRouter()


def _get_project_id_for_text(db: Session, text_id: int) -> int | None:
    """Look up the project context for a text via the text_to_project association."""
    assoc = db.query(TextToProject).filter(TextToProject.text_id == text_id).first()
    return assoc.project_id if assoc else None


# ---------------------------------------------------------------------------
# Text types
# ---------------------------------------------------------------------------

@router.get("/text_types", response_model=list[ProjectTextTypeSchema], tags=["texts"])
def list_text_types(db: Session = Depends(get_db)):
    """Return all available project text types."""
    return get_text_types(db)


@router.post("/text_types", response_model=ProjectTextTypeSchema, status_code=201, tags=["texts"])
def create_project_text_type(
    body: ProjectTextTypeCreate,
    current_user: User = Depends(require_permission("projecttext.edit")),
    db: Session = Depends(get_db),
):
    """Create a new project text type. Requires editor or admin role."""
    return create_text_type(db, body.name)


# ---------------------------------------------------------------------------
# Text categories
# ---------------------------------------------------------------------------

@router.get("/text_categories", response_model=list[ProjectTextCategorySchema], tags=["texts"])
def list_text_categories(db: Session = Depends(get_db)):
    """Return all text categories (e.g. Info, Warnung) with their display style."""
    return get_text_categories(db)


@router.post(
    "/text_categories",
    response_model=ProjectTextCategorySchema,
    status_code=201,
    tags=["texts"],
)
def create_project_text_category(
    body: ProjectTextCategoryCreate,
    current_user: User = Depends(require_permission("projecttext.edit")),
    db: Session = Depends(get_db),
):
    """Create a new text category. Requires editor or admin role."""
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="Der Name darf nicht leer sein.")
    if get_text_category_by_name(db, body.name) is not None:
        raise HTTPException(status_code=409, detail="Diese Kategorie gibt es schon.")
    return create_text_category(db, body.name, body.style)


def _check_category(db: Session, data: dict) -> None:
    if "category_id" not in data:
        return
    category_id = data["category_id"]
    if category_id is None or get_text_category(db, category_id) is None:
        raise HTTPException(status_code=422, detail=f"Kategorie {category_id} existiert nicht.")


def _ensure_visible(text: ProjectText, user: User | None, detail: str = TEXT_NOT_FOUND) -> None:
    """Internal texts and their attachments do not exist for anonymous visitors."""
    if not text.is_public and user is None:
        raise HTTPException(status_code=404, detail=detail)


# ---------------------------------------------------------------------------
# Texts
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/texts", response_model=list[ProjectTextSchema], tags=["texts"])
def list_project_texts(
    project: Project = Depends(get_project_or_404),
    current_user: User | None = Depends(optional_auth()),
    db: Session = Depends(get_db),
):
    """Return the texts linked to a project. Internal texts only for signed-in users."""
    return get_texts_for_project(db, project.id, include_internal=current_user is not None)


@router.get(
    "/projects/{project_id}/texts/changelog",
    response_model=list[TextChangeLogRead],
    tags=["texts"],
)
def get_texts_changelog(
    current_user: User = Depends(require_auth()),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Return the text change history for a project. Requires authentication."""
    return get_project_text_changelog(db, project.id)


@router.post(
    "/projects/{project_id}/texts",
    response_model=ProjectTextSchema,
    status_code=201,
    tags=["texts"],
)
def create_project_text(
    body: ProjectTextCreate,
    current_user: User = Depends(require_permission("projecttext.edit")),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Create a new text and link it to a project. Requires editor or admin role.
    Without ``category_id`` the text gets the default category („Info“)."""
    data = body.model_dump()
    if data["category_id"] is not None:
        _check_category(db, data)
    text = create_text_for_project(db, project.id, data)
    # Log CREATE in a second commit (text is already committed by create_text_for_project)
    create_text_changelog_for_create(db, text, project.id, current_user.id, current_user.username)
    db.commit()
    return text


@router.patch("/projects/texts/{text_id}", response_model=ProjectTextSchema, tags=["texts"])
def update_text(
    body: ProjectTextUpdate,
    current_user: User = Depends(require_permission("projecttext.edit")),
    text: ProjectText = Depends(get_text_or_404),
    db: Session = Depends(get_db),
):
    """Update an existing project text. Requires editor or admin role."""
    update_data = body.model_dump(exclude_unset=True)
    _check_category(db, update_data)
    if update_data.get("is_public", True) is None:
        raise HTTPException(status_code=422, detail="is_public darf nicht leer sein.")
    project_id = _get_project_id_for_text(db, text.id)

    # Add changelog to session before committing — update_project_text commits both together
    create_text_changelog_for_patch(db, text, update_data, project_id, current_user.id, current_user.username)
    return update_project_text(db, text.id, update_data)


@router.delete("/projects/texts/{text_id}", status_code=204, tags=["texts"])
def delete_text(
    current_user: User = Depends(require_permission("projecttext.edit")),
    text: ProjectText = Depends(get_text_or_404),
    db: Session = Depends(get_db),
):
    """Delete a project text. Requires editor or admin role."""
    project_id = _get_project_id_for_text(db, text.id)

    # Add changelog to session before deletion — delete_project_text commits both together.
    # The DB SET NULL rule will null out text_change_log.text_id after the text row is removed.
    create_text_changelog_for_delete(db, text, project_id, current_user.id, current_user.username)
    delete_project_text(db, text.id)


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

@router.post(
    "/projects/texts/{text_id}/attachments",
    response_model=TextAttachmentSchema,
    status_code=201,
    tags=["texts"],
)
async def upload_attachment(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("projecttext.edit")),
    text: ProjectText = Depends(get_text_or_404),
    db: Session = Depends(get_db),
):
    """Upload a file attachment to a project text. Requires editor or admin role.

    Accepted types: PDF, Word (.doc/.docx), Excel (.xls/.xlsx), JPEG, PNG.
    Maximum file size: 50 MB.
    """
    text_id = text.id

    # Read and enforce size limit
    file_bytes = await read_upload_within_limit(file)

    # Validate MIME via byte sniffing (not the attacker-controlled Content-Type header)
    try:
        detected_mime = validate_mime(file_bytes, file.content_type or "")
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    original_filename = file.filename or "upload"

    # Persist DB row first so foreign-key integrity is guaranteed before we
    # touch the filesystem. The file is written afterwards.
    attachment = create_text_attachment(
        db,
        text_id=text_id,
        filename=original_filename,
        stored_filename="",  # placeholder — updated below
        mime_type=detected_mime,
        file_size=len(file_bytes),
        user_id=current_user.id,
    )

    # Write file — on any error, roll back the DB row
    stored_filename = ""
    try:
        stored_filename, _ = save_attachment(text_id, file_bytes, detected_mime)
        attachment.stored_filename = stored_filename
        db.commit()
        db.refresh(attachment)
    except Exception as exc:
        # Remove the DB row (file may or may not exist yet)
        db.delete(attachment)
        db.commit()
        if stored_filename:
            delete_attachment_file(text_id, stored_filename)
        raise HTTPException(status_code=500, detail="Datei konnte nicht gespeichert werden.") from exc

    return attachment


@router.get(
    "/projects/texts/{text_id}/attachments",
    response_model=list[TextAttachmentSchema],
    tags=["texts"],
)
def list_attachments(
    text: ProjectText = Depends(get_text_or_404),
    current_user: User | None = Depends(optional_auth()),
    db: Session = Depends(get_db),
):
    """List all attachments for a project text (internal texts: signed-in users only)."""
    _ensure_visible(text, current_user)
    return get_text_attachments(db, text.id)


@router.delete(
    "/projects/texts/{text_id}/attachments/{attachment_id}",
    status_code=204,
    tags=["texts"],
)
def remove_attachment(
    text_id: int,
    attachment_id: int,
    current_user: User = Depends(require_permission("projecttext.edit")),
    db: Session = Depends(get_db),
):
    """Delete an attachment. Requires editor or admin role."""
    attachment = get_text_attachment(db, attachment_id)
    if not attachment or attachment.text_id != text_id:
        raise HTTPException(status_code=404, detail="Anhang nicht gefunden")

    stored = attachment.stored_filename
    delete_text_attachment(db, attachment_id)
    delete_attachment_file(text_id, stored)


@router.get(
    "/projects/texts/{text_id}/attachments/{attachment_id}/download",
    tags=["texts"],
)
def download_attachment(
    text_id: int,
    attachment_id: int,
    inline: bool = Query(default=False),
    current_user: User | None = Depends(optional_auth()),
    db: Session = Depends(get_db),
):
    """Stream an attachment file.

    Security:
    - Content-Type is set from the DB-stored mime_type (never re-detected).
    - Content-Disposition forces download by default (prevents stored XSS via HTML/SVG).
    - Pass ?inline=true to serve PDFs inline (for in-browser preview); ignored for other types.
    - Filename is RFC 5987-encoded to prevent header injection.
    - X-Content-Type-Options: nosniff is set.
    - Attachments of internal texts are only served to signed-in users.
    """
    attachment = get_text_attachment(db, attachment_id)
    if not attachment or attachment.text_id != text_id:
        raise HTTPException(status_code=404, detail="Anhang nicht gefunden")
    _ensure_visible(attachment.text, current_user, "Anhang nicht gefunden")

    file_path = get_attachment_path(text_id, attachment.stored_filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")

    # RFC 5987 percent-encode the filename for Content-Disposition
    encoded_filename = urllib.parse.quote(attachment.filename, safe="")
    # Only serve inline for PDFs — other types always force download
    disposition_type = "inline" if (inline and attachment.mime_type == "application/pdf") else "attachment"
    content_disposition = f"{disposition_type}; filename*=UTF-8''{encoded_filename}"

    return FileResponse(
        path=str(file_path),
        media_type=attachment.mime_type,
        headers={
            "Content-Disposition": content_disposition,
            "X-Content-Type-Options": "nosniff",
        },
    )
