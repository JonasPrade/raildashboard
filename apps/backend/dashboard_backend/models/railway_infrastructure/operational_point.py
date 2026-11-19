from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
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
    # rail (RINF) | light_rail | subway | tram (stops imported from OSM, see
    # scripts/import_osm_stops.py and docs/features/feature-routing.md → "Gleisarten").
    network = Column(String, nullable=False, default="rail", server_default="rail", index=True)
    source = Column(String, nullable=False, default="rinf", server_default="rinf")

    # relationships
    projects = relationship(
        'Project',
        secondary='project_to_operation_point',
        back_populates='operational_points'
    )

    def __repr__(self):
        return f"<OperationalPoint(op_id={self.op_id}, name={self.name})>"
