from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
)
from sqlalchemy.sql import func

from dashboard_backend.models.base import Base


class ProjectMapGeometry(Base):
    """Map facts derived from a project's line geometry.

    One row per project that is drawn on the map with at least one line (not a
    draft, not archived). The bounding box is the prefilter for the overlap
    search, the hash lets an unchanged geometry skip it, and ``lane`` is the
    project's stored lane for parallel drawing
    (docs/features/feature-map-overlapping-geometries.md → B1).
    """

    __tablename__ = "project_map_geometry"

    project_id = Column(
        Integer,
        ForeignKey("project.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    min_lon = Column(Float, nullable=False)
    min_lat = Column(Float, nullable=False)
    max_lon = Column(Float, nullable=False)
    max_lat = Column(Float, nullable=False)
    line_km = Column(Float, nullable=False)
    geometry_hash = Column(String(40), nullable=False)
    lane = Column(SmallInteger, nullable=False, default=0)
    computed_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_project_map_geometry_bbox", "min_lon", "max_lon", "min_lat", "max_lat"),
    )


class ProjectOverlap(Base):
    """Two projects whose lines run along the same track.

    Materialised like ``project_to_constituency``: recomputed when either
    geometry changes, never on page load. Stored once per pair with
    ``project_a_id < project_b_id``.
    """

    __tablename__ = "project_overlap"

    project_a_id = Column(
        Integer,
        ForeignKey("project.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    project_b_id = Column(
        Integer,
        ForeignKey("project.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    # Length both lines share, in km.
    shared_km = Column(Float, nullable=False)
    # Shared length as a share of each project's own line length (0..1).
    share_a = Column(Float, nullable=False)
    share_b = Column(Float, nullable=False)
    computed_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("project_a_id < project_b_id", name="ck_project_overlap_order"),
        # b → pairs; the primary key leads with project_a_id.
        Index("ix_project_overlap_project_b_id", "project_b_id"),
    )
