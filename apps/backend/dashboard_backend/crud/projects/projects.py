# dashboard_backend/crud/projects.py
import json
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from dashboard_backend.models.projects import Project
from dashboard_backend.models.projects.project_group import ProjectGroup


def get_projects(db: Session):
    """Gibt alle Projekte zurück."""
    return db.query(Project).all()


def get_project_by_id(db: Session, project_id: int):
    """Gibt ein einzelnes Projekt anhand der ID zurück."""
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


def recompute_parent_geojson(db: Session, project: Project) -> None:
    """Recompute and persist the geojson_representation of every ancestor of *project*.

    Walks the superior_project chain upwards. At each level, all direct children's
    geojson_representations are flattened into a FeatureCollection and stored on the
    parent. The recursion stops when a project has no superior project.
    """
    if project.superior_project_id is None:
        return

    parent = get_project_by_id(db, project.superior_project_id)
    if parent is None:
        return

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

    # Recurse upwards to update grandparent, great-grandparent, …
    recompute_parent_geojson(db, parent)


def create_project(db: Session, data: dict) -> Project:
    """Create a new project. `project_group_ids` is handled separately."""
    data = dict(data)
    group_ids = data.pop("project_group_ids", None)

    filtered = {k: v for k, v in data.items() if v is not None}

    project = Project(**filtered)
    if group_ids:
        project.project_groups = (
            db.query(ProjectGroup).filter(ProjectGroup.id.in_(group_ids)).all()
        )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project_id: int, update_data: dict):
    """Aktualisiert ein bestehendes Projekt."""
    project = get_project_by_id(db, project_id)
    if not project:
        return None

    update_data = dict(update_data)

    # Handle many-to-many group assignment separately
    group_ids = update_data.pop("project_group_ids", None)
    if group_ids is not None:
        project.project_groups = db.query(ProjectGroup).filter(ProjectGroup.id.in_(group_ids)).all()

    geojson_changed = "geojson_representation" in update_data

    for key, value in update_data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)

    # Cascade geometry upwards only when the geometry actually changed
    if geojson_changed:
        recompute_parent_geojson(db, project)

    return project

# def delete_project(db: Session, project_id: int):
#     """Löscht ein Projekt anhand der ID."""
#     project = get_project_by_id(db, project_id)
#     if not project:
#         return None
#     db.delete(project)
#     db.commit()
#     return project