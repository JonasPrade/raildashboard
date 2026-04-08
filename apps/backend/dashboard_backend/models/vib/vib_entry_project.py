from sqlalchemy import Column, ForeignKey, Integer, Table

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
)
