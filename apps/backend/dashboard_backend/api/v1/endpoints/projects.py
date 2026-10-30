from __future__ import annotations

import json

from fastapi import Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dashboard_backend.api.deps import get_project_or_404, get_project_or_redirect_404
from dashboard_backend.core.security import has_effective_permission, require_auth, require_permission
from dashboard_backend.crud.admin_assignments import link_project_to_finves
from dashboard_backend.crud.changelog import (
    create_changelog_for_patch,
    get_changelog_entry,
    get_project_changelog,
)
from dashboard_backend.crud import parliament as parliament_crud
from dashboard_backend.crud.finve_links import (
    FINVE_IDS_FIELD,
    FinveLinkConflict,
    FinveLinkError,
    set_project_finves,
)
from dashboard_backend.crud.finves import get_project_finves_with_budgets
from dashboard_backend.crud.sammel_finve_links import SAMMEL_YEARS_FIELD, set_project_sammel_years
from dashboard_backend.crud.projects.archive import (
    ArchiveError,
    archive_project,
    get_archived_projects,
    replacement,
    unarchive_project,
)
from dashboard_backend.crud.projects.bvwp import get_bvwp_data
from dashboard_backend.crud.projects.merge import MergeError, merge_projects
from dashboard_backend.crud.projects.projects import (
    ProjectHierarchyError,
    create_project,
    delete_project,
    finalize_project,
    get_draft_projects,
    get_project_options,
    get_projects,
    get_subprojects,
    has_subprojects,
    update_project,
    validate_superior_project,
)
from dashboard_backend.models.projects.project import Project
from dashboard_backend.crud.vib import get_vib_entries_for_project
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.models.parliament import IMPORT_KIND_POLITICIANS
from dashboard_backend.schemas.changelog import ChangeLogRead, RevertFieldRequest
from dashboard_backend.schemas.parliament import (
    ImportRunSchema,
    ProjectConstituenciesSchema,
    ProjectConstituencySchema,
)
from dashboard_backend.schemas.projects import ProjectSchema
from dashboard_backend.schemas.projects.project_schema import (
    FinveWithBudgetsSchema,
    ProjectOptionSchema,
)
from dashboard_backend.schemas.projects.bvwp_schema import BvwpProjectDataSchema
from dashboard_backend.schemas.projects.project_archive_schema import (
    ArchivedProjectSchema,
    ProjectArchiveRequest,
    ProjectArchiveResult,
    ProjectReplacementSchema,
    ProjectUnarchiveRequest,
)
from dashboard_backend.schemas.projects.link_finves_schema import LinkFinvesInput
from dashboard_backend.schemas.projects.project_create_schema import ProjectCreate
from dashboard_backend.schemas.projects.project_merge_schema import (
    ProjectMergeRequest,
    ProjectMergeResult,
)
from dashboard_backend.schemas.projects.project_update_schema import ProjectUpdate
from dashboard_backend.schemas.vib import VibEntryForProjectSchema

router = AuthRouter()


def _validate_hierarchy(db: Session, project_id: int | None, update_data: dict) -> None:
    """Reject a superior_project_id that does not exist, is the project itself, or
    already sits below it in the tree. Translates to HTTP 400."""
    if "superior_project_id" not in update_data:
        return
    try:
        validate_superior_project(db, project_id, update_data["superior_project_id"])
    except ProjectHierarchyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _validate_geometry_ownership(db: Session, project: Project, update_data: dict) -> None:
    """Reject writing the geometry of a project that aggregates it from its subprojects.

    Such a project does not own its geometry — the next change anywhere in its subtree
    would silently discard what was written here. Switching the toggle off in the same
    request is allowed and hands the geometry back to the project.
    """
    if "geojson_representation" not in update_data:
        return

    requested = update_data.get("geojson_from_subprojects")
    aggregated = project.geojson_from_subprojects if requested is None else requested
    if aggregated and has_subprojects(db, project.id):
        raise HTTPException(
            status_code=400,
            detail=(
                "Die Geometrie dieses Projekts wird automatisch aus seinen Unterprojekten "
                "zusammengesetzt. Schalte die automatische Zusammensetzung ab, um eine "
                "eigene Geometrie zu pflegen."
            ),
        )


