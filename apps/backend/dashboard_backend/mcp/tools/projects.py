"""Project, planning-state, financing and text tools.

Outputs stay compact on purpose: every answer lands in the client's context
window, so lists are paginated and geometries (``geojson_representation``,
``centroid``) are never returned.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import ValidationError
from sqlalchemy import and_, exists, func, not_, or_, select
from sqlalchemy.orm import Session, selectinload

from dashboard_backend.crud.changelog import (
    create_changelog_for_create,
    create_changelog_for_patch,
    create_text_changelog_for_create,
    create_text_changelog_for_patch,
)
from dashboard_backend.crud.finves import get_project_finves_with_budgets
from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.crud.projects.bvwp import get_bvwp_data
from dashboard_backend.crud.projects.merge import MergeError, resolve_redirect
from dashboard_backend.crud.projects.merge import merge_projects as merge_projects_crud
from dashboard_backend.crud.projects.projects import (
    ProjectHierarchyError,
    create_project as create_project_crud,
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
from dashboard_backend.crud.projects.progress import BEDARFSPLAN_GROUP_SHORT_NAME_PREFIX
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.models.associations.project_to_project_group import ProjectToProjectGroup
from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.associations.text_to_project import TextToProject
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.projects.project_text import ProjectText
from dashboard_backend.schemas.projects import ProjectSchema
from dashboard_backend.schemas.projects.bvwp_schema import BvwpProjectDataSchema
from dashboard_backend.schemas.projects.progress_schema import (
    LifecycleStatusLiteral,
    MainPhaseLiteral,
    ManualSourceTypeLiteral,
    ProgressObservationCreate,
    ProjectProgressSchema,
    TrackLiteral,
)
from dashboard_backend.schemas.projects.project_create_schema import ProjectCreate
from dashboard_backend.schemas.projects.project_text_schema import ProjectTextSchema
from dashboard_backend.schemas.projects.project_update_schema import ProjectUpdate
from dashboard_backend.services.geo_length import compute_geojson_length_km

MAX_LIMIT = 200

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=False)

# Never sent to the client: geometry blobs are huge and useless as text.
_GEOMETRY_FIELDS = {"geojson_representation", "centroid"}
# Fields update_project may not touch: geometry (no meaningful text edit) and the
# draft flag (finalizing is a separate workflow in the UI).
_READONLY_UPDATE_FIELDS = {"geojson_representation", "is_draft"}
# Changed through set_project_groups, which resolves names and keeps other groups.
_GROUP_FIELD = "project_group_ids"


def _project_or_error(db: Session, project_id: int) -> Project:
    project = get_project_by_id(db, project_id)
    if project is None:
        target = resolve_redirect(db, project_id)
        if target is not None:
            raise ToolError(
                f"Projekt {project_id} wurde mit Projekt {target} zusammengeführt — "
                f"bitte Projekt {target} verwenden."
            )
        raise ToolError(f"Projekt {project_id} nicht gefunden.")
    return project


def _project_dict(project: Project) -> dict[str, Any]:
    return ProjectSchema.model_validate(project).model_dump(mode="json", exclude=_GEOMETRY_FIELDS)


def _project_summary(
    project: Project, phase: str | None, is_known: bool | None = None
) -> dict[str, Any]:
    summary = {
        "id": project.id,
        "name": project.name,
        "project_number": project.project_number,
        "superior_project_id": project.superior_project_id,
        "project_groups": [g.short_name for g in project.project_groups],
        "phase": phase,
    }
    if is_known is not None:
        summary["is_known"] = is_known
    return summary


# --- SQL expressions over Project (outer-joined to ProjectProgress) ----------
# Shared by list_projects and the data-quality tools (mcp/tools/data_quality.py).


def effective_phase_expr():
    return func.coalesce(ProjectProgress.manual_phase_override, ProjectProgress.computed_phase)


def is_known_expr():
    """SQL twin of ``stored_headline_phase(...) is not None``: an override, or a
    computed phase that a credible observation decided (confidence > 0). The
    ``NICHT_GESTARTET``/0.0 fallback and a missing progress row are unknown."""
    return or_(
        ProjectProgress.manual_phase_override.isnot(None),
        and_(ProjectProgress.computed_phase.isnot(None), ProjectProgress.computed_confidence > 0),
    )


def has_geometry_expr():
    # An empty FeatureCollection carries no "coordinates" key.
    return and_(
        Project.geojson_representation.isnot(None),
        Project.geojson_representation.contains('"coordinates"'),
    )


def has_length_expr():
    return and_(Project.length.isnot(None), Project.length > 0)


def _bswag_member_expr():
    return exists().where(
        ProjectToProjectGroup.project_id == Project.id,
        ProjectToProjectGroup.project_group_id == ProjectGroup.id,
        func.upper(ProjectGroup.short_name).like(f"{BEDARFSPLAN_GROUP_SHORT_NAME_PREFIX}%"),
    )


def parl_relevant_expr(relevant: bool):
    """SQL twin of ``resolve_parl_relevant``: the override wins, else BSWAG* groups."""
    override = ProjectProgress.parl_befassung_relevant
    member = _bswag_member_expr()
    if relevant:
        return or_(override.is_(True), and_(override.is_(None), member))
    return or_(override.is_(False), and_(override.is_(None), not_(member)))


def last_change_expr():
    return (
        select(func.max(ChangeLog.timestamp))
        .where(ChangeLog.project_id == Project.id)
        .correlate(Project)
        .scalar_subquery()
    )


def _text_dict(text: ProjectText) -> dict[str, Any]:
    data = ProjectTextSchema.model_validate(text).model_dump(mode="json")
    data["text_type"] = data["text_type"]["name"]
    data["attachments"] = [a["filename"] for a in data["attachments"]]
    return data


def _group_filter(project_group: str):
    """Match a project group by id, short name or name (case-insensitive)."""
    value = project_group.strip()
    lowered = value.lower()
    clauses = [
        func.lower(ProjectGroup.short_name) == lowered,
        func.lower(ProjectGroup.name) == lowered,
    ]
    if value.isdigit():
        clauses.append(ProjectGroup.id == int(value))
    return or_(*clauses)


def _resolve_group_ids(db: Session, values: list[str]) -> set[int]:
    ids = set()
    for value in values:
        group = db.query(ProjectGroup).filter(_group_filter(value)).first()
        if group is None:
            raise ToolError(f"Projektgruppe '{value}' nicht gefunden.")
        ids.add(group.id)
    return ids


def list_project_groups(search: str | None = None, *, ctx: Context) -> dict[str, Any]:
    """Project groups (e.g. Bedarfsplan, Deutschlandtakt) with id, short name,
    name and the number of (non-draft) projects. ``search`` is a case-insensitive
    substring of short name or name. Use the short name or id as ``project_group``
    in list_projects."""
    get_principal(ctx)
    project_count = func.count(Project.id)
    with tool_session(ctx) as db:
        query = (
            db.query(ProjectGroup, project_count)
            .outerjoin(ProjectGroup.projects.and_(Project.is_draft.is_(False)))
            .group_by(ProjectGroup.id)
        )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(ProjectGroup.short_name.ilike(pattern), ProjectGroup.name.ilike(pattern))
            )
        rows = query.order_by(ProjectGroup.name, ProjectGroup.id).all()
        return {
            "groups": [
                {
                    "id": group.id,
                    "short_name": group.short_name,
                    "name": group.name,
                    "description": group.description,
                    "project_count": count,
                }
                for group, count in rows
            ]
        }


ProjectOrder = Literal["name", "id", "length", "last_change"]


def list_projects(
    search: str | None = None,
    project_group: str | list[str] | None = None,
    phase: MainPhaseLiteral | None = None,
    superior_project_id: int | None = None,
    is_known: bool | None = None,
    has_geometry: bool | None = None,
    has_length: bool | None = None,
    lifecycle_status: LifecycleStatusLiteral | None = None,
    parl_befassung_relevant: bool | None = None,
    updated_since: date | None = None,
    order_by: ProjectOrder = "name",
    descending: bool = False,
    limit: int = 50,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Search projects (drafts excluded), sorted by name unless ``order_by`` says otherwise.

    - search: case-insensitive substring of name or project number
    - project_group: id, short name or name of a project group (case-insensitive,
      see list_project_groups); a list matches projects in all of the groups
    - phase: planning phase (cached headline; manual override wins)
    - superior_project_id: only direct subprojects of this project
    - is_known: true = the planning state is backed by an observation or an
      override; false = unknown (``phase`` then shows the NICHT_GESTARTET fallback)
    - has_geometry / has_length: whether a line/point geometry or a length is stored
    - lifecycle_status: AKTIV (also projects without planning state), PAUSIERT, ABGEBROCHEN
    - parl_befassung_relevant: parliamentary involvement relevant (override, else
      membership in a BSWAG* group)
    - updated_since: only projects with a changelog entry on or after this date
    - order_by: name, id, length or last_change (newest change; projects never
      changed come last); descending reverses the order
    Returns ``total`` plus one page of compact entries; use get_project for details.
    """
    get_principal(ctx)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    effective_phase = effective_phase_expr()
    known = is_known_expr()
    with tool_session(ctx) as db:
        query = (
            db.query(Project, effective_phase, known)
            .outerjoin(ProjectProgress, ProjectProgress.project_id == Project.id)
            .filter(Project.is_draft.is_(False))
        )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(Project.name.ilike(pattern), Project.project_number.ilike(pattern))
            )
        groups = [project_group] if isinstance(project_group, str) else project_group or []
        groups = [g for g in groups if g.strip()]
        if groups:
            query = query.filter(
                and_(*(Project.project_groups.any(_group_filter(g)) for g in groups))
            )
        if phase:
            query = query.filter(effective_phase == phase)
        if superior_project_id is not None:
            query = query.filter(Project.superior_project_id == superior_project_id)
        if is_known is not None:
            query = query.filter(known if is_known else not_(known))
        if has_geometry is not None:
            query = query.filter(has_geometry_expr() if has_geometry else not_(has_geometry_expr()))
        if has_length is not None:
            query = query.filter(has_length_expr() if has_length else not_(has_length_expr()))
        if lifecycle_status:
            query = query.filter(
                func.coalesce(ProjectProgress.lifecycle_status, "AKTIV") == lifecycle_status
            )
        if parl_befassung_relevant is not None:
            query = query.filter(parl_relevant_expr(parl_befassung_relevant))
        if updated_since is not None:
            query = query.filter(
                exists().where(
                    ChangeLog.project_id == Project.id,
                    ChangeLog.timestamp >= datetime.combine(updated_since, time.min),
                )
            )
        total = query.count()

        sort_key = {
            "name": Project.name,
            "id": Project.id,
            "length": Project.length,
            "last_change": last_change_expr(),
        }[order_by]
        primary = sort_key.desc() if descending else sort_key.asc()
        if order_by in {"length", "last_change"}:
            # Projects without a length / without changes go last in both directions.
            primary = primary.nulls_last()
        rows = (
            query.options(selectinload(Project.project_groups))
            .order_by(primary, Project.name, Project.id)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "projects": [
                _project_summary(project, row_phase, bool(row_known))
                for project, row_phase, row_known in rows
            ],
        }


