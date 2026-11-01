from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from dashboard_backend.models.base import Base

IMPORT_KIND_POLITICIANS = "politicians"
IMPORT_KIND_CONSTITUENCIES = "constituencies"
IMPORT_KIND_LINKS = "links"

IMPORT_STATUS_RUNNING = "running"
IMPORT_STATUS_SUCCESS = "success"
IMPORT_STATUS_ERROR = "error"


class ParliamentImportRun(Base):
    """One import run, shown in the UI as the "Abrufstand".

    The people data ages much faster than the geometries — substitutes moving up
    and committee reshuffles shift the assignment without anything being wrong
    about the outlines. The UI therefore has to say when the data was last
    fetched, per kind of run.
    """

    __tablename__ = "parliament_import_run"

    id = Column(Integer, primary_key=True)
    kind = Column(String(30), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=IMPORT_STATUS_RUNNING)
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    parliament_period_id = Column(
        Integer, ForeignKey("parliament_period.id", ondelete="SET NULL"), nullable=True
    )
    # Free-form counters (mandates, constituencies, direct mandates, committee
    # members, ...) so a new metric does not need a migration.
    stats = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    # NULL = started by the scheduler (feature-routine-abrufe.md); the UI shows
    # „Zeitplan“ instead of a user name.
    triggered_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    triggered_by = relationship("User", lazy="select")

    @property
    def triggered_by_username(self) -> str | None:
        return self.triggered_by.username if self.triggered_by is not None else None
