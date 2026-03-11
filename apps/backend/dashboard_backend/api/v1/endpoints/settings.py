from fastapi import Depends
from pydantic import BaseModel
from typing import Literal
from sqlalchemy.orm import Session
from dashboard_backend.models.app_settings import AppSettings
from dashboard_backend.database import get_db
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.core.security import require_roles, UserRole

router = AuthRouter()

MapGroupMode = Literal["preconfigured", "all"]


class AppSettingsSchema(BaseModel):
    map_group_mode: MapGroupMode = "preconfigured"


class AppSettingsUpdate(BaseModel):
    map_group_mode: MapGroupMode


def _get_or_create(db: Session) -> AppSettings:
    row = db.query(AppSettings).filter(AppSettings.id == 1).first()
    if not row:
        row = AppSettings(id=1, map_group_mode="preconfigured")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/", response_model=AppSettingsSchema)
def get_settings(db: Session = Depends(get_db)):
    return _get_or_create(db)


@router.patch("/", response_model=AppSettingsSchema)
def patch_settings(
    body: AppSettingsUpdate,
    _: None = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
):
    row = _get_or_create(db)
    row.map_group_mode = body.map_group_mode
    db.commit()
    db.refresh(row)
    return row
