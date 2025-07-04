from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from dashboard_backend.models.base import Base


class FinveToProject(Base):
    __tablename__ = 'finve_to_project'

    project_id = Column(Integer, ForeignKey('project.id'), primary_key=True)
    finve_id = Column(Integer, ForeignKey('finve.id'), primary_key=True)

    __table_args__ = (
        UniqueConstraint('project_id', 'finve_id', name='uq_finve_to_project'),
    )
