from __future__ import annotations

from sqlalchemy.orm import Session

from dashboard_backend.models.projects.bvwp_project_data import BvwpProjectData


def get_bvwp_data(db: Session, project_id: int) -> BvwpProjectData | None:
    return db.query(BvwpProjectData).filter(BvwpProjectData.project_id == project_id).first()
