from sqlalchemy import Column, Index, Integer, ForeignKey, UniqueConstraint
from dashboard_backend.models.base import Base


class ProjectToOperationPoint(Base):
    __tablename__ = 'project_to_operation_point'
    project_id = Column(Integer, ForeignKey('project.id', onupdate='CASCADE', ondelete='CASCADE'), primary_key=True)
    operational_point_id = Column(Integer, ForeignKey('operational_point.id', onupdate='CASCADE', ondelete='CASCADE'), primary_key=True)
    __table_args__ = (
        UniqueConstraint('project_id', 'operational_point_id', name='uq_project_to_operational_point'),
        # operational point → projects; the primary key leads with project_id.
        Index('ix_project_to_operation_point_op_id', 'operational_point_id'),
    )

    def __repr__(self):
        return f"<ProjectToOperationPoint(project_id={self.project_id}, operation_point_id={self.operational_point_id})>"