def get_project(project_id: int, *, ctx: Context) -> dict[str, Any]:
    """Project detail: all fields, project groups, direct subprojects and BVWP data.
    The id of a merged project resolves to the project it was merged into
    (``redirected_from`` then names the old id)."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        redirected_from = None
        if get_project_by_id(db, project_id) is None:
            target = resolve_redirect(db, project_id)
            if target is not None:
                redirected_from, project_id = project_id, target
        project = _project_or_error(db, project_id)
        data = _project_dict(project)
        if redirected_from is not None:
            data["redirected_from"] = redirected_from
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


def create_project(
    name: str,
    superior_project_id: int | None = None,
    project_number: str | None = None,
    description: str | None = None,
    project_groups: list[str] | None = None,
    fields: dict[str, Any] | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Create a project, e.g. a subproject (stage) of an existing one (requires
    ``project.create``). The project is created final, not as a draft.

    - superior_project_id: the parent project (see get_project for subprojects)
    - project_groups: ids, short names or names (see list_project_groups)
    - fields: further project fields as in update_project, e.g. {"length": 12.5}
    Geometry cannot be set here: add it afterwards with route_project_geometry or
    edit_project_geometry. The creation is written to the project
    changelog. Returns the new project."""
    principal = get_principal(ctx)
    require(principal, "project.create")
    extra = dict(fields or {})
    blocked = sorted(set(extra) & (_READONLY_UPDATE_FIELDS | {_GROUP_FIELD}))
    if blocked:
        raise ToolError(f"Diese Felder sind hier nicht setzbar: {', '.join(blocked)}")
    unknown = sorted(set(extra) - set(ProjectCreate.model_fields))
    if unknown:
        raise ToolError(f"Unbekannte Felder: {', '.join(unknown)}")
    extra.update(
        {
            key: value
            for key, value in {
                "name": name,
                "superior_project_id": superior_project_id,
                "project_number": project_number,
                "description": description,
            }.items()
            if value is not None
        }
    )
    try:
        data = ProjectCreate.model_validate(extra).model_dump(exclude_unset=True)
    except ValidationError as exc:
        raise ToolError(f"Ungültige Werte: {exc}") from exc
    data["is_draft"] = False

    with tool_session(ctx) as db:
        if "superior_project_id" in data:
            try:
                validate_superior_project(db, None, data["superior_project_id"])
            except ProjectHierarchyError as exc:
                raise ToolError(str(exc)) from exc
        groups = [g for g in project_groups or [] if g.strip()]
        if groups:
            data[_GROUP_FIELD] = sorted(_resolve_group_ids(db, groups))
        user = load_user(db, principal)
        project = create_project_crud(db, data)
        create_changelog_for_create(
            db,
            project,
            {k: v for k, v in data.items() if k not in {"is_draft", _GROUP_FIELD}},
            user.id,
            user.username,
        )
        db.commit()
        db.refresh(project)
        return _project_dict(project)


