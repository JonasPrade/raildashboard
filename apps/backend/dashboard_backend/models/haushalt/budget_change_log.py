from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base


class BudgetChangeLog(Base):
    """Change history for Budget records, independent of projects."""

    __tablename__ = "budget_change_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    budget_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("budgets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    haushalt_year: Mapped[int] = mapped_column(Integer, nullable=False)
    username_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # CREATE / UPDATE / IMPORT

    entries: Mapped[list[BudgetChangeLogEntry]] = relationship(
        "BudgetChangeLogEntry", back_populates="changelog", cascade="all, delete-orphan"
    )


class BudgetChangeLogEntry(Base):
    """Per-field change record linked to a BudgetChangeLog entry."""

    __tablename__ = "budget_change_log_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    changelog_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("budget_change_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    changelog: Mapped[BudgetChangeLog] = relationship(
        "BudgetChangeLog", back_populates="entries"
    )
