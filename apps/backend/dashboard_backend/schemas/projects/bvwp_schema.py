from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class BvwpProjectDataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int

    # --- Grunddaten ---
    nkv: Optional[float] = None
    priority: Optional[str] = None
    reason_priority: Optional[str] = None
    bvwp_alternatives: Optional[str] = None
    bedarfsplan_nr: Optional[int] = None
    bottleneck_elimination: Optional[bool] = None

    # --- Kosten ---
    planned_total_cost: Optional[float] = None
    actual_cost: Optional[int] = None
    maintenance_cost: Optional[float] = None
    investment_cost: Optional[float] = None
    planning_cost: Optional[float] = None
    capital_service_cost: Optional[float] = None
    bvwp_planned_cost: Optional[float] = None
    bvwp_planned_maintenance_cost: Optional[float] = None
    bvwp_planned_planning_cost: Optional[float] = None
    bvwp_planned_planning_cost_incurred: Optional[float] = None
    bvwp_total_budget_relevant_cost: Optional[float] = None
    bvwp_total_budget_relevant_cost_incurred: Optional[float] = None
    bvwp_valuation_relevant_cost: Optional[float] = None
    bvwp_valuation_relevant_cost_pricelevel_2012: Optional[float] = None
    bvwp_valuation_relevant_cost_pricelevel_2012_planning_cost: Optional[float] = None
    bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cos: Optional[float] = None
    bvwp_valuation_relevant_cost_pricelevel_2012_present_value: Optional[float] = None

    # --- Verkehrsprognose Personenverkehr ---
    relocation_car_to_rail: Optional[float] = None
    relocation_rail_to_car: Optional[float] = None
    relocation_air_to_rail: Optional[float] = None
    induced_traffic: Optional[float] = None
    delta_car_km: Optional[float] = None
    delta_km_rail: Optional[float] = None
    delta_rail_running_time: Optional[float] = None
    delta_rail_km_rail: Optional[float] = None
    delta_rail_km_car_to_rail: Optional[float] = None
    delta_rail_km_rail_to_car: Optional[float] = None
    delta_rail_km_air_to_rail: Optional[float] = None
    delta_rail_km_induced: Optional[float] = None
    delta_travel_time_rail: Optional[float] = None
    delta_travel_time_car_to_rail: Optional[float] = None
    delta_travel_time_rail_to_car: Optional[float] = None
    delta_travel_time_air_to_rail: Optional[float] = None
    delta_travel_time_induced: Optional[float] = None

    # --- Verkehrsprognose Güterverkehr ---
    relocation_truck_to_rail: Optional[float] = None
    relocation_ship_to_rail: Optional[float] = None
    delta_truck_km: Optional[float] = None
    delta_truck_count: Optional[float] = None
    delta_rail_cargo_count: Optional[float] = None
    delta_rail_cargo_running_time: Optional[float] = None
    delta_rail_cargo_km_lkw_to_rail: Optional[float] = None
    delta_rail_cargo_km_ship_to_rail: Optional[float] = None
    delta_rail_cargo_time_rail: Optional[float] = None
    delta_rail_cargo_time_lkw_to_rail: Optional[float] = None
    delta_rail_cargo_time_ship_to_rail: Optional[float] = None

    # --- Nutzen Personenverkehr ---
    use_change_operation_cost_car_yearly: Optional[float] = None
    use_change_operating_cost_rail_yearly: Optional[float] = None
    use_change_operating_cost_air_yearly: Optional[float] = None
    use_change_pollution_car_yearly: Optional[float] = None
    use_change_pollution_rail_yearly: Optional[float] = None
    use_change_pollution_air_yearly: Optional[float] = None
    use_change_safety_car_yearly: Optional[float] = None
    use_change_safety_rail_yearly: Optional[float] = None
    use_change_travel_time_rail_yearly: Optional[float] = None
    use_change_travel_time_induced_yearly: Optional[float] = None
    use_change_travel_time_pkw_yearly: Optional[float] = None
    use_change_travel_time_air_yearly: Optional[float] = None
    use_change_travel_time_less_2min_yearly: Optional[float] = None
    use_change_implicit_benefit_induced_yearly: Optional[float] = None
    use_change_implicit_benefit_pkw_yearly: Optional[float] = None
    use_change_implicit_benefit_air_yearly: Optional[float] = None
    use_sum_passenger_yearly: Optional[float] = None
    use_change_operation_cost_car_present_value: Optional[float] = None
    use_change_operating_cost_rail_present_value: Optional[float] = None
    use_change_operating_cost_air_present_value: Optional[float] = None
    use_change_pollution_car_present_value: Optional[float] = None
    use_change_pollution_rail_present_value: Optional[float] = None
    use_change_pollution_air_present_value: Optional[float] = None
    use_change_safety_car_present_value: Optional[float] = None
    use_change_safety_rail_present_value: Optional[float] = None
    use_change_travel_time_rail_present_value: Optional[float] = None
    use_change_travel_time_induced_present_value: Optional[float] = None
    use_change_travel_time_pkw_present_value: Optional[float] = None
    use_change_travel_time_air_present_value: Optional[float] = None
    use_change_travel_time_less_2min_present_value: Optional[float] = None
    use_change_implicit_benefit_induced_present_value: Optional[float] = None
    use_change_implicit_benefit_pkw_present_value: Optional[float] = None
    use_change_implicit_benefit_air_present_value: Optional[float] = None
    use_sum_passenger_present_value: Optional[float] = None

    # --- Nutzen Güterverkehr ---
    use_change_operating_cost_truck_yearly: Optional[float] = None
    use_change_operating_cost_rail_cargo_yearly: Optional[float] = None
    use_change_operating_cost_ship_yearly: Optional[float] = None
    use_change_pollution_truck_yearly: Optional[float] = None
    use_change_pollution_rail_cargo_yearly: Optional[float] = None
    use_change_pollution_ship_yearly: Optional[float] = None
    use_change_safety_truck_yearly: Optional[float] = None
    use_change_safety_rail_cargo_yearly: Optional[float] = None
    use_change_safety_ship_yearly: Optional[float] = None
    use_change_running_time_rail_yearly: Optional[float] = None
    use_change_running_time_lkw_yearly: Optional[float] = None
    use_change_running_time_ship_yearly: Optional[float] = None
    use_change_implicit_benefit_truck_yearly: Optional[float] = None
    use_change_implicit_benefit_ship_yearly: Optional[float] = None
    use_change_reliability_yearly: Optional[float] = None
    use_sum_cargo_yearly: Optional[float] = None
    use_change_operating_cost_truck_present_value: Optional[float] = None
    use_change_operating_cost_rail_cargo_present_value: Optional[float] = None
    use_change_operating_cost_ship_present_value: Optional[float] = None
    use_change_pollution_truck_present_value: Optional[float] = None
    use_change_pollution_rail_cargo_present_value: Optional[float] = None
    use_change_pollution_ship_present_value: Optional[float] = None
    use_change_safety_truck_present_value: Optional[float] = None
    use_change_safety_rail_cargo_present_value: Optional[float] = None
    use_change_safety_ship_present_value: Optional[float] = None
    use_change_running_time_rail_present_value: Optional[float] = None
    use_change_running_time_lkw_present_value: Optional[float] = None
    use_change_running_time_ship_present_value: Optional[float] = None
    use_change_implicit_benefit_truck_present_value: Optional[float] = None
    use_change_implicit_benefit_ship_present_value: Optional[float] = None
    use_change_reliability_present_value: Optional[float] = None
    use_sum_cargo_present_value: Optional[float] = None

    # --- Weitere Nutzenwirkungen ---
    use_change_maintenance_cost_yearly: Optional[float] = None
    use_change_lcc_infrastructure_yearly: Optional[float] = None
    use_change_noise_intown_yearly: Optional[float] = None
    use_change_noise_outtown_yearly: Optional[float] = None
    sum_use_change_yearly: Optional[float] = None
    use_change_maintenance_cost_present_value: Optional[float] = None
    use_change_lcc_infrastructure_present_value: Optional[float] = None
    use_change_noise_intown_present_value: Optional[float] = None
    use_change_noise_outtown_present_value: Optional[float] = None
    sum_use_change_present_value: Optional[float] = None

    # --- Umwelt ---
    bvwp_environmental_impact: Optional[str] = None
    delta_nox: Optional[float] = None
    delta_co: Optional[float] = None
    delta_co2: Optional[float] = None
    delta_hc: Optional[float] = None
    delta_pm: Optional[float] = None
    delta_so2: Optional[float] = None
    bvwp_sum_use_environment: Optional[float] = None
    bvwp_sum_environmental_affectedness: Optional[str] = None
    bvwp_sum_environmental_affectedness_text: Optional[str] = None
    noise_new_affected: Optional[float] = None
    noise_relieved: Optional[float] = None
    change_noise_outtown: Optional[float] = None
    area_nature_high_importance: Optional[float] = None
    area_nature_high_importance_per_km: Optional[float] = None
    area_nature_high_importance_rating: Optional[str] = None
    natura2000_rating: Optional[str] = None
    natura2000_not_excluded: Optional[float] = None
    natura2000_probably: Optional[float] = None
    ufr_250: Optional[float] = None
    ufr_250_per_km: Optional[float] = None
    ufra_250_rating: Optional[str] = None
    bfn_rating: Optional[str] = None
    ufr_1000_undissacted_large_area: Optional[float] = None
    ufr_1000_undissacted_large_area_per_km: Optional[float] = None
    ufr_1000_undissacted_large_mammals: Optional[float] = None
    ufr_1000_undissacted_large_mammals_per_km: Optional[float] = None
    count_undissacted_area: Optional[float] = None
    count_reconnect_area: Optional[float] = None
    land_consumption: Optional[float] = None
    flooding_area: Optional[float] = None
    flooding_area_per_km: Optional[float] = None
    flooding_area_rating: Optional[str] = None
    water_protection_area: Optional[float] = None
    water_protection_area_per_km: Optional[float] = None
    water_protection_area_rating: Optional[str] = None
    uzvr: Optional[float] = None
    uvzr_rating: Optional[str] = None
    priortiy_area_landscape_protection: Optional[float] = None
    priority_area_landscape_protection_per_km: Optional[float] = None
    priority_area_landscape_protection_rating: Optional[str] = None
    environmental_additional_informations: Optional[str] = None

    # --- Raumordnung ---
    bvwp_regional_significance: Optional[str] = None
    spatial_significance_overall_result: Optional[str] = None
    spatial_significance_reasons: Optional[str] = None
    spatial_significance_street: Optional[str] = None
    spatial_significance_accessibility_deficits: Optional[str] = None
    spatial_significance_conclusion: Optional[str] = None

    # --- Kapazität ---
    bvwp_congested_rail_reference_6to9_km: Optional[float] = None
    bvwp_congested_rail_reference_6to9_perc: Optional[float] = None
    bvwp_congested_rail_plancase_6to9_km: Optional[float] = None
    bvwp_congested_rail_plancase_6to9_perc: Optional[float] = None
    bvwp_congested_rail_reference_9to16_km: Optional[float] = None
    bvwp_congested_rail_reference_9to16_perc: Optional[float] = None
    bvwp_congested_rail_plancase_9to16_km: Optional[float] = None
    bvwp_congested_rail_plancase_9to16_perc: Optional[float] = None
    bvwp_congested_rail_reference_16to19_km: Optional[float] = None
    bvwp_congested_rail_reference_16to19_perc: Optional[float] = None
    bvwp_congested_rail_plancase_16to19_km: Optional[float] = None
    bvwp_congested_rail_plancase_16to19_perc: Optional[float] = None
    bvwp_congested_rail_reference_19to22_km: Optional[float] = None
    bvwp_congested_rail_reference_19to22_perc: Optional[float] = None
    bvwp_congested_rail_plancase_19to22_km: Optional[float] = None
    bvwp_congested_rail_plancase_19to22_perc: Optional[float] = None
    bvwp_congested_rail_reference_22to6_km: Optional[float] = None
    bvwp_congested_rail_reference_22to6_perc: Optional[float] = None
    bvwp_congested_rail_plancase_22to6_km: Optional[float] = None
    bvwp_congested_rail_plancase_22to6_perc: Optional[float] = None
    bvwp_congested_rail_reference_day_km: Optional[float] = None
    bvwp_congested_rail_reference_day_perc: Optional[float] = None
    bvwp_congested_rail_plancase_day_km: Optional[float] = None
    bvwp_congested_rail_plancase_day_perc: Optional[float] = None
    bvwp_unscheduled_waiting_period_reference: Optional[float] = None
    bvwp_unscheduled_waiting_period_plancase: Optional[float] = None
    bvwp_punctuality_cargo_reference: Optional[float] = None
    bvwp_delta_punctuality_relativ: Optional[float] = None
    bvwp_delta_punctuality_absolut: Optional[float] = None

    # --- Reisezeitbeispiele & Sonstiges ---
    traveltime_reduction: Optional[float] = None
    bvwp_traveltime_examples: Optional[str] = None
    bvwp_duration_of_outstanding_planning: Optional[float] = None
    bvwp_duration_of_build: Optional[float] = None
    bvwp_duration_operating: Optional[float] = None
    bvwp_additional_informations: Optional[str] = None
