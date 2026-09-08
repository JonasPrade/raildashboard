from geoalchemy2 import Geometry
from sqlalchemy import Column, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from dashboard_backend.models.base import Base
from dashboard_backend.models.parliament._geometry import SqliteGeometry

CONSTITUENCY_SRID = 4326


class Constituency(Base):
    """A Bundestag constituency (Wahlkreis) with its official outline.

    The geometry comes from the Bundeswahlleiterin (© GeoBasis-DE / BKG) and is
    the fixed side of the feature: it changes once per election, while the people
    sitting in it change constantly.
    """

    __tablename__ = "constituency"

    id = Column(Integer, primary_key=True)
    parliament_period_id = Column(
        Integer,
        ForeignKey("parliament_period.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 1..299 — the key both data sources agree on.
    number = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)
    state = Column(String(100), nullable=True)  # Bundesland
    election_year = Column(Integer, nullable=True)
    # abgeordnetenwatch constituency id (null until the mandate import ran)
    external_id = Column(Integer, nullable=True, index=True)
    geometry_source = Column(String(300), nullable=True)

    _geom_sqlite = SqliteGeometry(CONSTITUENCY_SRID)
    geom = Column(
        _geom_sqlite.with_variant(
            Geometry(geometry_type="MULTIPOLYGON", srid=CONSTITUENCY_SRID), "postgresql"
        ),
        nullable=True,
    )

    period = relationship("ParliamentPeriod", backref="constituencies")

    __table_args__ = (
        UniqueConstraint("parliament_period_id", "number", name="uq_constituency_period_number"),
        Index("ix_constituency_number", "number"),
    )

    def __repr__(self) -> str:
        return f"<Constituency(number={self.number}, name={self.name!r})>"
