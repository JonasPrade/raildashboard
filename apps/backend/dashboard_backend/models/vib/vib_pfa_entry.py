from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from dashboard_backend.models.base import Base


class VibPfaEntry(Base):
    __tablename__ = "vib_pfa_entry"

    id = Column(Integer, primary_key=True, index=True)
    vib_entry_id = Column(
        Integer, ForeignKey("vib_entry.id", ondelete="CASCADE"), nullable=False, index=True
    )
    abschnitt_label = Column(Text, nullable=True)
    nr_pfa = Column(String(50), nullable=True)
    oertlichkeit = Column(Text, nullable=True)
    entwurfsplanung = Column(Text, nullable=True)
    abschluss_finve = Column(Text, nullable=True)
    datum_pfb = Column(Text, nullable=True)
    baubeginn = Column(Text, nullable=True)
    inbetriebnahme = Column(Text, nullable=True)

    vib_entry = relationship("VibEntry", back_populates="pfa_entries")
