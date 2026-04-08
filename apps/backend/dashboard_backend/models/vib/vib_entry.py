from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from dashboard_backend.models.base import Base
from dashboard_backend.models.vib.vib_entry_project import vib_entry_project


class VibEntry(Base):
    __tablename__ = "vib_entry"

    id = Column(Integer, primary_key=True, index=True)
    vib_report_id = Column(
        Integer, ForeignKey("vib_report.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vib_section = Column(String(20), nullable=True)   # e.g. "B.4.1.1"
    vib_lfd_nr = Column(String(20), nullable=True)
    vib_name_raw = Column(String(500), nullable=False)
    # category: laufend | neu | potentiell | abgeschlossen
    category = Column(String(20), nullable=False, server_default="laufend")

    raw_text = Column(Text, nullable=True)
    bauaktivitaeten = Column(Text, nullable=True)
    teilinbetriebnahmen = Column(Text, nullable=True)
    verkehrliche_zielsetzung = Column(Text, nullable=True)
    durchgefuehrte_massnahmen = Column(Text, nullable=True)
    noch_umzusetzende_massnahmen = Column(Text, nullable=True)

    strecklaenge_km = Column(Float, nullable=True)
    gesamtkosten_mio_eur = Column(Float, nullable=True)
    entwurfsgeschwindigkeit = Column(String(50), nullable=True)
    planungsstand = Column(Text, nullable=True)
    status_planung = Column(Boolean, nullable=False, server_default="false", default=False)
    status_bau = Column(Boolean, nullable=False, server_default="false", default=False)
    status_abgeschlossen = Column(Boolean, nullable=False, server_default="false", default=False)

    ai_extracted = Column(Boolean, nullable=False, server_default="false", default=False)
    ai_result = Column(Text, nullable=True)  # JSON blob from LLM extraction

    report = relationship("VibReport", back_populates="entries")
    projects = relationship("Project", secondary=vib_entry_project, backref="vib_entries")
    pfa_entries = relationship("VibPfaEntry", back_populates="vib_entry", cascade="all, delete-orphan")
