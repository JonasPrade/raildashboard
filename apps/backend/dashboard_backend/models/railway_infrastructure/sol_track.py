from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship

from dashboard_backend.models.base import Base


class SOLTrack(Base):
    __tablename__ = 'sol_track'
    id = Column(Integer, primary_key=True)
    track_validity_date_start = Column(Date)
    track_validity_date_end = Column(Date)
    sol_track_identification = Column(String)
    sol_track_direction = Column(String)
    section_id = Column(Integer, ForeignKey('section_of_line.id'))
    section = relationship('SectionOfLine', back_populates='tracks')
    parameters = relationship('SOLTrackParameter', back_populates='track')

    def __repr__(self):
        return f"<SOLTrack(sol_track_identification={self.sol_track_identification}, direction={self.sol_track_direction})>"

