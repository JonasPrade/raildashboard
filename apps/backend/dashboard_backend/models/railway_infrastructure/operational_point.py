from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from dashboard_backend.models.base import Base


class OperationalPoint(Base):
    __tablename__ = 'operational_point'

    id = Column(Integer, primary_key=True)
    op_id = Column(String, unique=True)
    name = Column(String)
    type = Column(String)
    country_code = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    validity_date_start = Column(Date)
    validity_date_end = Column(Date)
    railway_location = Column(String)
    railway_location_km = Column(Float)

    def __repr__(self):
        return f"<OperationalPoint(op_id={self.op_id}, name={self.name})>"
