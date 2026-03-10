from sqlalchemy import Column, Integer, ForeignKey, Index, text
from dashboard_backend.models.base import Base


class FinveToProject(Base):
    __tablename__ = 'finve_to_project'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    finve_id = Column(Integer, ForeignKey('finve.id'), nullable=False)
    # NULL  → permanent link used for regular (non-Sammel) FinVes
    # <year> → year-scoped link used for Sammelfinanzierungsvereinbarungen
    haushalt_year = Column(Integer, nullable=True)

    __table_args__ = (
        # One permanent entry per (project, finve) — only when haushalt_year IS NULL
        Index(
            'uq_finve_to_project_permanent',
            'project_id', 'finve_id',
            unique=True,
            postgresql_where=text('haushalt_year IS NULL'),
        ),
        # One entry per (project, finve, year) — only when haushalt_year IS NOT NULL
        Index(
            'uq_finve_to_project_yearly',
            'project_id', 'finve_id', 'haushalt_year',
            unique=True,
            postgresql_where=text('haushalt_year IS NOT NULL'),
        ),
    )
