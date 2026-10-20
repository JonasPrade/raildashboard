from sqlalchemy import Column, Integer, String
from dashboard_backend.models.base import Base


class ProjectTextCategory(Base):
    """How urgent a project text is (e.g. Info, Warnung). ``style`` picks one of
    the fixed display styles; see docs/features/feature-text-categories.md."""

    __tablename__ = 'project_text_category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    style = Column(String(20), nullable=False)

    def __repr__(self):
        return f"<ProjectTextCategory(id={self.id}, name='{self.name}', style='{self.style}')>"
