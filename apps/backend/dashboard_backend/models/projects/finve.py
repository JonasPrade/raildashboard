from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Float, Text, Index
from sqlalchemy.orm import relationship, backref

from dashboard_backend.models.base import Base


class Finve(Base):
    __tablename__ = 'finve'

    id = Column(Integer, primary_key=True, autoincrement=True, server_default="2000")
    name = Column(String(1000))
    starting_year = Column(Integer)
    cost_estimate_original = Column(Integer)
    temporary_finve_number = Column(Boolean, default=False)  # if true the finve number is not known yet
    # Identity for measures the budget report lists without a FinVe number —
    # the tables of Annex VWIB Part B beyond the Bedarfsplan table (Lärmsanierung,
    # ERTMS, Kleine und Mittlere Maßnahmen, InvKG) identify their entries by a
    # string ("t4:F 03 E 0793", "t5:B0094") instead. NULL for a FinVe that has a
    # real number; the importer matches on it across report years.
    finve_key = Column(String(120), nullable=True, unique=True, index=True)
    is_sammel_finve = Column(Boolean, default=False, nullable=False, server_default="false")
    # Manual planning-phase mapping for ProjectProgress derivation (a MainPhase
    # value). Overrides the auto-detection from the Sammel-FinVe name; used to
    # resolve Sammel-FinVes whose Leistungsphase can't be parsed (e.g. EKrG).
    progress_phase = Column(String(40), nullable=True)


