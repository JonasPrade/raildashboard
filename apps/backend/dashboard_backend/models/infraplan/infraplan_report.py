from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base


class InfraplanReport(Base):
    """A confirmed Infraplan year (Jahrgang). Entries and KPI values hang off it,
    so deleting the year removes everything imported from it."""

    __tablename__ = "infraplan_report"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    parse_result_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("infraplan_parse_result.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    entries = relationship(
        "InfraplanEntry",
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="InfraplanEntry.report_id",
    )
    kpi_values = relationship(
        "InfraplanKpiValue",
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
