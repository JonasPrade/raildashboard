"""Planning-state maintenance beyond observations: documents behind the PF /
parliamentary track, forced recomputation and the set-back conflicts across
all projects. Same right as the REST endpoints: ``progress.edit``.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.mcp.tools.projects import MAX_LIMIT, READ_ONLY, WRITE, _project_or_error
from dashboard_backend.models.projects.document import Document
from dashboard_backend.models.associations.progress_track_document import ProgressTrackDocument
from dashboard_backend.schemas.projects.progress_schema import (
    ProgressConflictRowSchema,
    ProjectProgressSchema,
)

PERMISSION = "progress.edit"
DocumentTrackLiteral = Literal["PF", "PARL"]


def _progress(db, project_id: int) -> dict[str, Any]:
    view = progress_crud.get_progress_view(db, project_id)
    return ProjectProgressSchema.model_validate(view).model_dump(mode="json")


def list_project_documents(project_id: int, *, ctx: Context) -> dict[str, Any]:
    """Documents of a project (title, date, source, public) and the tracks each
    is linked to as evidence: PF (Planfeststellung) or PARL (parliamentary
    involvement). Link or unlink with set_track_document; the linked documents
    also appear in get_project_progress (``pf_documents``, ``parl_documents``)."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        links = (
            db.query(ProgressTrackDocument)
            .filter(ProgressTrackDocument.project_id == project.id)
            .all()
        )
        tracks: dict[int, list[str]] = {}
        for link in links:
            tracks.setdefault(link.document_id, []).append(link.track)
        documents = {doc.id: doc for doc in project.documents}
        missing = set(tracks) - set(documents)
        if missing:
            # Linked to a track without belonging to the project's documents.
            for doc in db.query(Document).filter(Document.id.in_(missing)).all():
                documents[doc.id] = doc
        return {
            "project_id": project.id,
            "documents": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "date": doc.date.isoformat() if doc.date else None,
                    "source": doc.source,
                    "is_public": bool(doc.is_public),
                    "tracks": sorted(tracks.get(doc.id, [])),
                }
                for doc in sorted(documents.values(), key=lambda d: (d.title or "", d.id))
            ],
        }


def set_track_document(
    project_id: int,
    track: DocumentTrackLiteral,
    document_id: int,
    linked: bool = True,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Link a document as evidence behind the PF (Planfeststellung) or PARL
    (parliamentary involvement) track of a project, or unlink it with
    linked=false (requires ``progress.edit``). Document ids: list_project_documents.
    Linking twice is harmless. Written to the project changelog. Returns the
    planning state afterwards."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        user = load_user(db, principal)
        if linked:
            link = progress_crud.link_track_document(db, project_id, track, document_id, user)
            if link is None:
                raise ToolError(f"Dokument {document_id} nicht gefunden.")
        elif not progress_crud.unlink_track_document(db, project_id, track, document_id, user):
            raise ToolError(
                f"Dokument {document_id} ist nicht mit dem Strang {track} verknüpft."
            )
        return _progress(db, project_id)


def recompute_project_progress(project_id: int, *, ctx: Context) -> dict[str, Any]:
    """Recompute a project's planning state now (requires ``progress.edit``):
    re-derives the observations from the imports and refreshes the cached
    headline, forecast and list values. Writing tools already do this; use it
    when a value in list_projects looks stale. Returns the planning state."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        progress_crud.recompute_progress(db, project_id)
        return _progress(db, project_id)


def list_progress_conflicts(limit: int = 50, offset: int = 0, *, ctx: Context) -> dict[str, Any]:
    """Projects whose planning state has a set-back conflict (requires
    ``progress.edit``): a newer report states a lower phase than older
    information. Per project the computed phase, the conflict (``applied``
    false = the newer report is held back, the headline ignores it) and the
    contradicted observations. Held-back reports come first. Resolve by
    checking the sources: correct or delete a wrong manual observation, fix an
    import assignment, or set a manual phase override (set_phase_override).
    Superior and archived projects are not listed. Paged with limit/offset."""
    require(get_principal(ctx), PERMISSION)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    with tool_session(ctx) as db:
        rows = progress_crud.list_progress_conflicts(db)
        return {
            "total": len(rows),
            "offset": offset,
            "conflicts": [
                ProgressConflictRowSchema.model_validate(row).model_dump(mode="json")
                for row in rows[offset : offset + limit]
            ],
        }


def register(server: MCPServer) -> None:
    server.add_tool(list_project_documents, annotations=READ_ONLY)
    server.add_tool(list_progress_conflicts, annotations=READ_ONLY)
    server.add_tool(set_track_document, annotations=WRITE)
    server.add_tool(recompute_project_progress, annotations=WRITE)
