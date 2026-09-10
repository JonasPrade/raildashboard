from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from dashboard_backend.models.base import Base

# ``electoral_data.mandate_won`` values used by abgeordnetenwatch.
MANDATE_TYPE_CONSTITUENCY = "constituency"
MANDATE_TYPE_LIST = "list"
MANDATE_TYPE_MOVED_UP = "moved_up"


class Mandate(Base):
    """One seat in one legislative period.

    Two degrees of responsibility for a constituency, deliberately kept apart:

    * ``is_direct_mandate`` — won the constituency (``mandate_won == "constituency"``).
    * everything else with a ``constituency_id`` — ran here and entered over the
      state list. abgeordnetenwatch has no *Betreuungswahlkreis*; the candidacy is
      the best available substitute and a weaker statement, so the UI must keep
      showing it as one.

    ``is_direct_mandate`` is stored rather than derived per query: the distinction
    carries the whole feature and is set exactly once, by the importer.
    """

    __tablename__ = "mandate"

    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, nullable=False, unique=True, index=True)
    politician_id = Column(
        Integer, ForeignKey("politician.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parliament_period_id = Column(
        Integer, ForeignKey("parliament_period.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Null for mandates without any constituency reference at all.
    constituency_id = Column(
        Integer, ForeignKey("constituency.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mandate_type = Column(String(30), nullable=True)
    is_direct_mandate = Column(Boolean, nullable=False, default=False, server_default="false")
    fraction_label = Column(String(200), nullable=True, index=True)
    info = Column(Text, nullable=True)

    politician = relationship("Politician", backref="mandates")
    constituency = relationship("Constituency", backref="mandates")
    committee_memberships = relationship(
        "CommitteeMembership", back_populates="mandate", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_mandate_period_constituency", "parliament_period_id", "constituency_id"),
    )

    def __repr__(self) -> str:
        return f"<Mandate(external_id={self.external_id}, direct={self.is_direct_mandate})>"
