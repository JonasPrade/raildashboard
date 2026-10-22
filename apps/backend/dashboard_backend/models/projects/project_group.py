from sqlalchemy import JSON, Column, String, Integer, Boolean, Text
from sqlalchemy.orm import relationship
from dashboard_backend.models.base import Base


class ProjectGroup(Base):
    __tablename__ = 'project_group'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    short_name = Column(String(20), unique=True)
    description = Column(Text)
    public = Column(Boolean, default=False)
    color = Column(String(10), default="#6E50FA")
    plot_only_superior_projects = Column(Boolean, default=True,
        comment='if true, only projects that have no superior project is plotted in frontend')
    is_visible = Column(Boolean, default=True,
        comment='if false, this group is hidden from the map entirely')
    is_default_selected = Column(Boolean, default=False,
        comment='if true, this group is pre-selected on the map when no ?group= URL param is present')
    skipped_phases = Column(JSON, nullable=False, default=list, server_default='[]',
        comment='MainPhase values (VORPLANUNG/GENEHMIGUNGSPLANUNG) its projects usually skip, '
                'e.g. corridor renewals without Planfeststellung')
    assumed_build_months = Column(Integer, nullable=True,
        comment='assumed construction period in months for projects without a published '
                'closure period (corridor renewals: 6); the forecast derives the commissioning')
    id_old = Column(Integer, unique=True, nullable=True,
        comment='old id from the old database, used for migration purposes')

    # relationships
    projects = relationship(
        'Project',
        secondary='project_to_project_group',
        back_populates='project_groups'
    )

    def __repr__(self):
        return f"<ProjectGroup(id={self.id}, name={self.name}, short_name={self.short_name})>"