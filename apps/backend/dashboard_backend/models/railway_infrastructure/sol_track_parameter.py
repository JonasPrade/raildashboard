from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from dashboard_backend.models.base import Base


class SOLTrackParameter(Base):
    __tablename__ = 'sol_track_parameter'
    id = Column(Integer, primary_key=True)
    parameter_id = Column(String)
    is_applicable = Column(String)
    value = Column(String)
    optional_value = Column(String)
    track_id = Column(Integer, ForeignKey('sol_track.id'))
    manual_added = Column(Boolean, default=False)
    track = relationship('SOLTrack', back_populates='parameters')

