from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from dashboard_backend.models.base import Base


class ProjectToSectionOfLine(Base):
    __tablename__ = 'project_to_section_of_line'
    project_id = Column(Integer, ForeignKey('project.id', onupdate='CASCADE', ondelete='CASCADE'), primary_key=True)
    section_of_line_id = Column(Integer, ForeignKey('section_of_line.id', onupdate='CASCADE', ondelete='CASCADE'), primary_key=True)
    __table_args__ = (
        UniqueConstraint('project_id', 'section_of_line_id', name='uq_project_to_section_of_line'),
    )

