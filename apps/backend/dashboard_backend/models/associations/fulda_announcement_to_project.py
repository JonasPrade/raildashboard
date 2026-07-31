"""m:n link between Fulda-Runde announcements and projects (#46).

A single Fulda-Runde line (e.g. "ABS Augsburg–Donauwörth") can map to several
dashboard projects/subprojects, mirroring the VIB importer's ``vib_entry_project``
table. Editor-confirmed links drive the derived FULDA_RUNDE observations.
"""

from sqlalchemy import Column, ForeignKey, Index, Integer, Table

from dashboard_backend.models.base import Base

fulda_announcement_to_project = Table(
    "fulda_announcement_to_project",
    Base.metadata,
    Column(
        "fulda_announcement_id",
        Integer,
        ForeignKey("fulda_announcement.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "project_id",
        Integer,
        ForeignKey("project.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # The derived-observation sync filters by project_id; the composite primary
    # key leads with fulda_announcement_id and cannot serve that lookup.
    Index("ix_fulda_announcement_to_project_project_id", "project_id"),
)
