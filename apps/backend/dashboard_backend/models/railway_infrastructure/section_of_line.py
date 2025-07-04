from sqlalchemy import Column, Integer, String, Date, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship

from dashboard_backend.models.base import Base


class SectionOfLine(Base):
    __tablename__ = 'section_of_line'
    id = Column(Integer, primary_key=True)
    validity_date_start = Column(Date)
    validity_date_end = Column(Date)
    solim_code = Column(String)
    sol_line_identification = Column(String)
    sol_op_start = Column(String, ForeignKey('operational_point.op_id'))
    sol_op_end = Column(String, ForeignKey('operational_point.op_id'))
    sol_length = Column(Float)
    sol_nature = Column(String)

    tracks = relationship('SOLTrack', back_populates='section')
    op_start = relationship('OperationalPoint', foreign_keys=[sol_op_start])
    op_end = relationship('OperationalPoint', foreign_keys=[sol_op_end])

    def __repr__(self):
            return f"<SectionOfLine(solim_code={self.solim_code}, length={self.sol_length})>"


