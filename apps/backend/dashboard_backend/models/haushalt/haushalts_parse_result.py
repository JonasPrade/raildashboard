from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base


class HaushaltsParseResult(Base):
    """Persisted raw output of a Haushalt PDF parse run.

    Enables inspection, error checking, and re-opening without re-upload.
    `confirmed_at` prevents double-import and shows import status in the list.
    """

    __tablename__ = "haushalts_parse_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    haushalt_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    pdf_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    parsed_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    username_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )  # PENDING / SUCCESS / FAILURE
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_by_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)

    parsed_by_user: Mapped["User"] = relationship("User")  # noqa: F821
