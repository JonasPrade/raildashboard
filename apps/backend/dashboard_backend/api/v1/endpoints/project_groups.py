from fastapi import Depends, HTTPException, Query, Request
from pydantic import BaseModel, TypeAdapter
from typing import Optional
from sqlalchemy.orm import Session
from dashboard_backend.crud.projects.project_groups import (
    get_project_groups,
    get_project_group_by_id,
    get_project_group_ref,
    get_group_geometry_sources,
    get_project_group_by_short_name,
    create_project_group,
    update_project_group,
    delete_project_group,
)
from dashboard_backend.database import get_db
from dashboard_backend.schemas.projects import (
    ProjectGroupSchema,
    ProjectGroupCreate,
    ProjectGroupGeometriesSchema,
)
from dashboard_backend.core.http_cache import etag_json_response
from dashboard_backend.services.geometry_simplify import TOLERANCE_DEG, simplify_geojson_text
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.core.security import require_permission

router = AuthRouter()

_group_list_adapter = TypeAdapter(list[ProjectGroupSchema])
_group_adapter = TypeAdapter(ProjectGroupSchema)
_geometries_adapter = TypeAdapter(ProjectGroupGeometriesSchema)


class ProjectGroupUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    description: Optional[str] = None
    public: Optional[bool] = None
    color: Optional[str] = None
    plot_only_superior_projects: Optional[bool] = None
    is_visible: Optional[bool] = None
    is_default_selected: Optional[bool] = None


@router.get("/", response_model=list[ProjectGroupSchema])
def read_project_groups(request: Request, db: Session = Depends(get_db)):
    """All groups with their projects as slim items (no geometry).

    Geometry comes from ``GET /{group_id}/geometries``. The response carries an
    ETag; an unchanged list is answered with 304.
    """
    return etag_json_response(request, get_project_groups(db), _group_list_adapter)


@router.get("/{group_id}", response_model=ProjectGroupSchema)
def read_project_group(group_id: int, request: Request, db: Session = Depends(get_db)):
    group = get_project_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="ProjectGroup not found")
    return etag_json_response(request, group, _group_adapter)


@router.get("/{group_id}/geometries", response_model=ProjectGroupGeometriesSchema)
def read_project_group_geometries(
    group_id: int,
    request: Request,
    only_superior: bool = Query(
        True,
        description="Skip subprojects — their geometry is already part of their parent's.",
    ),
    db: Session = Depends(get_db),
):
    """Simplified overview-map geometries of a group's projects, keyed by project id.

    Lines are simplified (~20 m tolerance) and coordinates rounded to ~1 m;
    projects without geometry are omitted. The exact geometry stays on
    ``GET /projects/{id}``. The response carries an ETag.
    """
    if not get_project_group_ref(db, group_id):
        raise HTTPException(status_code=404, detail="ProjectGroup not found")

    geometries = {}
    for project_id, geojson_text in get_group_geometry_sources(db, group_id, only_superior):
        simplified = simplify_geojson_text(geojson_text)
        if simplified is not None:
            geometries[project_id] = simplified

    payload = ProjectGroupGeometriesSchema(
        group_id=group_id,
        only_superior=only_superior,
        tolerance=TOLERANCE_DEG,
        geometries=geometries,
    )
    return etag_json_response(request, payload, _geometries_adapter)


@router.post("/", response_model=ProjectGroupSchema, status_code=201)
def create_project_group_endpoint(
    body: ProjectGroupCreate,
    _: None = Depends(require_permission("projectgroup.create")),
    db: Session = Depends(get_db),
):
    if get_project_group_by_short_name(db, body.short_name):
        raise HTTPException(status_code=409, detail="short_name already in use")
    return create_project_group(db, body.model_dump())


@router.patch("/{group_id}", response_model=ProjectGroupSchema)
def patch_project_group(
    group_id: int,
    body: ProjectGroupUpdate,
    _: None = Depends(require_permission("projectgroup.edit")),
    db: Session = Depends(get_db),
):
    updates = body.model_dump(exclude_unset=True)

    new_short_name = updates.get("short_name")
    if new_short_name is not None:
        existing = get_project_group_by_short_name(db, new_short_name)
        if existing and existing.id != group_id:
            raise HTTPException(status_code=409, detail="short_name already in use")

    group = update_project_group(db, group_id, updates)
    if not group:
        raise HTTPException(status_code=404, detail="ProjectGroup not found")
    return group


@router.delete("/{group_id}", status_code=204)
def delete_project_group_endpoint(
    group_id: int,
    _: None = Depends(require_permission("projectgroup.edit")),
    db: Session = Depends(get_db),
):
    group = delete_project_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="ProjectGroup not found")
    return None
