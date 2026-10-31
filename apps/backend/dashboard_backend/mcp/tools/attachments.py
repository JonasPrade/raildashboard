"""Read the content of attachments to project texts (read-only).

``get_project_texts`` lists the attachments (id, filename, type, size); these
tools open one: PDF and Word text, or a PDF page / image file as image — e.g. a
Planfeststellungsbeschluss attached to a project. Uploading and deleting stay
in the UI.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver.utilities.types import Image
from sqlalchemy.orm import Session

from dashboard_backend.mcp.context import get_principal, tool_session
from dashboard_backend.mcp.tools.projects import READ_ONLY, _project_or_error
from dashboard_backend.models.associations.text_to_project import TextToProject
from dashboard_backend.models.projects.text_attachment import TextAttachment
from dashboard_backend.services.attachment_content import (
    DOCX,
    IMAGES,
    PDF,
    AttachmentContentError,
    docx_text,
    pdf_page_png,
    pdf_text,
)
from dashboard_backend.utils.file_storage import get_attachment_path


def _load(db: Session, project_id: int, text_id: int, attachment_id: int) -> tuple[TextAttachment, bytes]:
    _project_or_error(db, project_id)
    linked = (
        db.query(TextToProject)
        .filter(TextToProject.text_id == text_id, TextToProject.project_id == project_id)
        .first()
    )
    attachment = db.get(TextAttachment, attachment_id)
    if linked is None or attachment is None or attachment.text_id != text_id:
        raise ToolError(
            f"Anhang {attachment_id} gehört nicht zu Text {text_id} von Projekt {project_id} "
            "(siehe get_project_texts)."
        )
    try:
        path = get_attachment_path(text_id, attachment.stored_filename)
        data = path.read_bytes()
    except (OSError, ValueError) as exc:
        raise ToolError(f"Die Datei zu Anhang {attachment_id} fehlt auf dem Server.") from exc
    return attachment, data


def _meta(attachment: TextAttachment) -> dict[str, Any]:
    return {
        "attachment_id": attachment.id,
        "text_id": attachment.text_id,
        "filename": attachment.filename,
        "mime_type": attachment.mime_type,
        "file_size": attachment.file_size,
    }


def read_text_attachment(
    project_id: int,
    text_id: int,
    attachment_id: int,
    page: int = 1,
    pages: int = 3,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Text content of an attachment to a project text (ids from
    get_project_texts → ``attachments``).
    - PDF: ``pages`` pages from ``page`` (at most 10 per call), with
      ``page_count`` and ``next_page`` to read on; a page without text is
      probably a scan — read it with get_text_attachment_image.
    - Word (.docx): the whole text (paragraphs, table rows as "a | b").
    - Images: no text — use get_text_attachment_image.
    - Other formats (.doc, .xls, .xlsx): not readable here; open them in the UI.
    Long texts are cut after 40,000 characters (``truncated``)."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        attachment, data = _load(db, project_id, text_id, attachment_id)
        meta = _meta(attachment)
    try:
        if attachment.mime_type == PDF:
            result = pdf_text(data, page, pages)
        elif attachment.mime_type == DOCX:
            result = docx_text(data)
        elif attachment.mime_type in IMAGES:
            raise ToolError("Ein Bild hat keinen Text — mit get_text_attachment_image ansehen.")
        else:
            raise ToolError(
                f"Dateien vom Typ {attachment.mime_type} lassen sich hier nicht lesen; "
                "bitte in der Oberfläche öffnen."
            )
    except AttachmentContentError as exc:
        raise ToolError(str(exc)) from exc
    out = {**meta, "text": result.text, "truncated": result.truncated}
    if result.page_count is not None:
        out["page_count"] = result.page_count
        out["pages"] = [result.first_page, result.last_page]
        out["next_page"] = result.last_page + 1 if result.last_page < result.page_count else None
    if result.empty_pages:
        out["empty_pages"] = list(result.empty_pages)
        out["note"] = "Seiten ohne Text — vermutlich gescannt; mit get_text_attachment_image lesen."
    return out


def get_text_attachment_image(
    project_id: int,
    text_id: int,
    attachment_id: int,
    page: int = 1,
    dpi: int = 110,
    *,
    ctx: Context,
) -> Image:
    """An attachment as image: one PDF page (``page``, dpi 50–200 — raise it
    when text is hard to read) or a PNG/JPEG file as it is. For scans without
    a text layer, plans and maps. Text PDFs are cheaper with
    read_text_attachment."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        attachment, data = _load(db, project_id, text_id, attachment_id)
    if attachment.mime_type in IMAGES:
        return Image(data=data, format=IMAGES[attachment.mime_type])
    if attachment.mime_type != PDF:
        raise ToolError(f"Dateien vom Typ {attachment.mime_type} lassen sich nicht als Bild zeigen.")
    try:
        return Image(data=pdf_page_png(data, page, dpi), format="png")
    except AttachmentContentError as exc:
        raise ToolError(str(exc)) from exc


def register(server: MCPServer) -> None:
    server.add_tool(read_text_attachment, annotations=READ_ONLY)
    server.add_tool(get_text_attachment_image, annotations=READ_ONLY)

