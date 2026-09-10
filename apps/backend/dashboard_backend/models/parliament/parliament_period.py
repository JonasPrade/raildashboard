from sqlalchemy import Boolean, Column, Date, Integer, String

from dashboard_backend.models.base import Base


class ParliamentPeriod(Base):
    """One legislative period of one parliament (currently only the Bundestag).

    Kept as its own table so that later periods — and, one day, Landtage — are a
    row rather than a schema change. Everything person-related hangs off the
    mandate, which points here.
    """

    __tablename__ = "parliament_period"

    id = Column(Integer, primary_key=True)
    # abgeordnetenwatch parliament-period id (161 = "Bundestag 2025 - 2029")
    external_id = Column(Integer, nullable=False, unique=True, index=True)
    label = Column(String(200), nullable=False)
    parliament_label = Column(String(200), nullable=True)
    # abgeordnetenwatch parliament id (5 = Bundestag)
    parliament_external_id = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    # Exactly one period is the one the UI reads; set by the importer.
    is_current = Column(Boolean, nullable=False, default=False, server_default="false")

    def __repr__(self) -> str:
        return f"<ParliamentPeriod(external_id={self.external_id}, label={self.label!r})>"
