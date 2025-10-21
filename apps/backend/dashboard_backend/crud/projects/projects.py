# dashboard_backend/crud/projects.py
from sqlalchemy.orm import Session
from dashboard_backend.models.projects import Project

def get_projects(db: Session):
    """Gibt alle Projekte zurück."""
    return db.query(Project).all()

def get_project_by_id(db: Session, project_id: int):
    """Gibt ein einzelnes Projekt anhand der ID zurück."""
    return db.query(Project).filter(Project.id == project_id).first()

# def create_project(db: Session, project: Project):
#     """Erstellt ein neues Projekt."""
#     db.add(project)
#     db.commit()
#     db.refresh(project)
#     return project

def update_project(db: Session, project_id: int, update_data: dict):
    """Aktualisiert ein bestehendes Projekt."""
    project = get_project_by_id(db, project_id)
    if not project:
        return None
    for key, value in update_data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project

# def delete_project(db: Session, project_id: int):
#     """Löscht ein Projekt anhand der ID."""
#     project = get_project_by_id(db, project_id)
#     if not project:
#         return None
#     db.delete(project)
#     db.commit()
#     return project