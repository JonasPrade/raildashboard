from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base


class FinveChangeLog(Base):
    """Change history for Finve records, independent of projects."""

    __tablename__ = "finve_change_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    finve_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("finve.id", ondelete="SET NULL"), nullable=True, index=True
    )
    haushalt_year: Mapped[int] = mapped_column(Integer, nullable=False)
    username_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # CREATE / UPDATE / IMPORT

    entries: Mapped[list[FinveChangeLogEntry]] = relationship(
        "FinveChangeLogEntry", back_populates="changelog", cascade="all, delete-orphan"
    )


class FinveChangeLogEntry(Base):
    """Per-field change record linked to a FinveChangeLog entry."""

    __tablename__ = "finve_change_log_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    changelog_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("finve_change_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    changelog: Mapped[FinveChangeLog] = relationship(
        "FinveChangeLog", back_populates="entries"
    )
