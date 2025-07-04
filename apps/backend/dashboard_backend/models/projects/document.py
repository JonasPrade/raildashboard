from sqlalchemy import Column, Integer, String, Text, Date, Boolean
from dashboard_backend.models.base import Base
from sqlalchemy.orm import relationship

class Document(Base):
    __tablename__ = 'document'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    file_path = Column(String(500), nullable=False)  # ggf. als URL oder lokaler Pfad
    date = Column(Date)  # Veröffentlichungsdatum
    source = Column(String(255))  # z.B. BMDV, DB Netz
    is_public = Column(Boolean, default=True)

    projects = relationship(
        'Project',
        secondary='document_to_project',
        back_populates='documents'
    )

