# python
from sqlalchemy.orm import Session
from dashboard_backend.models.projects.project_group import ProjectGroup


def get_project_group_by_id(db: Session, group_id: int):
    return db.query(ProjectGroup).filter(ProjectGroup.id == group_id).first()

def get_project_groups(db: Session):
    return db.query(ProjectGroup).all()

# def create_project_group(db: Session, group: dict):
#     db_group = ProjectGroup(**group)
#     db.add(db_group)
#     db.commit()
#     db.refresh(db_group)
#     return db_group

# def update_project_group(db: Session, group_id: int, updates: dict):
#     db_group = db.query(ProjectGroup).filter(ProjectGroup.id == group_id).first()
#     if db_group:
#         for key, value in updates.items():
#             setattr(db_group, key, value)
#         db.commit()
#         db.refresh(db_group)
#     return db_group

# def delete_project_group(db: Session, group_id: int):
#     db_group = db.query(ProjectGroup).filter(ProjectGroup.id == group_id).first()
#     if db_group:
#         db.delete(db_group)
#         db.commit()
#     return db_group
