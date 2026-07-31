from sqlalchemy import Column, ForeignKey, Index, Integer, Table

from dashboard_backend.models.base import Base

vib_entry_project = Table(
    "vib_entry_project",
    Base.metadata,
    Column(
        "vib_entry_id",
        Integer,
        ForeignKey("vib_entry.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "project_id",
        Integer,
        ForeignKey("project.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # The derived-observation sync and the forecast both filter by project_id;
    # the composite primary key leads with vib_entry_id and cannot serve them.
    Index("ix_vib_entry_project_project_id", "project_id"),
)
