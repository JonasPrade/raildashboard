from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base


class ChangeLog(Base):
    """High-level record of a data modification event (what, when, by whom)."""

    __tablename__ = "change_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    username_snapshot: Mapped[str | None] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False, default="PATCH")

    entries: Mapped[list[ChangeLogEntry]] = relationship(
        "ChangeLogEntry", back_populates="changelog", cascade="all, delete-orphan"
    )


class ChangeLogEntry(Base):
    """Per-field change record linked to a ChangeLog entry."""

    __tablename__ = "change_log_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    changelog_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("change_log.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    changelog: Mapped[ChangeLog] = relationship("ChangeLog", back_populates="entries")


class TextChangeLog(Base):
    """High-level record of a project-text modification event (what, when, by whom)."""

    __tablename__ = "text_change_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # SET NULL so history survives after the text is deleted
    text_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("project_text.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # SET NULL so history survives after the project is deleted
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("project.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    username_snapshot: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Preserves the text header even after the text row is deleted
    text_header_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False, default="PATCH")

    entries: Mapped[list[TextChangeLogEntry]] = relationship(
        "TextChangeLogEntry", back_populates="text_changelog", cascade="all, delete-orphan"
    )


class TextChangeLogEntry(Base):
    """Per-field change record linked to a TextChangeLog entry."""

    __tablename__ = "text_change_log_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    text_changelog_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("text_change_log.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    text_changelog: Mapped[TextChangeLog] = relationship("TextChangeLog", back_populates="entries")