@router.get("/", response_model=list[ProjectSchema])
def read_all_projects(db: Session = Depends(get_db)):
    """Retrieve all projects."""
    return get_projects(db)


@router.post("/", response_model=ProjectSchema, status_code=201)
def create_project_endpoint(
    body: ProjectCreate,
    current_user: User = Depends(require_permission("project.create")),
    db: Session = Depends(get_db),
):
    """Create a new project. Only `name` is required."""
    data = body.model_dump(exclude_unset=True)
    _validate_hierarchy(db, None, data)
    return create_project(db, data)


# NOTE: must be declared before GET /{project_id} so "options" is not captured
# as a project id.
@router.get("/options", response_model=list[ProjectOptionSchema])
def read_project_options(db: Session = Depends(get_db)):
    """Minimal project list (id, name, number, parent) for pickers and dropdowns.

    ``GET /`` returns the full ``ProjectSchema`` including
    ``geojson_representation``; every consumer that only renders a select box
    should use this route instead.
    """
    return get_project_options(db)


# NOTE: must be declared before GET /{project_id} so "drafts" is not captured
# as a project id.
@router.get("/drafts", response_model=list[ProjectSchema])
def read_draft_projects(
    current_user: User = Depends(require_permission("project.create")),
    db: Session = Depends(get_db),
):
    """Retrieve all draft (not yet finalized) projects for the admin board."""
    return get_draft_projects(db)


# NOTE: must be declared before GET /{project_id} so "archived" is not captured
# as a project id.
@router.get("/archived", response_model=list[ArchivedProjectSchema])
def read_archived_projects(
    current_user: User = Depends(require_permission("project.delete")),
    db: Session = Depends(get_db),
):
    """Archived projects for the admin archive page, newest first
    (feature-project-archive.md)."""
    return get_archived_projects(db)


@router.post("/{project_id}/archive", response_model=ProjectArchiveResult)
def archive_project_endpoint(
    project_id: int,
    body: ProjectArchiveRequest,
    current_user: User = Depends(require_permission("project.delete")),
    db: Session = Depends(get_db),
):
    """Archive a replaced or superseded project with a mandatory reason. Refused
    (400, naming the links) while FinVe/GVFG links or non-archived subprojects
    exist, or when the lifecycle is ABGEBROCHEN. Recorded in the changelog."""
    try:
        result = archive_project(
            db,
            project_id,
            body.reason,
            current_user.id,
            current_user.username,
            replaced_by_project_id=body.replaced_by_project_id,
        )
    except ArchiveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.get("/{project_id}/replacement", response_model=ProjectReplacementSchema)