def compute_project_length(
    project_id: int, apply: bool = False, *, ctx: Context
) -> dict[str, Any]:
    """Length in km computed from the project geometry — the same calculation as
    "Länge aus Geometrie berechnen" in the UI (geodesic sum over all lines).
    Returns the computed and the stored length. With ``apply=true`` the computed
    value is written to the ``length`` field (requires ``project.edit``; recorded
    in the changelog). This is the source for ``length``: use it instead of
    published lengths (e.g. from DB press releases), which measure differently."""
    principal = get_principal(ctx)
    if apply:
        require(principal, "project.edit")
    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        computed = compute_geojson_length_km(project.geojson_representation)
        result = {
            "project_id": project.id,
            "has_geometry": bool(project.geojson_representation),
            "geometry_from_subprojects": bool(project.geojson_from_subprojects),
            "computed_length_km": computed,
            "stored_length_km": project.length,
            "applied": False,
        }
        if not apply:
            return result
        if computed is None:
            raise ToolError("Aus der Projektgeometrie lässt sich keine Länge berechnen.")
        if project.length != computed:
            update_data = {"length": computed}
            user = load_user(db, principal)
            create_changelog_for_patch(db, project, update_data, user.id, user.username)
            project = update_project_crud(db, project.id, update_data, project=project)
        result.update(stored_length_km=project.length, applied=True)
        return result


