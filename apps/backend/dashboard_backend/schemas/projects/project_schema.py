from pydantic import BaseModel
from typing import Optional, Any

class ProjectSchema(BaseModel):
    id: Optional[int] = None
    name: str
    project_number: Optional[str] = None
    superior_project_id: Optional[int] = None
    old_id: Optional[int] = None
    superior_project_old_id: Optional[int] = None
    description: Optional[str] = None
    justification: Optional[str] = None

    effects_passenger_long_rail: Optional[bool] = False
    effects_passenger_local_rail: Optional[bool] = False
    effects_cargo_rail: Optional[bool] = False

    length: Optional[float]

    nbs: bool = False
    abs: bool = False
    elektrification: bool = False
    charging_station: Optional[bool] = False
    small_charging_station: Optional[bool] = False
    second_track: bool = False
    third_track: bool = False
    fourth_track: bool = False
    curve: bool = False
    platform: bool = False
    junction_station: bool = False
    number_junction_station: Optional[int]
    overtaking_station: bool = False
    number_overtaking_station: Optional[int]
    double_occupancy: bool = False
    block_increase: bool = False
    flying_junction: bool = False
    tunnel_structural_gauge: bool = False
    increase_speed: bool = False
    new_vmax: Optional[int]
    level_free_platform_entrance: bool = False
    etcs: bool = False
    etcs_level: Optional[int]
    station_railroad_switches: Optional[bool] = False
    new_station: Optional[bool] = False
    depot: Optional[bool] = False
    battery: Optional[bool] = False
    h2: Optional[bool] = False
    efuel: Optional[bool] = False
    closure: Optional[bool] = False
    optimised_electrification: Optional[bool] = False
    filling_stations_efuel: Optional[bool] = False
    filling_stations_h2: Optional[bool] = False
    filling_stations_diesel: Optional[bool] = False
    filling_stations_count: Optional[int] = 0
    sanierung: Optional[bool] = False
    sgv740m: Optional[bool] = False
    railroad_crossing: Optional[bool] = False
    new_estw: Optional[bool] = False
    new_dstw: Optional[bool] = False
    noise_barrier: Optional[bool] = False
    overpass: Optional[bool] = False
    buffer_track: Optional[bool] = False
    gwb: Optional[bool] = False
    simultaneous_train_entries: Optional[bool] = False
    tilting: Optional[bool] = False

    geojson_representation: Optional[str]
    centroid: Optional[Any]  # Für Geo-Daten, ggf. anpassen

    class Config:
        from_attributes = True