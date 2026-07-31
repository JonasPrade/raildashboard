# python
from sqlalchemy.orm import Session, selectinload

from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup


def _with_projects():
    """Loader options for the read endpoints, which serialise the full project list.

    Without these, ``ProjectGroupSchema`` triggers one lazy SELECT per group for
    ``projects`` **and** one per project for ``ProjectSchema.project_groups`` —
    the map page therefore paid ``1 + groups + groups*projects`` queries. Two
    ``selectinload`` levels collapse that to three queries in total.

    Drafts are excluded in SQL (the schema validator drops them afterwards
    anyway), so draft rows are never loaded or serialised.
    """
    return (
        selectinload(ProjectGroup.projects.and_(Project.is_draft.is_(False)))
        .selectinload(Project.project_groups),
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
