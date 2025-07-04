from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from dashboard_backend.models.base import Base


class ProjectToProjectGroup(Base):
    __tablename__ = 'project_to_project_group'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project.id', onupdate='CASCADE', ondelete='CASCADE'))
    project_group_id = Column(Integer, ForeignKey('project_group.id', onupdate='CASCADE', ondelete='CASCADE'))

    __table_args__ = (
        UniqueConstraint('project_id', 'project_group_id', name='uq_project_to_project_group'),
    )

    def __repr__(self):
        return f"<ProjectToProjectGroup(project_id={self.project_id}, project_group_id={self.project_group_id})>"
