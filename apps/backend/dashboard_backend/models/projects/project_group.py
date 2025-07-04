from sqlalchemy import Column, String, Integer, Boolean, Text
from sqlalchemy.orm import relationship
from dashboard_backend.models.base import Base


class ProjectGroup(Base):
    __tablename__ = 'project_group'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    short_name = Column(String(20), unique=True)
    description = Column(Text)
    public = Column(Boolean, default=False)
    color = Column(String(10), default="#FF0000")
    plot_only_superior_projects = Column(Boolean, default=True,
        comment='if true, only projects that have no superior project is plotted in frontend')

    # relationships
    projects = relationship(
        'Project',
        secondary='project_to_project_group',
        back_populates='project_groups'
    )

    def __repr__(self):
        return f"<ProjectGroup(id={self.id}, name={self.name}, short_name={self.short_name})>"