import numpy as np
import pandas as pd
from pydantic import ValidationError
import logging

from dashboard_backend.database import Session
from dashboard_backend.models.projects import Project
from dashboard_backend.schemas.projects import ProjectSchema

def import_project_content_old_db(filepath_csv: str, clear_db: bool = False):
    df = pd.read_csv(filepath_csv)

    # renaming of some columns
    df.rename(columns={
        'id': 'old_id',
        'superior_project_content_id': 'superior_project_old_id',
        }, inplace=True)

    # drop some columns by name
    df = df.drop(columns=[
        'project_id',
        'nkv',
        'planned_total_cost',
        'actual_cost',
        'ibn_planned',
        'ibn_final',
        'hoai',
        'parl_befassung_planned',
        'parl_befassung_date',
        'ro_finished',
        'ro_finished_date',
        'pf_finished',
        'pf_finished_date',
        'bvwp_planned_cost',
        'bvwp_planned_maintenance_cost',
        'bvwp_environmental_impact',
        'bvwp_planned_planning_cost',
        'bvwp_planned_planning_cost_incurred',
        'bvwp_total_budget_relevant_cost',
        'bvwp_total_budget_relevant_cost_incurred',
        'bvwp_valuation_relevant_cost',
        'bvwp_valuation_relevant_cost_pricelevel_2012',
        'bvwp_regional_significance',
        'bottleneck_elimination',
        'traveltime_reduction',
        'bvwp_alternatives',
        'bvwp_congested_rail_reference_6to9_km',
        'bvwp_congested_rail_reference_6to9_perc',
        'bvwp_congested_rail_plancase_6to9_km',
        'bvwp_congested_rail_plancase_6to9_perc',
        'bvwp_congested_rail_reference_9to16_km',
        'bvwp_congested_rail_reference_9to16_perc',
        'bvwp_congested_rail_plancase_9to16_km',
        'bvwp_congested_rail_plancase_9to16_perc',
        'bvwp_congested_rail_reference_16to19_km',
        'bvwp_congested_rail_reference_16to19_perc',
        'bvwp_congested_rail_plancase_16to19_km',
        'bvwp_congested_rail_plancase_16to19_perc',
        'bvwp_congested_rail_reference_19to22_km',
        'bvwp_congested_rail_reference_19to22_perc',
        'bvwp_congested_rail_plancase_19to22_km',
        'bvwp_congested_rail_plancase_19to22_perc',
        'bvwp_congested_rail_reference_22to6_km',
        'bvwp_congested_rail_reference_22to6_perc',
        'bvwp_congested_rail_plancase_22to6_km',
        'bvwp_congested_rail_plancase_22to6_perc',
        'bvwp_congested_rail_reference_day_km',
        'bvwp_congested_rail_reference_day_perc',
        'bvwp_congested_rail_plancase_day_km',
        'bvwp_congested_rail_plancase_day_perc',
        'bvwp_unscheduled_waiting_period_reference',
        'bvwp_unscheduled_waiting_period_plancase',
        'bvwp_punctuality_cargo_reference',
        'bvwp_delta_punctuality_absolut',
        'bvwp_traveltime_examples',
        'bvwp_delta_punctuality_relativ',
        'relocation_car_to_rail',
        'relocation_rail_to_car',
        'relocation_air_to_rail',
        'induced_traffic',
        'delta_car_km',
        'delta_rail_running_time',
        'delta_travel_time_rail',
        'delta_travel_time_car_to_rail',
        'delta_travel_time_rail_to_car',
        'delta_travel_time_air_to_rail',
        'delta_travel_time_induced',
        'relocation_truck_to_rail',
        'relocation_ship_to_rail',
        'delta_truck_km',
        'delta_truck_count',
        'delta_rail_cargo_count',
        'delta_rail_cargo_running_time',
        'delta_rail_cargo_km_lkw_to_rail',
        'delta_rail_cargo_km_ship_to_rail',
        'delta_rail_cargo_time_rail',
        'delta_rail_cargo_time_lkw_to_rail',
        'delta_rail_cargo_time_ship_to_rail',
        'use_change_operation_cost_car_yearly',
        'use_change_operating_cost_rail_yearly',
        'use_change_operating_cost_air_yearly',
        'use_change_pollution_car_yearly',
        'use_change_pollution_rail_yearly',
        'use_change_pollution_air_yearly',
        'use_change_safety_car_yearly',
        'use_change_safety_rail_yearly',
        'use_change_travel_time_rail_yearly',
        'use_change_travel_time_induced_yearly',
        'use_change_travel_time_pkw_yearly',
        'use_change_travel_time_air_yearly',
        'use_change_travel_time_less_2min_yearly',
        'use_change_implicit_benefit_induced_yearly',
        'use_change_implicit_benefit_pkw_yearly',
        'use_change_implicit_benefit_air_yearly',
        'use_sum_passenger_yearly',
        'use_change_operation_cost_car_present_value',
        'use_change_operating_cost_rail_present_value',
        'use_change_operating_cost_air_present_value',
        'use_change_pollution_car_present_value',
        'use_change_pollution_rail_present_value',
        'use_change_pollution_air_present_value',
        'use_change_safety_car_present_value',
        'use_change_safety_rail_present_value',
        'use_change_travel_time_rail_present_value',
        'use_change_travel_time_induced_present_value',
        'use_change_travel_time_pkw_present_value',
        'use_change_travel_time_air_present_value',
        'use_change_travel_time_less_2min_present_value',
        'use_change_implicit_benefit_induced_present_value',
        'use_change_implicit_benefit_pkw_present_value',
        'use_change_implicit_benefit_air_present_value',
        'use_sum_passenger_present_value',
        'use_change_operating_cost_truck_yearly',
        'use_change_operating_cost_rail_cargo_yearly',
        'use_change_operating_cost_ship_yearly',
        'use_change_pollution_truck_yearly',
        'use_change_pollution_rail_cargo_yearly',
        'use_change_pollution_ship_yearly',
        'use_change_safety_truck_yearly',
        'use_change_safety_rail_cargo_yearly',
        'use_change_safety_ship_yearly',
        'use_change_running_time_rail_yearly',
        'use_change_running_time_lkw_yearly',
        'use_change_running_time_ship_yearly',
        'use_change_implicit_benefit_truck_yearly',
        'use_change_implicit_benefit_ship_yearly',
        'use_change_reliability_yearly',
        'use_sum_cargo_yearly',
        'use_change_operating_cost_truck_present_value',
        'use_change_operating_cost_rail_cargo_present_value',
        'use_change_operating_cost_ship_present_value',
        'use_change_pollution_truck_present_value',
        'use_change_pollution_rail_cargo_present_value',
        'use_change_pollution_ship_present_value',
        'use_change_safety_truck_present_value',
        'use_change_safety_rail_cargo_present_value',
        'use_change_safety_ship_present_value',
        'use_change_running_time_rail_present_value',
        'use_change_running_time_lkw_present_value',
        'use_change_running_time_ship_present_value',
        'use_change_implicit_benefit_truck_present_value',
        'use_change_implicit_benefit_ship_present_value',
        'use_change_reliability_present_value',
        'use_sum_cargo_present_value',
        'use_change_maintenance_cost_yearly',
        'use_change_lcc_infrastructure_yearly',
        'use_change_noise_intown_yearly',
        'use_change_noise_outtown_yearly',
        'sum_use_change_yearly',
        'use_change_maintenance_cost_present_value',
        'use_change_lcc_infrastructure_present_value',
        'use_change_noise_intown_present_value',
        'use_change_noise_outtown_present_value',
        'sum_use_change_present_value',
        'bvwp_duration_of_outstanding_planning',
        'bvwp_duration_of_build',
        'bvwp_duration_operating',
        'delta_nox',
        'delta_co',
        'delta_co2',
        'delta_hc',
        'delta_pm',
        'delta_so2',
        'bvwp_sum_use_environment',
        'bvwp_sum_environmental_affectedness',
        'bvwp_sum_environmental_affectedness_text',
        'noise_new_affected',
        'noise_relieved',
        'change_noise_outtown',
        'area_nature_high_importance',
        'area_nature_high_importance_per_km',
        'area_nature_high_importance_rating',
        'natura2000_rating',
        'natura2000_not_excluded',
        'natura2000_probably',
        'ufr_250',
        'ufr_250_per_km',
        'ufra_250_rating',
        'bfn_rating',
        'ufr_1000_undissacted_large_area',
        'ufr_1000_undissacted_large_area_per_km',
        'ufr_1000_undissacted_large_mammals',
        'ufr_1000_undissacted_large_mammals_per_km',
        'count_undissacted_area',
        'count_reconnect_area',
        'land_consumption',
        'flooding_area',
        'flooding_area_per_km',
        'flooding_area_rating',
        'water_protection_area',
        'water_protection_area_per_km',
        'water_protection_area_rating',
        'uzvr',
        'uvzr_rating',
        'priortiy_area_landscape_protection',
        'priority_area_landscape_protection_per_km',
        'priority_area_landscape_protection_rating',
        'environmental_additional_informations',
        'bvwp_valuation_relevant_cost_pricelevel_2012_planning_cost',
        'bvwp_valuation_relevant_cost_pricelevel_2012_present_value',
        'spatial_significance_overall_result',
        'spatial_significance_reasons',
        'spatial_significance_street',
        'spatial_significance_accessibility_deficits',
        'spatial_significance_conclusion',
        'bvwp_additional_informations',
        'delta_km_rail',
        'delta_rail_km_rail',
        'delta_rail_km_car_to_rail',
        'delta_rail_km_rail_to_car',
        'delta_rail_km_air_to_rail',
        'delta_rail_km_induced',
        'bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cos',
        'use_capital_service_spfv',
        'use_maintenance_cost_spfv',
        'use_energy_cost_spfv',
        'use_capital_service_spnv',
        'use_maintenance_cost_spnv',
        'use_energy_cost_spnv',
        'use_capital_service_loco_sgv',
        'use_maintenance_cost_loco_sgv',
        'use_energy_cost_sgv',
        'use_change_traction_sgv',
        'maintenance_cost',
        'planning_cost',
        'capital_service_cost',
        'investment_cost',
        'optimised_electrification',
        'lp_12',
        'lp_34',
        'bau',
        'ibn_erfolgt',
        'priority',
        'lfd_nr',
        'finve_nr',
        'bedarfsplan_nr',
        'reason_project',
        'reason_priority',
    ])

    # replace all string "false" and "true" with boolean values
    df = df.replace({'false': False, 'true': True})
    # convert all nan to None

    # int columns to int
    int_columns = [
        'number_junction_station',
        'number_overtaking_station',
        'new_vmax',
        'etcs_level',
        'filling_stations_count',
        'superior_project_old_id',
    ]
    for col in int_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')


    # boolean columns to boolean
    bool_columns = [
        'nbs', 'abs', 'elektrification', 'charging_station', 'small_charging_station',
        'second_track', 'third_track', 'fourth_track', 'curve', 'platform',
        'junction_station', 'overtaking_station', 'double_occupancy',
        'block_increase', 'flying_junction', 'tunnel_structural_gauge',
        'increase_speed', 'level_free_platform_entrance', 'etcs',
        'station_railroad_switches', 'new_station', 'depot', 'battery',
        'h2', 'efuel', 'closure',
        'filling_stations_efuel', 'filling_stations_h2',
        'filling_stations_diesel', 'sanierung', 'sgv740m', 'railroad_crossing', 'new_estw', 'new_dstw', 'noise_barrier',
        'overpass', 'gwb', 'buffer_track', 'simultaneous_train_entries', 'tilting',
        'effects_passenger_long_rail', 'effects_passenger_local_rail', 'effects_cargo_rail'
    ]
    for col in bool_columns:
        df[col] = df[col].apply(lambda x: x if x in [True, False, 1, 0, 'true', 'false'] else np.nan)
        df[col] = df[col].astype('boolean')
        df[col] = df[col].replace({pd.NA: False})
        df[col] = df[col].where(pd.notnull(df[col]), False)


    # check for str columns that should be converted to str
    str_columns = ['name', 'project_number', 'description']
    for col in str_columns:
        # replace all nan to None
        df[col] = df[col].where(pd.notnull(df[col]), None)

    df['geojson_representation'] = df['geojson_representation'].where(pd.notnull(df['geojson_representation']), None)
    df['centroid'] = df['centroid'].where(pd.notnull(df['centroid']), None)

    # start import into the database
    session = Session()

    if clear_db:
        session.query(Project).delete()
        session.commit()

    # import the df to the dabase
    for _, row in df.iterrows():
        # import the row to the schema
        try:
            data = ProjectSchema(**row.to_dict())
            project = Project(**data.model_dump(exclude_unset=True))
            session.add(project)
        except ValidationError as e:
            logging.error(f"Validation error for row with old_id {row['old_id']} and name {row['name']}: {e}")

    session.commit()

if __name__ == "__main__":
    filepath_csv = '../../data/old_db_import/prosd_prod_public_projects_contents.csv'
    import_project_content_old_db(filepath_csv, clear_db = True)