def update_project(project_id: int, changes: dict[str, Any], *, ctx: Context) -> dict[str, Any]:
    """Change project fields (requires ``project.edit``). ``changes`` maps field
    names to new values, e.g. {"description": "…", "nbs": true}; see get_project
    for the field names. Geometry and the draft flag cannot be changed here
    (geometry: route_project_geometry / edit_project_geometry); use
    set_project_groups for the group assignment. ``length`` comes from the
    geometry: set it with compute_project_length, not from published figures.
    Every change is written to the project changelog and can be reverted in the UI."""
    principal = get_principal(ctx)
    require(principal, "project.edit")
    if _GROUP_FIELD in changes:
        raise ToolError("Projektgruppen bitte mit set_project_groups ändern.")
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


def set_project_groups(
    project_id: int,
    add: list[str] | None = None,
    remove: list[str] | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Add the project to and/or remove it from project groups (requires
    ``project.edit``). Groups are given by id, short name or name
    (case-insensitive, see list_project_groups); other memberships stay.
    The change is written to the project changelog and can be reverted in the UI.
    Returns the project's groups afterwards."""
    principal = get_principal(ctx)
    require(principal, "project.edit")
    add = [g for g in add or [] if g.strip()]
    remove = [g for g in remove or [] if g.strip()]
    if not add and not remove:
        raise ToolError("Keine Gruppen übergeben (add oder remove).")

    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        add_ids, remove_ids = _resolve_group_ids(db, add), _resolve_group_ids(db, remove)
        if add_ids & remove_ids:
            raise ToolError("Eine Gruppe steht sowohl in add als auch in remove.")
        current = {g.id for g in project.project_groups}
        new_ids = sorted((current | add_ids) - remove_ids)
        if set(new_ids) != current:
            update_data = {_GROUP_FIELD: new_ids}
            user = load_user(db, principal)
            create_changelog_for_patch(db, project, update_data, user.id, user.username)
            project = update_project_crud(db, project.id, update_data, project=project)
        return {
            "project_id": project.id,
            "project_groups": [
                {"id": g.id, "short_name": g.short_name, "name": g.name}
                for g in sorted(project.project_groups, key=lambda g: g.id)
            ],
        }


def add_progress_observation(
    project_id: int,
    track: TrackLiteral,
    asserted_state: str,
    observed_date: date | None = None,
    note: str | None = None,
    confidence: float | None = None,
    is_expected: bool = False,
    source_type: ManualSourceTypeLiteral = "MANUELL",
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


def delete_progress_observation(
    project_id: int, observation_id: int, *, ctx: Context
) -> dict[str, Any]:
    """Delete a manual planning-state observation (requires ``progress.edit``),
    e.g. a duplicate or a wrong entry. Observation ids are listed by
    get_project_progress. Derived observations (``is_derived``, from the
    imports) cannot be deleted. Returns the recomputed planning state."""
    principal = get_principal(ctx)
    require(principal, "progress.edit")
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        user = load_user(db, principal)
        try:
            deleted = progress_crud.delete_observation(db, project_id, observation_id, user)
        except progress_crud.DerivedObservationDeleteError as exc:
            raise ToolError(
                "Abgeleitete Beobachtungen stammen aus den Importen und lassen sich "
                "nicht löschen."
            ) from exc
        if deleted is None:
            raise ToolError(f"Beobachtung {observation_id} gehört nicht zu Projekt {project_id}.")
        view = progress_crud.get_progress_view(db, project_id)
        return ProjectProgressSchema.model_validate(view).model_dump(mode="json")


def set_phase_override(
    project_id: int,
    phase: MainPhaseLiteral | None = None,
    note: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Set or clear the manual phase override of a project (requires
    ``progress.edit``). The override wins over the phase computed from the
    observations; the observations stay untouched as evidence.

    - phase: the phase to pin; ``null`` clears the override (the computed phase
      applies again)
    - note: why the override is set (required when setting, e.g. the source)
    An override on a superior project pins its whole subtree.
    Returns the recomputed planning state."""
    principal = get_principal(ctx)
    require(principal, "progress.edit")
    if phase is not None and not (note and note.strip()):
        raise ToolError("Zum Setzen eines Overrides ist eine Begründung (note) nötig.")
    payload: dict[str, Any] = (
        {"manual_phase_override": phase, "manual_override_note": note.strip()}
        if phase is not None
        else {"clear_phase_override": True}
    )
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        progress_crud.update_progress(db, project_id, payload, load_user(db, principal))
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


def merge_projects(
    survivor_id: int,
    merged_id: int,
    geometry_from: Literal["survivor", "merged"] = "survivor",
    apply: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Merge a duplicate into another project (requires ``project.merge``).
    ``survivor_id`` stays, ``merged_id`` is deleted; its old id redirects to the
    survivor. Without ``apply`` (default) nothing is written — the answer is the
    plan: field changes, links moved/dropped per table, moved subprojects and
    warnings. Check it, then call again with ``apply=true``.

    - Fields: the survivor wins, its empty fields are filled, flags are OR-ed.
    - geometry_from: whose geometry (with length, operational points and routes)
      is kept; ``survivor`` by default, automatically ``merged`` when the
      survivor has none.
    - All links (groups, texts, FinVe/VIB/…, todos, observations, changelog,
      subprojects) move to the survivor; duplicates are dropped.
    - Rejected when one project is an ancestor of the other.
    One pair per call."""
    principal = get_principal(ctx)
    require(principal, "project.merge")
    with tool_session(ctx) as db:
        user = load_user(db, principal) if apply else None
        try:
            return merge_projects_crud(
                db,
                survivor_id,
                merged_id,
                geometry_from=geometry_from,
                apply=apply,
                user_id=user.id if user else None,
                username=user.username if user else None,
            )
        except MergeError as exc:
            raise ToolError(str(exc)) from exc


def register(server: MCPServer) -> None:
    for fn in (
        list_project_groups,
        list_projects,
        get_project,
        get_project_progress,
        list_project_finves,
        get_project_texts,
        list_text_types,
    ):
        server.add_tool(fn, annotations=READ_ONLY)
    for fn in (
        create_project,
        compute_project_length,
        update_project,
        set_project_groups,
        add_progress_observation,
        set_phase_override,
        upsert_project_text,
    ):
        server.add_tool(fn, annotations=WRITE)
    server.add_tool(delete_progress_observation, annotations=DESTRUCTIVE)
    server.add_tool(merge_projects, annotations=DESTRUCTIVE)
