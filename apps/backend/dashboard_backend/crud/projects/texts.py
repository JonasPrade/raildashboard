from __future__ import annotations

import time

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from dashboard_backend.models.associations.text_to_project import TextToProject
from dashboard_backend.models.projects.project_text import ProjectText
from dashboard_backend.models.projects.project_text_category import ProjectTextCategory
from dashboard_backend.models.projects.project_text_type import ProjectTextType

DEFAULT_CATEGORY_NAME = "Info"


def get_texts_for_project(
    db: Session, project_id: int, include_internal: bool = True
) -> list[ProjectText]:
    """Texts linked to a project; ``include_internal=False`` keeps public ones only."""
    query = (
        db.query(ProjectText)
        .join(TextToProject, TextToProject.text_id == ProjectText.id)
        .filter(TextToProject.project_id == project_id)
        .options(selectinload(ProjectText.attachments), selectinload(ProjectText.category))
    )
    if not include_internal:
        query = query.filter(ProjectText.is_public.is_(True))
    return query.all()


def get_text_types(db: Session) -> list[ProjectTextType]:
    return db.query(ProjectTextType).all()


def create_text_type(db: Session, name: str) -> ProjectTextType:
    text_type = ProjectTextType(name=name)
    db.add(text_type)
    db.commit()
    db.refresh(text_type)
    return text_type


def get_text_categories(db: Session) -> list[ProjectTextCategory]:
    return db.query(ProjectTextCategory).order_by(ProjectTextCategory.id).all()


def get_text_category(db: Session, category_id: int) -> ProjectTextCategory | None:
    return db.query(ProjectTextCategory).filter(ProjectTextCategory.id == category_id).first()


def get_text_category_by_name(db: Session, name: str) -> ProjectTextCategory | None:
    return (
        db.query(ProjectTextCategory)
        .filter(func.lower(ProjectTextCategory.name) == name.strip().lower())
        .first()
    )


def get_default_text_category(db: Session) -> ProjectTextCategory | None:
    """„Info“, or the oldest category when „Info“ was removed by hand."""
    return get_text_category_by_name(db, DEFAULT_CATEGORY_NAME) or (
        db.query(ProjectTextCategory).order_by(ProjectTextCategory.id).first()
    )


def create_text_category(db: Session, name: str, style: str) -> ProjectTextCategory:
    category = ProjectTextCategory(name=name.strip(), style=style)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def create_text_for_project(db: Session, project_id: int, data: dict) -> ProjectText:
    now = int(time.time())
    data = dict(data)
    if data.get("category_id") is None:
        default = get_default_text_category(db)
        data["category_id"] = default.id if default else None
    text = ProjectText(**data, created_at=now, updated_at=now)
    db.add(text)
    db.flush()
    association = TextToProject(project_id=project_id, text_id=text.id)
    db.add(association)
    db.commit()
    db.refresh(text)
    return text


def update_project_text(db: Session, text_id: int, update_data: dict) -> ProjectText | None:
    text = db.query(ProjectText).filter(ProjectText.id == text_id).first()
    if not text:
        return None
    for key, value in update_data.items():
        setattr(text, key, value)
    text.updated_at = int(time.time())
    db.commit()
    db.refresh(text)
    return text


def delete_project_text(db: Session, text_id: int) -> bool:
    text = db.query(ProjectText).filter(ProjectText.id == text_id).first()
    if not text:
        return False
    db.delete(text)
    db.commit()
    return True
