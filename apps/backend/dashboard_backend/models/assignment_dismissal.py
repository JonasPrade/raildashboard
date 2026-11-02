"""Permanently ignored open assignment (feature-unassigned-assignments.md →
„Dauerhaft ignorieren“).

One row hides one imported record from „Offene Zuordnungen“ — a FinVe, a VIB
entry, a GVFG Vorhaben or an Infraplan row that will never get a project (e.g.
a bus or tram Vorhaben, a pure equipment line). ``kind`` names the source table,
``entry_id`` the row in it; there is no foreign key because the four sources
are different tables. A row whose record is gone (report deleted) is harmless
and is skipped when the ignored list is read.

Ignoring never touches the record itself: links, confirmation and planning
state stay as they are. Undoing it deletes the row.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from dashboard_backend.models.base import Base

KIND_FINVE = "finve"
KIND_VIB = "vib"
KIND_GVFG = "gvfg"
KIND_INFRAPLAN = "infraplan"
KINDS = (KIND_FINVE, KIND_VIB, KIND_GVFG, KIND_INFRAPLAN)


class AssignmentDismissal(Base):
    __tablename__ = "assignment_dismissal"
    __table_args__ = (
        UniqueConstraint("kind", "entry_id", name="uq_assignment_dismissal_kind_entry"),
    )

    id = Column(Integer, primary_key=True)
    kind = Column(String(20), nullable=False)
    entry_id = Column(Integer, nullable=False)
    note = Column(Text, nullable=True)
    dismissed_at = Column(DateTime, nullable=False, server_default=func.now())
    dismissed_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    dismissed_by = relationship("User", lazy="select")

    @property
    def dismissed_by_username(self) -> str | None:
        return self.dismissed_by.username if self.dismissed_by is not None else None
