from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from dashboard_backend.models.base import Base


class DocumentToProject(Base):
    __tablename__ = 'document_to_project'

    project_id = Column(Integer, ForeignKey('project.id', ondelete="CASCADE"), primary_key=True)
    document_id = Column(Integer, ForeignKey('document.id', ondelete="CASCADE"), primary_key=True)

    __table_args__ = (
        UniqueConstraint('project_id', 'document_id', name='uq_document_to_project'),
    )
