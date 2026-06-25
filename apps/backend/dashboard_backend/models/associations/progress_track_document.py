"""Association: documents linked behind a project's PF / parliamentary track.

Reuses the existing ``Document`` model (same idea as ``document_to_project``)
but scopes the link to a single :class:`ObservationTrack` (here only PF/PARL).
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from dashboard_backend.models.base import Base


class ProgressTrackDocument(Base):
    __tablename__ = "progress_track_document"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    track = Column(String(10), nullable=False)  # ObservationTrack: PF | PARL
    document_id = Column(
        Integer, ForeignKey("document.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id", "track", "document_id", name="uq_progress_track_document"
        ),
    )
