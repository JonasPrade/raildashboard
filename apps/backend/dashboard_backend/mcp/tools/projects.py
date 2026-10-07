"""Project, planning-state, financing and text tools.

Outputs stay compact on purpose: every answer lands in the client's context
window, so lists are paginated and geometries (``geojson_representation``,
``centroid``) are never returned.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import ValidationError
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from dashboard_backend.crud.changelog import (
    create_changelog_for_patch,
    create_text_changelog_for_create,
    create_text_changelog_for_patch,
)
from dashboard_backend.crud.finves import get_project_finves_with_budgets
from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.crud.projects.bvwp import get_bvwp_data
from dashboard_backend.crud.projects.projects import (
    ProjectHierarchyError,
    get_project_by_id,
    get_subprojects,
    update_project as update_project_crud,
    validate_superior_project,
)
from dashboard_backend.crud.projects.texts import (
    create_text_for_project,
    get_text_types,
    get_texts_for_project,
    update_project_text,
)
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.models.associations.text_to_project import TextToProject
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.projects.project_text import ProjectText
from dashboard_backend.schemas.projects import ProjectSchema
from dashboard_backend.schemas.projects.bvwp_schema import BvwpProjectDataSchema
from dashboard_backend.schemas.projects.progress_schema import (
    MainPhaseLiteral,
    ProgressObservationCreate,
    ProjectProgressSchema,
    SourceTypeLiteral,
    TrackLiteral,
)
from dashboard_backend.schemas.projects.project_text_schema import ProjectTextSchema
from dashboard_backend.schemas.projects.project_update_schema import ProjectUpdate

MAX_LIMIT = 200

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)

# Never sent to the client: geometry blobs are huge and useless as text.
_GEOMETRY_FIELDS = {"geojson_representation", "centroid"}
# Fields update_project may not touch: geometry (no meaningful text edit) and the
# draft flag (finalizing is a separate workflow in the UI).
_READONLY_UPDATE_FIELDS = {"geojson_representation", "is_draft"}


def _project_or_error(db: Session, project_id: int) -> Project:
    project = get_project_by_id(db, project_id)
    if project is None:
        raise ToolError(f"Projekt {project_id} nicht gefunden.")
    return project


def _project_dict(project: Project) -> dict[str, Any]:
    return ProjectSchema.model_validate(project).model_dump(mode="json", exclude=_GEOMETRY_FIELDS)


def _project_summary(project: Project, phase: str | None) -> dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "project_number": project.project_number,
        "superior_project_id": project.superior_project_id,
        "project_groups": [g.short_name for g in project.project_groups],
        "phase": phase,
    }


def _text_dict(text: ProjectText) -> dict[str, Any]:
    data = ProjectTextSchema.model_validate(text).model_dump(mode="json")
    data["text_type"] = data["text_type"]["name"]
    data["attachments"] = [a["filename"] for a in data["attachments"]]
    return data


def list_projects(
    search: str | None = None,
    project_group: str | None = None,
    phase: MainPhaseLiteral | None = None,
    superior_project_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Search projects (drafts excluded), sorted by name.

    - search: case-insensitive substring of name or project number
    - project_group: short name or id of a project group
    - phase: planning phase (cached headline; manual override wins)
    - superior_project_id: only direct subprojects of this project
    Returns ``total`` plus one page of compact entries; use get_project for details.
    """
    get_principal(ctx)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    effective_phase = func.coalesce(
        ProjectProgress.manual_phase_override, ProjectProgress.computed_phase
    )
    with tool_session(ctx) as db:
        query = (
            db.query(Project, effective_phase)
            .outerjoin(ProjectProgress, ProjectProgress.project_id == Project.id)
            .filter(Project.is_draft.is_(False))
        )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(Project.name.ilike(pattern), Project.project_number.ilike(pattern))
            )
        if project_group:
            group_filter = ProjectGroup.short_name == project_group
            if project_group.isdigit():
                group_filter = or_(group_filter, ProjectGroup.id == int(project_group))
            query = query.filter(Project.project_groups.any(group_filter))
        if phase:
            query = query.filter(effective_phase == phase)
        if superior_project_id is not None:
            query = query.filter(Project.superior_project_id == superior_project_id)
        total = query.count()
        rows = (
            query.options(selectinload(Project.project_groups))
            .order_by(Project.name, Project.id)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "projects": [_project_summary(project, row_phase) for project, row_phase in rows],
        }


def get_project(project_id: int, *, ctx: Context) -> dict[str, Any]:
    """Project detail: all fields, project groups, direct subprojects and BVWP data."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        data = _project_dict(project)
        data["subprojects"] = [
            {"id": sub.id, "name": sub.name, "project_number": sub.project_number}
            for sub in get_subprojects(db, project.id)
        ]
        bvwp = get_bvwp_data(db, project.id)
        data["bvwp"] = (
            BvwpProjectDataSchema.model_validate(bvwp).model_dump(mode="json", exclude_none=True)
            if bvwp
            else None
        )
        return data


def get_project_progress(project_id: int, *, ctx: Context) -> dict[str, Any]:
    """Planning state (Planungsstand): effective phase, parallel tracks (PF,
    parliament), observations with their weight, subproject span and forecast."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        view = progress_crud.get_progress_view(db, project_id)
        return ProjectProgressSchema.model_validate(view).model_dump(mode="json")


def list_project_finves(project_id: int, *, ctx: Context) -> list[dict[str, Any]]:
    """Financing agreements (FinVe) of a project with their budget history per
    budget year, including the per-Haushaltstitel breakdown. Amounts in T€."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        return [f.model_dump(mode="json") for f in get_project_finves_with_budgets(db, project)]


def get_project_texts(
    project_id: int, text_type: str | None = None, *, ctx: Context
) -> list[dict[str, Any]]:
    """Texts of a project, optionally filtered by text type name (case-insensitive).
    Use list_text_types for the available types."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        texts = get_texts_for_project(db, project_id)
        if text_type:
            wanted = text_type.strip().lower()
            texts = [t for t in texts if t.text_type and t.text_type.name.lower() == wanted]
        return [_text_dict(t) for t in texts]


