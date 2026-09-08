from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.sql import func

from dashboard_backend.models.base import Base

# How a project overlaps a constituency. A station project has no kilometres,
# only a location — the weighting has to carry both cases.
OVERLAP_KIND_LINE = "line"
OVERLAP_KIND_POINT = "point"


class ProjectToConstituency(Base):
    """Materialised intersection of a project geometry with a constituency.

    Recomputed whenever the project geometry changes (including the aggregation
    from subprojects), never on page load: the whole point of the table is that a
    ``ST_Intersection`` over the entire portfolio is not something a request pays
    for.
    """

    __tablename__ = "project_to_constituency"

    project_id = Column(
        Integer,
        ForeignKey("project.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    constituency_id = Column(
        Integer,
        ForeignKey("constituency.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    # Route kilometres of the project inside this constituency; 0.0 for a
    # point-only project.
    length_km = Column(Float, nullable=False, default=0.0)
    # Share of the whole project that falls into this constituency (0..1).
    share = Column(Float, nullable=False, default=0.0)
    overlap_kind = Column(String(10), nullable=False, default=OVERLAP_KIND_LINE)
    computed_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        # constituency → projects; the primary key leads with project_id.
        Index("ix_project_to_constituency_constituency_id", "constituency_id"),
    )
