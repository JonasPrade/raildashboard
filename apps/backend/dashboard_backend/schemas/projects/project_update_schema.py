from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ProjectUpdate(BaseModel):
    """Partial update schema for Project (PATCH semantics – all fields optional)."""

    name: Optional[str] = None
    project_number: Optional[str] = None
    description: Optional[str] = None
    justification: Optional[str] = None
    superior_project_id: Optional[int] = None

    effects_passenger_long_rail: Optional[bool] = None
    effects_passenger_local_rail: Optional[bool] = None
    effects_cargo_rail: Optional[bool] = None

    length: Optional[float] = None

    nbs: Optional[bool] = None
    abs: Optional[bool] = None
    elektrification: Optional[bool] = None
    charging_station: Optional[bool] = None
    small_charging_station: Optional[bool] = None
    second_track: Optional[bool] = None
    third_track: Optional[bool] = None
    fourth_track: Optional[bool] = None
    curve: Optional[bool] = None
    platform: Optional[bool] = None
    junction_station: Optional[bool] = None
    number_junction_station: Optional[int] = None
    overtaking_station: Optional[bool] = None
    number_overtaking_station: Optional[int] = None
    double_occupancy: Optional[bool] = None
    block_increase: Optional[bool] = None
    flying_junction: Optional[bool] = None
    tunnel_structural_gauge: Optional[bool] = None
    increase_speed: Optional[bool] = None
    new_vmax: Optional[int] = None
    level_free_platform_entrance: Optional[bool] = None
    etcs: Optional[bool] = None
    etcs_level: Optional[int] = None
    station_railroad_switches: Optional[bool] = None
    new_station: Optional[bool] = None
    depot: Optional[bool] = None
    battery: Optional[bool] = None
    h2: Optional[bool] = None
    efuel: Optional[bool] = None
    closure: Optional[bool] = None
    optimised_electrification: Optional[bool] = None
    filling_stations_efuel: Optional[bool] = None
    filling_stations_h2: Optional[bool] = None
    filling_stations_diesel: Optional[bool] = None
    filling_stations_count: Optional[int] = None
    sanierung: Optional[bool] = None
    sgv740m: Optional[bool] = None
    railroad_crossing: Optional[bool] = None
    new_estw: Optional[bool] = None
    new_dstw: Optional[bool] = None
    noise_barrier: Optional[bool] = None
    overpass: Optional[bool] = None
    buffer_track: Optional[bool] = None
    gwb: Optional[bool] = None
    simultaneous_train_entries: Optional[bool] = None
    tilting: Optional[bool] = None

    geojson_representation: Optional[str] = None
