from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from dashboard_backend.models.base import Base


class TextToProject(Base):
    __tablename__ = 'text_to_project'
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    text_id = Column(Integer, ForeignKey('project_text.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    __table_args__ = (
        UniqueConstraint('project_id', 'text_id', name='uq_text_to_project'),
    )