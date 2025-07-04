from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Float, Text, Index
from sqlalchemy.orm import relationship, backref

from dashboard_backend.models.base import Base


class Finve(Base):
    __tablename__ = 'finve'

    id = Column(Integer, primary_key=True, autoincrement=True, server_default="2000")
    name = Column(String(1000))
    starting_year = Column(Integer)
    cost_estimate_original = Column(Integer)
    temporary_finve_number = Column(Boolean, default=False)  # if true the finve number is not known yet

    projects = relationship(
        'ProjectContent',
        secondary="finve_to_project",
        backref=backref('finve', lazy=True)
    )
