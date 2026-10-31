"""Revert one recorded field change of a project — shared by the REST endpoint
(``POST /projects/{id}/changelog/revert``) and the MCP tool ``revert_project_change``.

The caller decides how a permission is checked (``can``): the REST layer asks
the user's effective capabilities, MCP the key's (owner ∩ scopes). Errors carry
an HTTP-like status so the endpoint can map them one to one.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from sqlalchemy.orm import Session

from dashboard_backend.crud.changelog import create_changelog_for_patch, get_changelog_entry
from dashboard_backend.crud.finve_links import FINVE_IDS_FIELD, FinveLinkError, set_project_finves
from dashboard_backend.crud.projects.projects import has_subprojects, update_project
from dashboard_backend.crud.sammel_finve_links import SAMMEL_YEARS_FIELD, set_project_sammel_years
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.users import User
from dashboard_backend.schemas.projects.project_update_schema import ProjectUpdate

GEOMETRY_OWNED_BY_SUBPROJECTS = (
    "Die Geometrie dieses Projekts wird automatisch aus seinen Unterprojekten "
    "zusammengesetzt. Schalte die automatische Zusammensetzung ab, um eine "
    "eigene Geometrie zu pflegen."
)


class RevertError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class GeometryOwnershipError(ValueError):
    pass


def validate_geometry_ownership(db: Session, project: Project, update_data: dict) -> None:
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
        raise GeometryOwnershipError(GEOMETRY_OWNED_BY_SUBPROJECTS)


def revert_changelog_entry(
    db: Session,
    project: Project,
    entry_id: int,
    user: User,
    can: Callable[[str], bool],
) -> Project:
    """Set the entry's field back to its recorded old value and log a REVERT.

    ``project.edit`` is the caller's job; FinVe links (permanent and per
    Sammel-FinVe year) additionally need ``finve.edit``, checked here.
    """
    entry = get_changelog_entry(db, entry_id, project.id)
    if entry is None:
        raise RevertError(404, "Changelog entry not found")

    field_name = entry.field_name
    if field_name in (FINVE_IDS_FIELD, SAMMEL_YEARS_FIELD):
        if not can("finve.edit"):
            raise RevertError(403, "Not enough privileges")
        try:
            if field_name == FINVE_IDS_FIELD:
                target = json.loads(entry.old_value) if entry.old_value is not None else []
                set_project_finves(db, project.id, target, user=user, action="REVERT")
            else:
                old = json.loads(entry.old_value or entry.new_value or "{}")
                set_project_sammel_years(
                    db, project.id, old["finve_id"], old.get("years") or [], user=user, action="REVERT"
                )
        except FinveLinkError as exc:
            raise RevertError(409, str(exc)) from exc
        db.refresh(project)
        return project

    if field_name not in ProjectUpdate.model_fields.keys():
        raise RevertError(400, f"Unknown field: {field_name}")

    # Parse stored JSON value back to the original Python type
    target_value = json.loads(entry.old_value) if entry.old_value is not None else None
    try:
        validate_geometry_ownership(db, project, {field_name: target_value})
    except GeometryOwnershipError as exc:
        raise RevertError(400, str(exc)) from exc

    # Record the revert action in the changelog before applying it
    create_changelog_for_patch(
        db, project, {field_name: target_value}, user.id, user.username, action="REVERT"
    )
    return update_project(db, project.id, {field_name: target_value}, project=project)