def list_text_types(*, ctx: Context) -> list[dict[str, Any]]:
    """Available project text types (id + name), needed for upsert_project_text."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        return [{"id": t.id, "name": t.name} for t in get_text_types(db)]


def update_project(project_id: int, changes: dict[str, Any], *, ctx: Context) -> dict[str, Any]:
    """Change project fields (requires ``project.edit``). ``changes`` maps field
    names to new values, e.g. {"description": "…", "nbs": true}; see get_project
    for the field names. Geometry and the draft flag cannot be changed here.
    Every change is written to the project changelog and can be reverted in the UI."""
    principal = get_principal(ctx)
    require(principal, "project.edit")
    blocked = sorted(set(changes) & _READONLY_UPDATE_FIELDS)
    if blocked:
        raise ToolError(f"Diese Felder sind über MCP nicht änderbar: {', '.join(blocked)}")
    unknown = sorted(set(changes) - set(ProjectUpdate.model_fields))
    if unknown:
        raise ToolError(f"Unbekannte Felder: {', '.join(unknown)}")
    try:
        update_data = ProjectUpdate.model_validate(changes).model_dump(exclude_unset=True)
    except ValidationError as exc:
        raise ToolError(f"Ungültige Werte: {exc}") from exc
    if not update_data:
        raise ToolError("Keine Änderungen übergeben.")

    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        if "superior_project_id" in update_data:
            try:
                validate_superior_project(db, project.id, update_data["superior_project_id"])
            except ProjectHierarchyError as exc:
                raise ToolError(str(exc)) from exc
        user = load_user(db, principal)
        create_changelog_for_patch(db, project, update_data, user.id, user.username)
        updated = update_project_crud(db, project.id, update_data, project=project)
        return _project_dict(updated)


def add_progress_observation(
    project_id: int,
    track: TrackLiteral,
    asserted_state: str,
    observed_date: date | None = None,
    note: str | None = None,
    confidence: float | None = None,
    is_expected: bool = False,
    source_type: SourceTypeLiteral = "MANUELL",
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Add a planning-state observation (requires ``progress.edit``).

    - track MAIN: asserted_state is a phase (NICHT_GESTARTET, VORPLANUNG,
      GENEHMIGUNGSPLANUNG, BAU, IN_BETRIEB)
    - track PF / PARL: asserted_state is OFFEN, LAEUFT or ABGESCHLOSSEN
    - is_expected: the date is a forecast, not a fact
    Returns the recomputed planning state."""
    principal = get_principal(ctx)
    require(principal, "progress.edit")
    try:
        payload = ProgressObservationCreate(
            source_type=source_type,
            track=track,
            asserted_state=asserted_state,
            observed_date=observed_date,
            confidence=confidence,
            note=note,
            is_expected=is_expected,
        ).model_dump(exclude_unset=True)
    except ValidationError as exc:
        raise ToolError(f"Ungültige Werte: {exc}") from exc
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        user = load_user(db, principal)
        progress_crud.create_observation(db, project_id, payload, user)
        view = progress_crud.get_progress_view(db, project_id)
        return ProjectProgressSchema.model_validate(view).model_dump(mode="json")


def upsert_project_text(
    project_id: int,
    header: str | None = None,
    text: str | None = None,
    text_type_id: int | None = None,
    weblink: str | None = None,
    text_id: int | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Create a project text, or update one when ``text_id`` is given (requires
    ``projecttext.edit``). Creating needs ``header`` and ``text_type_id`` (see
    list_text_types); on update only the passed fields change. Changes are
    written to the text changelog."""
    principal = get_principal(ctx)
    require(principal, "projecttext.edit")
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        if text_type_id is not None and text_type_id not in {t.id for t in get_text_types(db)}:
            raise ToolError(f"Texttyp {text_type_id} existiert nicht.")
        user = load_user(db, principal)

        if text_id is None:
            if not header or text_type_id is None:
                raise ToolError("Zum Anlegen sind header und text_type_id nötig.")
            created = create_text_for_project(
                db,
                project_id,
                {"header": header, "text": text, "weblink": weblink, "type": text_type_id},
            )
            create_text_changelog_for_create(db, created, project_id, user.id, user.username)
            db.commit()
            return _text_dict(created)

        linked = (
            db.query(TextToProject)
            .filter(TextToProject.text_id == text_id, TextToProject.project_id == project_id)
            .first()
        )
        existing = db.query(ProjectText).filter(ProjectText.id == text_id).first()
        if linked is None or existing is None:
            raise ToolError(f"Text {text_id} gehört nicht zu Projekt {project_id}.")
        update_data = {
            key: value
            for key, value in {
                "header": header,
                "text": text,
                "weblink": weblink,
                "type": text_type_id,
            }.items()
            if value is not None
        }
        if not update_data:
            raise ToolError("Keine Änderungen übergeben.")
        create_text_changelog_for_patch(
            db, existing, update_data, project_id, user.id, user.username
        )
        return _text_dict(update_project_text(db, text_id, update_data))


def register(server: MCPServer) -> None:
    for fn in (
        list_projects,
        get_project,
        get_project_progress,
        list_project_finves,
        get_project_texts,
        list_text_types,
    ):
        server.add_tool(fn, annotations=READ_ONLY)
    for fn in (update_project, add_progress_observation, upsert_project_text):
        server.add_tool(fn, annotations=WRITE)
