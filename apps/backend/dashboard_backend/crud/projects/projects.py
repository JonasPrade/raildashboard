import json
from typing import Any, Callable, List, Optional

from sqlalchemy.orm import Session, selectinload

from dashboard_backend.models.projects import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.services.constituency_matching import recompute_links_for_project_ids


def get_projects(db: Session):
    """Gibt alle finalisierten Projekte zurück (Entwürfe ausgeblendet)."""
    # ProjectSchema serializes project_groups — eager-load to avoid 1+N queries.
    return (
        db.query(Project)
        .options(selectinload(Project.project_groups))
        .filter(Project.is_draft.is_(False))
        .all()
    )


def get_draft_projects(db: Session):
    """Gibt alle noch nicht finalisierten Projekte (Entwürfe) zurück."""
    return (
        db.query(Project)
        .options(selectinload(Project.project_groups))
        .filter(Project.is_draft.is_(True))
        .all()
    )


def get_project_options(db: Session) -> List[Any]:
    """Minimal (id, name, project_number, superior_project_id) rows for pickers.

    Selects only the four columns instead of whole ORM entities: the dropdowns
    that use this would otherwise transfer every project's
    ``geojson_representation``, which dwarfs the rest of the row.
    """
    return (
        db.query(
            Project.id,
            Project.name,
            Project.project_number,
            Project.superior_project_id,
        )
        .filter(Project.is_draft.is_(False))
        .order_by(Project.name)
        .all()
    )


def get_subprojects(db: Session, project_id: int):
    """Direct children of *project_id* (drafts excluded), ordered by name.

    The detail page needs the children in full (map geometry + summary cards).
    Fetching them by parent beats loading every project and filtering client-side.
    """
    return (
        db.query(Project)
        .options(selectinload(Project.project_groups))
        .filter(
            Project.superior_project_id == project_id,
            Project.is_draft.is_(False),
        )
        .order_by(Project.name)
        .all()
    )


def get_project_by_id(db: Session, project_id: int):
    """Gibt ein einzelnes Projekt anhand der ID zurück (auch Entwürfe)."""
    return db.query(Project).filter(Project.id == project_id).first()


def _extract_features(geojson_str: Optional[str]) -> List[Any]:
    """Parse a geojson_representation string and return a flat list of GeoJSON Features."""
    if not geojson_str:
        return []
    try:
        obj = json.loads(geojson_str)
    except (json.JSONDecodeError, TypeError):
        return []

    obj_type = obj.get("type") if isinstance(obj, dict) else None
    if obj_type == "FeatureCollection":
        return [f for f in obj.get("features", []) if isinstance(f, dict)]
    if obj_type == "Feature":
        return [obj]
    # Raw geometry — wrap in a Feature
    if obj_type in (
        "Point", "MultiPoint", "LineString", "MultiLineString",
        "Polygon", "MultiPolygon", "GeometryCollection",
    ):
        return [{"type": "Feature", "geometry": obj, "properties": {}}]
    return []


def has_subprojects(db: Session, project_id: int) -> bool:
    """True if at least one project has *project_id* as its superior project."""
    return (
        db.query(Project.id)
        .filter(Project.superior_project_id == project_id)
        .first()
        is not None
    )


def recompute_geojson_for_parent(db: Session, parent_id: Optional[int]) -> None:
    """Recompute and persist the geojson_representation of *parent_id* and its ancestors.

    At each level, all direct children's geojson_representations are flattened into a
    FeatureCollection and stored on the parent, then the walk continues upwards. The
    walk stops at the root — `_seen` guards against a corrupt cyclic chain.

    A parent with `geojson_from_subprojects = False` owns its geometry: it is left
    untouched and the walk stops there, because an unchanged geometry cannot change what
    its own ancestors aggregate.
    """
    seen: set[int] = set()
    touched: List[int] = []
    current_id = parent_id

    while current_id is not None and current_id not in seen:
        seen.add(current_id)
        parent = get_project_by_id(db, current_id)
        if parent is None:
            break
        if not parent.geojson_from_subprojects:
            break

        children = (
            db.query(Project)
            .filter(Project.superior_project_id == parent.id)
            .all()
        )

        features: List[Any] = []
        for child in children:
            features.extend(_extract_features(child.geojson_representation))

        if features:
            parent.geojson_representation = json.dumps(
                {"type": "FeatureCollection", "features": features}
            )
        else:
            parent.geojson_representation = None

        db.commit()
        db.refresh(parent)
        touched.append(parent.id)

        # Continue upwards to update grandparent, great-grandparent, …
        current_id = parent.superior_project_id

    # The aggregated geometry just changed at every level walked — the
    # constituency links of those projects are stale in exactly the same way.
    recompute_links_for_project_ids(db, touched)


def recompute_parent_geojson(db: Session, project: Project) -> None:
    """Recompute the geojson_representation of every ancestor of *project*."""
    recompute_geojson_for_parent(db, project.superior_project_id)


class ProjectHierarchyError(ValueError):
    """Raised when a superior-project assignment would produce an invalid hierarchy."""


