from __future__ import annotations

import time

from sqlalchemy.orm import Session

from dashboard_backend.models.associations.text_to_project import TextToProject
from dashboard_backend.models.projects.project_text import ProjectText
from dashboard_backend.models.projects.project_text_type import ProjectTextType


def get_texts_for_project(db: Session, project_id: int) -> list[ProjectText]:
    return (
        db.query(ProjectText)
        .join(TextToProject, TextToProject.text_id == ProjectText.id)
        .filter(TextToProject.project_id == project_id)
        .all()
    )


def get_text_types(db: Session) -> list[ProjectTextType]:
    return db.query(ProjectTextType).all()


def create_text_type(db: Session, name: str) -> ProjectTextType:
    text_type = ProjectTextType(name=name)
    db.add(text_type)
    db.commit()
    db.refresh(text_type)
    return text_type


def create_text_for_project(db: Session, project_id: int, data: dict) -> ProjectText:
    now = int(time.time())
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
