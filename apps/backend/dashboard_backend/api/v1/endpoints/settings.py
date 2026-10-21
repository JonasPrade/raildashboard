from fastapi import Depends
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from dashboard_backend.models.app_settings import AppSettings
from dashboard_backend.database import get_db
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.core.security import require_permission

router = AuthRouter()

MapGroupMode = Literal["preconfigured", "all"]

LEGAL_URL_FIELDS = ("impressum_url", "datenschutz_url")
LEGAL_MARKDOWN_FIELDS = ("impressum_markdown", "datenschutz_markdown")


class AppSettingsSchema(BaseModel):
    map_group_mode: MapGroupMode = "preconfigured"
    # Legal pages: URL set → redirect outside, otherwise the Markdown is the page.
    impressum_url: Optional[str] = None
    impressum_markdown: Optional[str] = None
    datenschutz_url: Optional[str] = None
    datenschutz_markdown: Optional[str] = None


class AppSettingsUpdate(BaseModel):
    """Partial update: only the fields sent are changed; ``null`` or an empty
    string clears a legal-page field."""

    map_group_mode: Optional[MapGroupMode] = None
    impressum_url: Optional[str] = Field(default=None, max_length=500)
    impressum_markdown: Optional[str] = None
    datenschutz_url: Optional[str] = Field(default=None, max_length=500)
    datenschutz_markdown: Optional[str] = None

    @field_validator(*LEGAL_URL_FIELDS, mode="before")
    @classmethod
    def _validate_url(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("URL must be a string")
        value = value.strip()
        if not value:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("URL must start with http:// or https://")
        return value

    @field_validator(*LEGAL_MARKDOWN_FIELDS, mode="before")
    @classmethod
    def _blank_markdown_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value


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
    _: None = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
):
    row = _get_or_create(db)
    changes = body.model_dump(exclude_unset=True)
    # map_group_mode is NOT NULL: an explicit null leaves it unchanged.
    if changes.get("map_group_mode") is None:
        changes.pop("map_group_mode", None)
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row
