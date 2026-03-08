from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base


class UnmatchedBudgetRow(Base):
    """Persistent storage for PDF rows that could not be matched to a known Finve."""

    __tablename__ = "unmatched_budget_row"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    haushalt_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    raw_finve_number: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_name: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_finve_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("finve.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)

    resolved_finve: Mapped["Finve | None"] = relationship("Finve")  # noqa: F821
