from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from dashboard_backend.models.base import Base


class VibPfaEntry(Base):
    __tablename__ = "vib_pfa_entry"

    id = Column(Integer, primary_key=True, index=True)
    vib_entry_id = Column(
        Integer, ForeignKey("vib_entry.id", ondelete="CASCADE"), nullable=False, index=True
    )
    abschnitt_label = Column(String(100), nullable=True)  # e.g. "1. Baustufe"
    nr_pfa = Column(String(50), nullable=True)
    oertlichkeit = Column(String(200), nullable=True)
    entwurfsplanung = Column(String(100), nullable=True)
    abschluss_finve = Column(String(100), nullable=True)
    datum_pfb = Column(String(100), nullable=True)
    baubeginn = Column(String(100), nullable=True)
    inbetriebnahme = Column(String(100), nullable=True)

    vib_entry = relationship("VibEntry", back_populates="pfa_entries")
