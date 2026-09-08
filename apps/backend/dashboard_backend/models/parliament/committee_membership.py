from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from dashboard_backend.models.base import Base

# Strongest role first — a mandate can carry several, and the strongest wins.
COMMITTEE_ROLE_RANKS: tuple[tuple[str, str], ...] = (
    ("chairperson", "Vorsitz"),
    ("deputy_chairperson", "Stellv. Vorsitz"),
    ("foreperson", "Obfrau/Obmann"),
    ("spokesperson", "Sprecher/in"),
    ("member", "Mitglied"),
    ("alternate_member", "Stellv. Mitglied"),
)

COMMITTEE_ROLE_LABELS: dict[str, str] = dict(COMMITTEE_ROLE_RANKS)
COMMITTEE_ROLE_ORDER: dict[str, int] = {
    role: index for index, (role, _) in enumerate(COMMITTEE_ROLE_RANKS)
}
# Unknown roles sort behind every known one but stay visible.
UNKNOWN_ROLE_RANK = len(COMMITTEE_ROLE_RANKS)


def role_rank(role: str | None) -> int:
    return COMMITTEE_ROLE_ORDER.get(role or "", UNKNOWN_ROLE_RANK)


def role_label(role: str | None) -> str:
    if not role:
        return COMMITTEE_ROLE_LABELS["member"]
    return COMMITTEE_ROLE_LABELS.get(role, role)


class CommitteeMembership(Base):
    __tablename__ = "committee_membership"

    id = Column(Integer, primary_key=True)
    mandate_id = Column(
        Integer, ForeignKey("mandate.id", ondelete="CASCADE"), nullable=False, index=True
    )
    committee_id = Column(
        Integer, ForeignKey("committee.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(50), nullable=True)
    role_label = Column(String(50), nullable=True)
    role_rank = Column(Integer, nullable=False, default=UNKNOWN_ROLE_RANK)

    mandate = relationship("Mandate", back_populates="committee_memberships")
    committee = relationship("Committee", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("mandate_id", "committee_id", name="uq_committee_membership"),
    )
