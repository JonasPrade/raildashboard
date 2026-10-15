from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dashboard_backend.models.base import Base


class InfraplanParseResult(Base):
    """Draft of one uploaded Infraplan PDF (pattern: ``haushalts_parse_result``).

    The uploaded PDF is kept per draft (``pdf_path``, a file name inside
    ``settings.infraplan_pdf_dir``) so the draft can be re-parsed and page
    images can be rendered for the KPI review. ``warnings_json`` holds the
    plausibility findings (gaps/duplicates in the running numbers); a draft
    with warnings must not be confirmed without ``force``.
    """

    __tablename__ = "infraplan_parse_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )  # PENDING / RUNNING / SUCCESS / FAILURE
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    warnings_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kpi_pages_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    username_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_by_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
