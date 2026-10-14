"""Redirect from a deleted (merged) project id to the project it was merged into.

Written by the project merge (``crud/projects/merge.py``): the merged project row
is deleted, and this table keeps old links (``/projects/<old id>``) working.
Redirects never chain — a merge re-points the redirects that targeted the
deleted project.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from dashboard_backend.models.base import Base


class ProjectRedirect(Base):
    __tablename__ = "project_redirect"

    # No FK: the old project row no longer exists.
    old_project_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    new_project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Name of the deleted project, so the redirect stays readable.
    old_name: Mapped[str | None] = mapped_column(String, nullable=True)
    merged_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    merged_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
