from sqlalchemy import Column, Integer, Index, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from dashboard_backend.models.base import Base

class Project(Base):
    __tablename__ = 'project'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    project_number = Column(String, unique=True, nullable=False)
    superior_project_id = Column(Integer, ForeignKey('project.id', onupdate='CASCADE',
                                                                      ondelete='CASCADE'))
    description = Column(String, nullable=True)
    justification = Column(String, nullable=True)

    # which train category is affected by the project
    effects_passenger_long_rail = Column(Boolean, default=False)
    effects_passenger_local_rail = Column(Boolean, default=False)
    effects_cargo_rail = Column(Boolean, default=False)

    # project data
    length = Column(Float)

    # properties of project
    nbs = Column(Boolean, nullable=False, default=False)
    abs = Column(Boolean, nullable=False, default=False)
    elektrification = Column(Boolean, nullable=False, default=False)
    charging_station = Column(Boolean, default=False)
    small_charging_station = Column(Boolean, default=False)
    second_track = Column(Boolean, nullable=False, default=False)
    third_track = Column(Boolean, nullable=False, default=False)
    fourth_track = Column(Boolean, nullable=False, default=False)
    curve = Column(Boolean, nullable=False, default=False)  # Neue Verbindungskurve
    platform = Column(Boolean, nullable=False, default=False)  # Neuer Bahnsteig
    junction_station = Column(Boolean, nullable=False, default=False)
    number_junction_station = Column(Integer)
    overtaking_station = Column(Boolean, nullable=False, default=False)
    number_overtaking_station = Column(Integer)
    double_occupancy = Column(Boolean, nullable=False, default=False)
    block_increase = Column(Boolean, nullable=False, default=False)
    flying_junction = Column(Boolean, nullable=False, default=False)
    tunnel_structural_gauge = Column(Boolean, nullable=False, default=False)
    increase_speed = Column(Boolean, nullable=False, default=False)
    new_vmax = Column(Integer)
    level_free_platform_entrance = Column(Boolean, nullable=False, default=False)
    etcs = Column(Boolean, nullable=False, default=False)
    etcs_level = Column(Integer)
    station_railroad_switches = Column(Boolean, default=False)
    new_station = Column(Boolean, default=False)
    depot = Column(Boolean, default=False)
    battery = Column(Boolean, default=False)
    h2 = Column(Boolean, default=False)
    efuel = Column(Boolean, default=False)
    closure = Column(Boolean, default=False)  # close of rail
    optimised_electrification = Column(Boolean, default=False)
    filling_stations_efuel = Column(Boolean, default=False)
    filling_stations_h2 = Column(Boolean, default=False)
    filling_stations_diesel = Column(Boolean, default=False)
    filling_stations_count = Column(Integer, default=0)
    sanierung = Column(Boolean, default=False)
    sgv740m = Column(Boolean, default=False)
    railroad_crossing = Column(Boolean, default=False)  # Änderungen an Bahnübergängen
    new_estw = Column(Boolean, default=False)
    new_dstw = Column(Boolean, default=False)
    noise_barrier = Column(Boolean, default=False)  # alle Lärmschutzmaßnahmen
    overpass = Column(Boolean, default=False)  # Überleitstellen
    buffer_track = Column(Boolean, default=False)  # Puffergleis
    gwb = Column(Boolean, default=False)  # Gleiswechselbetrieb
    simultaneous_train_entries = Column(Boolean, default=False)  # gleichzeitige Zugeinfahrten
    tilting = Column(Boolean, default=False)

    # some additionale fields for Geojson and centroid to avoid anoying calculations
    geojson_representation = Column(String)  # storing the GeoJSON as a text field
    centroid = Column(Geometry('POINT'))  # storing the centroid as a point geometry

    # Relationships
    bvwp_data = relationship(
        'BvwpProjectData',
        backref='project',
        cascade="all, delete-orphan"
    )
    project_groups = relationship(
        'ProjectGroup',
        secondary='project_to_project_group',
        back_populates='projects'
    )
    finve = relationship(
        'Finve',
        secondary='finve_to_project',
        backref='projects'
    )
    project_texts = relationship(
        'ProjectToText',
        backref='project',
        cascade="all, delete-orphan"
    )
    documents = relationship(
        'Document',
        secondary='document_to_project',
        back_populates='projects'
    )
    operational_points = relationship(
        'OperationalPoint',
        secondary='project_to_operation_point',
        back_populates='projects'
    )
    project_progress = relationship('ProjectProgress', backref='project', cascade="all, delete-orphan")
    superior_project = relationship('Project', remote_side='Project.id')

    # indexes
    superior_project_id_index = Index('superior_project_content_id_index',
                                                         superior_project_id)
