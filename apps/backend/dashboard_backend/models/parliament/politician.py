from sqlalchemy import Column, Integer, String

from dashboard_backend.models.base import Base


class Politician(Base):
    """A person. Separate from :class:`Mandate` because one person can hold
    several mandates over time (a later period, or a seat taken over as a
    substitute); party, faction and committee role belong to the mandate.
    """

    __tablename__ = "politician"

    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, nullable=False, unique=True, index=True)
    label = Column(String(300), nullable=False)  # display name as delivered
    first_name = Column(String(150), nullable=True)
    last_name = Column(String(150), nullable=True, index=True)
    party_label = Column(String(150), nullable=True)
    abgeordnetenwatch_url = Column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<Politician(external_id={self.external_id}, label={self.label!r})>"
