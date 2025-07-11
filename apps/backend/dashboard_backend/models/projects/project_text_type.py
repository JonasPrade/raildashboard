from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from dashboard_backend.models.base import Base


class ProjectTextType(Base):
    __tablename__ = 'project_text_type'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)


    def __repr__(self):
        return f"<ProjectTextType(id={self.id}, name='{self.name}')>"
