from pydantic import BaseModel, ConfigDict, field_serializer, model_serializer
from typing import Optional, Any
from ..utils import nan_to_none


class TitelEntrySchema(BaseModel):
    titel_key: str
    kapitel: str
    titel_nr: str
    label: str
    is_nachrichtlich: bool
    cost_estimate_last_year: Optional[int] = None
    cost_estimate_aktuell: Optional[int] = None
    verausgabt_bis: Optional[int] = None
    bewilligt: Optional[int] = None
    ausgabereste_transferred: Optional[int] = None
    veranschlagt: Optional[int] = None
    vorhalten_future: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_entry(cls, entry: Any) -> "TitelEntrySchema":
        return cls(
            titel_key=entry.titel.titel_key,
            kapitel=entry.titel.kapitel,
            titel_nr=entry.titel.titel_nr,
            label=entry.titel.label,
            is_nachrichtlich=entry.titel.is_nachrichtlich,
            cost_estimate_last_year=entry.cost_estimate_last_year,
            cost_estimate_aktuell=entry.cost_estimate_aktuell,
            verausgabt_bis=entry.verausgabt_bis,
            bewilligt=entry.bewilligt,
            ausgabereste_transferred=entry.ausgabereste_transferred,
            veranschlagt=entry.veranschlagt,
            vorhalten_future=entry.vorhalten_future,
        )


class BudgetSummarySchema(BaseModel):
    budget_year: int
    lfd_nr: Optional[str] = None
    bedarfsplan_number: Optional[str] = None
    cost_estimate_original: Optional[int] = None
    cost_estimate_last_year: Optional[int] = None
    cost_estimate_actual: Optional[int] = None
    delta_previous_year: Optional[int] = None
    delta_previous_year_relativ: Optional[float] = None
    spent_two_years_previous: Optional[int] = None
    allowed_previous_year: Optional[int] = None
    spending_residues: Optional[int] = None
    year_planned: Optional[int] = None
    next_years: Optional[int] = None
    titel_entries: list[TitelEntrySchema] = []

    model_config = ConfigDict(from_attributes=True)


class FinveWithBudgetsSchema(BaseModel):
    id: int
    name: Optional[str] = None
    starting_year: Optional[int] = None
    cost_estimate_original: Optional[int] = None
    budgets: list[BudgetSummarySchema] = []

    model_config = ConfigDict(from_attributes=True)


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

    geojson_representation: Optional[str] = None
    centroid: Optional[Any]  = None # Für Geo-Daten, ggf. anpassen

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("centroid")
    def serialize_centroid(self, v):
        if v is None:
            return None
        from geoalchemy2.shape import to_shape
        from shapely.geometry import mapping
        return nan_to_none(mapping(to_shape(v)))  # sanitize coords

    @model_serializer(mode="wrap")
    def ser(self, serializer):
        # post-process the whole dict to replace any NaN in floats/lists/dicts
        data = serializer(self)
        return nan_to_none(data)