def read_project_replacement(
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Public: the successor of an archived, replaced project and the archived
    projects this one replaces (feature-project-archive.md → „Ersetzt durch“)."""
    return replacement(db, project.id)


@router.post("/{project_id}/unarchive", response_model=ProjectSchema)
def unarchive_project_endpoint(
    project_id: int,
    body: ProjectUnarchiveRequest,
    current_user: User = Depends(require_permission("project.delete")),
    db: Session = Depends(get_db),
):
    """Restore an archived project. Recorded in the changelog."""
    try:
        project = unarchive_project(db, project_id, body.reason, current_user.id, current_user.username)
    except ArchiveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/finalize", response_model=ProjectSchema)
def finalize_project_endpoint(
    project_id: int,
    current_user: User = Depends(require_permission("project.create")),
    db: Session = Depends(get_db),
):
    """Finalize a draft project (mark it as no longer a draft)."""
    project = finalize_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project_endpoint(
    project_id: int,
    current_user: User = Depends(require_permission("project.delete")),
    db: Session = Depends(get_db),
):
    """Delete a project — a draft discarded in the wizard or a finalized project
    removed from the detail page. Subprojects are removed with it (FK ON DELETE
    CASCADE), so the frontend asks for confirmation twice."""
    try:
        deleted = delete_project(db, project_id)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Das Projekt kann nicht gelöscht werden, weil noch Verknüpfungen bestehen.",
        ) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return None


@router.post("/merge", response_model=ProjectMergeResult)
def merge_projects_endpoint(
    body: ProjectMergeRequest,
    current_user: User = Depends(require_permission("project.merge")),
    db: Session = Depends(get_db),
):
    """Merge a duplicate project into another one (feature-project-merge.md).
    ``apply=false`` returns the plan only; ``apply=true`` deletes the merged
    project and leaves a redirect from its id to the survivor."""
    try:
        return merge_projects(
            db,
            body.survivor_id,
            body.merged_id,
            geometry_from=body.geometry_from,
            apply=body.apply,
            user_id=current_user.id,
            username=current_user.username,
        )
    except MergeError as exc:
        # Raised while planning, before anything is written.
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{project_id}", response_model=ProjectSchema)
def read_project(project: Project = Depends(get_project_or_redirect_404)):
    """Retrieve a single project by ID. The id of a merged project resolves to
    the project it was merged into — the response then carries the new id, and
    the frontend replaces the URL."""
    return project


@router.get("/{project_id}/subprojects", response_model=list[ProjectSchema])
def read_subprojects(
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Direct subprojects of a project, drafts and archived projects excluded."""
    return get_subprojects(db, project.id)


@router.get(
    "/{project_id}/constituencies",
    response_model=ProjectConstituenciesSchema,
    dependencies=[Depends(require_auth())],
)
def read_project_constituencies(
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Constituencies this project touches, heaviest first, with their MPs.

    Requires a login (any role): members of parliament are only shown to
    signed-in users, unlike the other project reads. A project without a geometry returns an
    empty list plus ``has_geometry = false`` — the UI says *why* there is nothing
    to show instead of rendering an empty block.
    """
    rows = parliament_crud.links_for_project(db, project.id)
    mandates_by_constituency = parliament_crud.mandates_for_constituencies(
        db, [constituency.id for _, constituency in rows]
    )

    constituencies: list[ProjectConstituencySchema] = []
    for link, constituency in rows:
        direct, listed = parliament_crud.split_mandates(
            mandates_by_constituency.get(constituency.id, [])
        )
        constituencies.append(
            ProjectConstituencySchema(
                id=constituency.id,
                number=constituency.number,
                name=constituency.name,
                state=constituency.state,
                length_km=link.length_km,
                share=link.share,
                overlap_kind=link.overlap_kind,
                direct_mandates=direct,
                list_mandates=listed,
                has_direct_mandate=bool(direct),
                has_any_mandate=bool(direct or listed),
            )
        )

    last_import = parliament_crud.last_successful_run(db, IMPORT_KIND_POLITICIANS)
    return ProjectConstituenciesSchema(
        project_id=project.id,
        has_geometry=bool(project.geojson_representation),
        constituencies=constituencies,
        last_import=ImportRunSchema.model_validate(last_import) if last_import else None,
    )


@router.get("/{project_id}/bvwp", response_model=BvwpProjectDataSchema)
def get_project_bvwp(
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Return BVWP assessment data for a project. Returns 404 if no BVWP data exists."""
    bvwp = get_bvwp_data(db, project.id)
    if not bvwp:
        raise HTTPException(status_code=404, detail="No BVWP data for this project")
    return bvwp


@router.get("/{project_id}/vib", response_model=list[VibEntryForProjectSchema])
def get_project_vib(
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Return all VIB entries linked to a project, newest year first."""
    entries = get_vib_entries_for_project(db, project.id)
    return [VibEntryForProjectSchema.from_entry(e) for e in entries]


@router.patch("/{project_id}", response_model=ProjectSchema)
def patch_project(
    body: ProjectUpdate,
    current_user: User = Depends(require_permission("project.edit")),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Update project fields. All changed fields are recorded in the changelog."""
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return project

    _validate_hierarchy(db, project.id, update_data)
    _validate_geometry_ownership(db, project, update_data)

    # Record before/after values in changelog (committed together with the update below)
    create_changelog_for_patch(db, project, update_data, current_user.id, current_user.username)
    return update_project(db, project.id, update_data, project=project)


@router.get("/{project_id}/finves", response_model=list[FinveWithBudgetsSchema])
def get_project_finves(
    include_subprojects: bool = False,
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Return all FinVes linked to a project, each with their full budget history
    including per-Haushaltstiteln breakdown. ``include_subprojects`` adds the
    FinVes of all sub-projects (each once, flagged ``from_subprojects``)."""
    return get_project_finves_with_budgets(db, project, include_subprojects=include_subprojects)


@router.post("/{project_id}/finves", status_code=204)
def link_finves_to_project(
    body: LinkFinvesInput,
    current_user: User = Depends(require_permission("finve.edit")),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Link a list of existing FinVes to this project. Existing links are preserved;
    the change is logged and the planning state recomputed."""
    try:
        link_project_to_finves(db, project.id, body.finve_ids, current_user)
    except FinveLinkConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FinveLinkError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return None


@router.get("/{project_id}/changelog", response_model=list[ChangeLogRead])
def read_project_changelog(
    current_user: User = Depends(require_auth()),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Return the full changelog for a project, newest entries first."""
    return get_project_changelog(db, project.id)


def _revert_finve_ids(db: Session, project: Project, entry, current_user: User) -> Project:
    """Set the project's permanent FinVe links back to the entry's old list.
    FinVe links are guarded by ``finve.edit`` on top of ``project.edit``."""
    if not has_effective_permission(current_user, "finve.edit"):
        raise HTTPException(status_code=403, detail="Not enough privileges")
    target = json.loads(entry.old_value) if entry.old_value is not None else []
    try:
        set_project_finves(db, project.id, target, user=current_user, action="REVERT")
    except FinveLinkError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.refresh(project)
    return project


def _revert_sammel_years(db: Session, project: Project, entry, current_user: User) -> Project:
    """Set the project's years in one Sammel-FinVe back to the entry's old list.
    Guarded by ``finve.edit`` like the permanent FinVe links."""
    if not has_effective_permission(current_user, "finve.edit"):
        raise HTTPException(status_code=403, detail="Not enough privileges")
    old = json.loads(entry.old_value or entry.new_value or "{}")
    try:
        set_project_sammel_years(
            db, project.id, old["finve_id"], old.get("years") or [], user=current_user, action="REVERT"
        )
    except FinveLinkError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.refresh(project)
    return project


@router.post("/{project_id}/changelog/revert", response_model=ProjectSchema)
def revert_project_field(
    body: RevertFieldRequest,
    current_user: User = Depends(require_permission("project.edit")),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db),
):
    """Revert a single field to its previous value as recorded in the given ChangeLogEntry."""
    entry = get_changelog_entry(db, body.changelog_entry_id, project.id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Changelog entry not found")

    field_name = entry.field_name
    if field_name == FINVE_IDS_FIELD:
        return _revert_finve_ids(db, project, entry, current_user)
    if field_name == SAMMEL_YEARS_FIELD:
        return _revert_sammel_years(db, project, entry, current_user)
    if field_name not in ProjectUpdate.model_fields.keys():
        raise HTTPException(status_code=400, detail=f"Unknown field: {field_name}")

    # Parse stored JSON value back to the original Python type
    target_value = json.loads(entry.old_value) if entry.old_value is not None else None

    _validate_geometry_ownership(db, project, {field_name: target_value})

    # Record the revert action in the changelog before applying it
    create_changelog_for_patch(
        db,
        project,
        {field_name: target_value},
        current_user.id,
        current_user.username,
        action="REVERT",
    )
    return update_project(db, project.id, {field_name: target_value}, project=project)
