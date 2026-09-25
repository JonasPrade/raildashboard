# python
from sqlalchemy.orm import Session, selectinload

from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.schemas.projects.project_schema import (
    PROJECT_FLAG_FIELDS,
    PROJECT_LIST_ITEM_COLUMNS,
)


def _with_projects():
    """Loader options for the read endpoints, which serialise the slim project list.

    One ``selectinload`` keeps it at two queries in total (groups, then all their
    projects) instead of one lazy SELECT per group. ``load_only`` restricts the
    project SELECT to the columns ``ProjectListItem`` reads — above all it keeps
    ``geojson_representation`` (the bulk of each row) out of the list path.

    Drafts are excluded in SQL (the schema validator drops them afterwards
    anyway), so draft rows are never loaded or serialised.
    """
    columns = [
        getattr(Project, name)
        for name in (*PROJECT_LIST_ITEM_COLUMNS, *PROJECT_FLAG_FIELDS)
    ]
    return (
        selectinload(ProjectGroup.projects.and_(Project.is_draft.is_(False)))
        .load_only(*columns, raiseload=True),
    )


def get_project_group_ref(db: Session, group_id: int):
    """The group row alone, without its project list.

    For paths that never serialise ``projects`` (existence checks, DELETE) —
    loading the full project list there is pure waste.
    """
    return db.query(ProjectGroup).filter(ProjectGroup.id == group_id).first()


def get_project_group_by_id(db: Session, group_id: int):
    return (
        db.query(ProjectGroup)
        .options(*_with_projects())
        .filter(ProjectGroup.id == group_id)
        .first()
    )

def get_project_groups(db: Session):
    return db.query(ProjectGroup).options(*_with_projects()).all()

def get_group_geometry_sources(db: Session, group_id: int, only_superior: bool):
    """``(project_id, geojson_representation)`` rows of a group's non-draft projects.

    Selects the two columns only. With *only_superior* the subprojects are
    skipped: a parent's geometry already contains its children's.
    """
    query = (
        db.query(Project.id, Project.geojson_representation)
        .join(Project.project_groups)
        .filter(
            ProjectGroup.id == group_id,
            Project.is_draft.is_(False),
            Project.geojson_representation.isnot(None),
        )
    )
    if only_superior:
        query = query.filter(Project.superior_project_id.is_(None))
    return query.order_by(Project.id).all()


def get_project_group_by_short_name(db: Session, short_name: str):
    return db.query(ProjectGroup).filter(ProjectGroup.short_name == short_name).first()

def update_project_group(db: Session, group_id: int, updates: dict):
    db_group = db.query(ProjectGroup).filter(ProjectGroup.id == group_id).first()
    if not db_group:
        return None
    for key, value in updates.items():
        setattr(db_group, key, value)
    db.commit()
    db.refresh(db_group)
    return db_group


def create_project_group(db: Session, data: dict):
    db_group = ProjectGroup(**data)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


def delete_project_group(db: Session, group_id: int):
    db_group = get_project_group_ref(db, group_id)
    if not db_group:
        return None
    db.delete(db_group)
    db.commit()
    return db_group
