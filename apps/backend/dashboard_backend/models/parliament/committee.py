from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from dashboard_backend.models.base import Base

# The two committees this feature cares about: the addressees of the technical
# and of the financial argument.
COMMITTEE_KEY_TRANSPORT = "verkehr"
COMMITTEE_KEY_BUDGET = "haushalt"

COMMITTEE_LABELS: dict[str, str] = {
    COMMITTEE_KEY_TRANSPORT: "Verkehrsausschuss",
    COMMITTEE_KEY_BUDGET: "Haushaltsausschuss",
}


class Committee(Base):
    __tablename__ = "committee"

    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, nullable=False, unique=True, index=True)
    parliament_period_id = Column(
        Integer, ForeignKey("parliament_period.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Stable internal key ("verkehr" / "haushalt") the API filter uses.
    key = Column(String(30), nullable=False, index=True)
    label = Column(String(200), nullable=False)

    memberships = relationship(
        "CommitteeMembership", back_populates="committee", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Committee(key={self.key!r}, label={self.label!r})>"