def ancestor_ids(project_id: int, parent_of: Callable[[int], Optional[int]]) -> List[int]:
    """Ids of all ancestors of *project_id*, nearest parent first.

    *parent_of* maps a project id to its superior_project_id. A corrupt cyclic chain
    terminates the walk instead of looping forever.
    """
    ancestors: List[int] = []
    seen = {project_id}

    current_id = parent_of(project_id)
    while current_id is not None and current_id not in seen:
        ancestors.append(current_id)
        seen.add(current_id)
        current_id = parent_of(current_id)

    return ancestors


def check_superior_project(
    project_id: Optional[int],
    superior_project_id: Optional[int],
    *,
    exists: Callable[[int], bool],
    parent_of: Callable[[int], Optional[int]],
) -> None:
    """Pure hierarchy rules — the data is supplied via *exists* / *parent_of*.

    Rejects unknown parents, self-references and any parent that already sits below the
    project in the tree (which would create a cycle). *project_id* is None while the
    project is still being created — only the existence check applies then.

    Raises ProjectHierarchyError with a user-facing (German) message.
    """
    if superior_project_id is None:
        return

    if project_id is not None and superior_project_id == project_id:
        raise ProjectHierarchyError(
            "Ein Projekt kann nicht sich selbst als übergeordnetes Projekt haben."
        )

    if not exists(superior_project_id):
        raise ProjectHierarchyError(
            f"Das übergeordnete Projekt mit der ID {superior_project_id} existiert nicht."
        )

    if project_id is not None and project_id in ancestor_ids(superior_project_id, parent_of):
        raise ProjectHierarchyError(
            "Das gewählte Projekt ist bereits ein Unterprojekt dieses Projekts — "
            "das würde einen Zyklus erzeugen."
        )


def validate_superior_project(
    db: Session, project_id: Optional[int], superior_project_id: Optional[int]
) -> None:
    """Database-backed wrapper around check_superior_project()."""
    check_superior_project(
        project_id,
        superior_project_id,
        exists=lambda pid: get_project_by_id(db, pid) is not None,
        parent_of=lambda pid: db.query(Project.superior_project_id)
        .filter(Project.id == pid)
        .scalar(),
    )


def create_project(db: Session, data: dict) -> Project:
    """Create a new project. `project_group_ids` is handled separately."""
    data = dict(data)
    group_ids = data.pop("project_group_ids", None)

    project = Project(**data)
    if group_ids:
        project.project_groups = (
            db.query(ProjectGroup).filter(ProjectGroup.id.in_(group_ids)).all()
        )
    db.add(project)
    db.commit()
    db.refresh(project)
    if project.geojson_representation:
        recompute_links_for_project_ids(db, [project.id])
    return project


def update_project(db: Session, project_id: int, update_data: dict, project: Project | None = None):
    """Aktualisiert ein bestehendes Projekt.

    Callers that already loaded the project (e.g. for changelog recording)
    can pass it via *project* to avoid a second identical SELECT.
    """
    if project is None:
        project = get_project_by_id(db, project_id)
    if not project:
        return None

    update_data = dict(update_data)

    # NOT NULL toggle — an explicit null in a PATCH payload can only mean "unchanged".
    if update_data.get("geojson_from_subprojects", False) is None:
        del update_data["geojson_from_subprojects"]

    # Handle many-to-many group assignment separately
    group_ids = update_data.pop("project_group_ids", None)
    if group_ids is not None:
        project.project_groups = db.query(ProjectGroup).filter(ProjectGroup.id.in_(group_ids)).all()

    geojson_changed = "geojson_representation" in update_data

    previous_superior_id = project.superior_project_id
    superior_changed = (
        "superior_project_id" in update_data
        and update_data["superior_project_id"] != previous_superior_id
    )

    # Switching back to "aggregate from subprojects" makes the project's own geometry stale.
    switched_to_aggregated = (
        update_data.get("geojson_from_subprojects") is True
        and not project.geojson_from_subprojects
    )

    for key, value in update_data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)

    if geojson_changed:
        # The project's own geometry changed — its constituency links follow. The
        # ancestors are handled by the cascade below, which recomputes theirs.
        recompute_links_for_project_ids(db, [project.id])

    if switched_to_aggregated and has_subprojects(db, project.id):
        # Rebuild the project's own geometry from its subprojects. The walk starts at the
        # project itself and continues upwards, so the ancestor chain is covered too.
        recompute_geojson_for_parent(db, project.id)
    elif geojson_changed or superior_changed:
        # Cascade geometry upwards when the geometry changed — or when the project moved
        # in the tree, in which case both the old and the new parent chain are stale.
        recompute_parent_geojson(db, project)

    if superior_changed:
        recompute_geojson_for_parent(db, previous_superior_id)

    return project


def finalize_project(db: Session, project_id: int):
    """Mark a draft project as finalized (no longer a draft)."""
    project = get_project_by_id(db, project_id)
    if not project:
        return None
    project.is_draft = False
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int) -> bool:
    """Delete a project by id. Returns True if a project was deleted."""
    project = get_project_by_id(db, project_id)
    if not project:
        return False
    db.delete(project)
    db.commit()
    return True