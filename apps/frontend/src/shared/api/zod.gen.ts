import { makeApi, Zodios, type ZodiosOptions } from "@zodios/core";
import { z } from "zod";

const SessionCredentials = z
  .object({ username: z.string(), password: z.string() })
  .passthrough();
const ValidationError = z
  .object({
    loc: z.array(z.union([z.string(), z.number()])),
    msg: z.string(),
    type: z.string(),
    input: z.unknown().optional(),
    ctx: z.object({}).partial().passthrough().optional(),
  })
  .passthrough();
const HTTPValidationError = z
  .object({ detail: z.array(ValidationError) })
  .partial()
  .passthrough();
const RouteRequest = z
  .object({ start_op: z.string(), end_op: z.string() })
  .passthrough();
const RouteResponse = z
  .object({ sectionofline_ids: z.array(z.number().int()) })
  .passthrough();
const ProjectSchema = z
  .object({
    id: z.union([z.number(), z.null()]).optional(),
    name: z.string(),
    project_number: z.union([z.string(), z.null()]).optional(),
    superior_project_id: z.union([z.number(), z.null()]).optional(),
    old_id: z.union([z.number(), z.null()]).optional(),
    superior_project_old_id: z.union([z.number(), z.null()]).optional(),
    description: z.union([z.string(), z.null()]).optional(),
    justification: z.union([z.string(), z.null()]).optional(),
    effects_passenger_long_rail: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(false),
    effects_passenger_local_rail: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(false),
    effects_cargo_rail: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(false),
    length: z.union([z.number(), z.null()]),
    nbs: z.boolean().optional().default(false),
    abs: z.boolean().optional().default(false),
    elektrification: z.boolean().optional().default(false),
    charging_station: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(false),
    small_charging_station: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(false),
    second_track: z.boolean().optional().default(false),
    third_track: z.boolean().optional().default(false),
    fourth_track: z.boolean().optional().default(false),
    curve: z.boolean().optional().default(false),
    platform: z.boolean().optional().default(false),
    junction_station: z.boolean().optional().default(false),
    number_junction_station: z.union([z.number(), z.null()]),
    overtaking_station: z.boolean().optional().default(false),
    number_overtaking_station: z.union([z.number(), z.null()]),
    double_occupancy: z.boolean().optional().default(false),
    block_increase: z.boolean().optional().default(false),
    flying_junction: z.boolean().optional().default(false),
    tunnel_structural_gauge: z.boolean().optional().default(false),
    increase_speed: z.boolean().optional().default(false),
    new_vmax: z.union([z.number(), z.null()]),
    level_free_platform_entrance: z.boolean().optional().default(false),
    etcs: z.boolean().optional().default(false),
    etcs_level: z.union([z.number(), z.null()]),
    station_railroad_switches: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(false),
    new_station: z.union([z.boolean(), z.null()]).optional().default(false),
    depot: z.union([z.boolean(), z.null()]).optional().default(false),
    battery: z.union([z.boolean(), z.null()]).optional().default(false),
    h2: z.union([z.boolean(), z.null()]).optional().default(false),
    efuel: z.union([z.boolean(), z.null()]).optional().default(false),
    closure: z.union([z.boolean(), z.null()]).optional().default(false),
    optimised_electrification: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(false),
    filling_stations_efuel: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(false),
    filling_stations_h2: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(false),
    filling_stations_diesel: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(false),
    filling_stations_count: z
      .union([z.number(), z.null()])
      .optional()
      .default(0),
    sanierung: z.union([z.boolean(), z.null()]).optional().default(false),
    sgv740m: z.union([z.boolean(), z.null()]).optional().default(false),
    railroad_crossing: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(false),
    new_estw: z.union([z.boolean(), z.null()]).optional().default(false),
    new_dstw: z.union([z.boolean(), z.null()]).optional().default(false),
    noise_barrier: z.union([z.boolean(), z.null()]).optional().default(false),
    overpass: z.union([z.boolean(), z.null()]).optional().default(false),
    buffer_track: z.union([z.boolean(), z.null()]).optional().default(false),
    gwb: z.union([z.boolean(), z.null()]).optional().default(false),
    simultaneous_train_entries: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(false),
    tilting: z.union([z.boolean(), z.null()]).optional().default(false),
    geojson_representation: z.union([z.string(), z.null()]).optional(),
    centroid: z.union([z.unknown(), z.null()]).optional(),
  })
  .passthrough();
const ProjectUpdate = z
  .object({
    name: z.union([z.string(), z.null()]),
    project_number: z.union([z.string(), z.null()]),
    description: z.union([z.string(), z.null()]),
    justification: z.union([z.string(), z.null()]),
    superior_project_id: z.union([z.number(), z.null()]),
    effects_passenger_long_rail: z.union([z.boolean(), z.null()]),
    effects_passenger_local_rail: z.union([z.boolean(), z.null()]),
    effects_cargo_rail: z.union([z.boolean(), z.null()]),
    length: z.union([z.number(), z.null()]),
    nbs: z.union([z.boolean(), z.null()]),
    abs: z.union([z.boolean(), z.null()]),
    elektrification: z.union([z.boolean(), z.null()]),
    charging_station: z.union([z.boolean(), z.null()]),
    small_charging_station: z.union([z.boolean(), z.null()]),
    second_track: z.union([z.boolean(), z.null()]),
    third_track: z.union([z.boolean(), z.null()]),
    fourth_track: z.union([z.boolean(), z.null()]),
    curve: z.union([z.boolean(), z.null()]),
    platform: z.union([z.boolean(), z.null()]),
    junction_station: z.union([z.boolean(), z.null()]),
    number_junction_station: z.union([z.number(), z.null()]),
    overtaking_station: z.union([z.boolean(), z.null()]),
    number_overtaking_station: z.union([z.number(), z.null()]),
    double_occupancy: z.union([z.boolean(), z.null()]),
    block_increase: z.union([z.boolean(), z.null()]),
    flying_junction: z.union([z.boolean(), z.null()]),
    tunnel_structural_gauge: z.union([z.boolean(), z.null()]),
    increase_speed: z.union([z.boolean(), z.null()]),
    new_vmax: z.union([z.number(), z.null()]),
    level_free_platform_entrance: z.union([z.boolean(), z.null()]),
    etcs: z.union([z.boolean(), z.null()]),
    etcs_level: z.union([z.number(), z.null()]),
    station_railroad_switches: z.union([z.boolean(), z.null()]),
    new_station: z.union([z.boolean(), z.null()]),
    depot: z.union([z.boolean(), z.null()]),
    battery: z.union([z.boolean(), z.null()]),
    h2: z.union([z.boolean(), z.null()]),
    efuel: z.union([z.boolean(), z.null()]),
    closure: z.union([z.boolean(), z.null()]),
    optimised_electrification: z.union([z.boolean(), z.null()]),
    filling_stations_efuel: z.union([z.boolean(), z.null()]),
    filling_stations_h2: z.union([z.boolean(), z.null()]),
    filling_stations_diesel: z.union([z.boolean(), z.null()]),
    filling_stations_count: z.union([z.number(), z.null()]),
    sanierung: z.union([z.boolean(), z.null()]),
    sgv740m: z.union([z.boolean(), z.null()]),
    railroad_crossing: z.union([z.boolean(), z.null()]),
    new_estw: z.union([z.boolean(), z.null()]),
    new_dstw: z.union([z.boolean(), z.null()]),
    noise_barrier: z.union([z.boolean(), z.null()]),
    overpass: z.union([z.boolean(), z.null()]),
    buffer_track: z.union([z.boolean(), z.null()]),
    gwb: z.union([z.boolean(), z.null()]),
    simultaneous_train_entries: z.union([z.boolean(), z.null()]),
    tilting: z.union([z.boolean(), z.null()]),
    geojson_representation: z.union([z.string(), z.null()]),
  })
  .partial()
  .passthrough();
const BvwpProjectDataSchema = z
  .object({
    id: z.number().int(),
    project_id: z.number().int(),
    nkv: z.union([z.number(), z.null()]).optional(),
    priority: z.union([z.string(), z.null()]).optional(),
    reason_priority: z.union([z.string(), z.null()]).optional(),
    bvwp_alternatives: z.union([z.string(), z.null()]).optional(),
    bedarfsplan_nr: z.union([z.number(), z.null()]).optional(),
    bottleneck_elimination: z.union([z.boolean(), z.null()]).optional(),
    planned_total_cost: z.union([z.number(), z.null()]).optional(),
    actual_cost: z.union([z.number(), z.null()]).optional(),
    maintenance_cost: z.union([z.number(), z.null()]).optional(),
    investment_cost: z.union([z.number(), z.null()]).optional(),
    planning_cost: z.union([z.number(), z.null()]).optional(),
    capital_service_cost: z.union([z.number(), z.null()]).optional(),
    bvwp_planned_cost: z.union([z.number(), z.null()]).optional(),
    bvwp_planned_maintenance_cost: z.union([z.number(), z.null()]).optional(),
    bvwp_planned_planning_cost: z.union([z.number(), z.null()]).optional(),
    bvwp_planned_planning_cost_incurred: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_total_budget_relevant_cost: z.union([z.number(), z.null()]).optional(),
    bvwp_total_budget_relevant_cost_incurred: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_valuation_relevant_cost: z.union([z.number(), z.null()]).optional(),
    bvwp_valuation_relevant_cost_pricelevel_2012: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_valuation_relevant_cost_pricelevel_2012_planning_cost: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cos: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_valuation_relevant_cost_pricelevel_2012_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    relocation_car_to_rail: z.union([z.number(), z.null()]).optional(),
    relocation_rail_to_car: z.union([z.number(), z.null()]).optional(),
    relocation_air_to_rail: z.union([z.number(), z.null()]).optional(),
    induced_traffic: z.union([z.number(), z.null()]).optional(),
    delta_car_km: z.union([z.number(), z.null()]).optional(),
    delta_km_rail: z.union([z.number(), z.null()]).optional(),
    delta_rail_running_time: z.union([z.number(), z.null()]).optional(),
    delta_rail_km_rail: z.union([z.number(), z.null()]).optional(),
    delta_rail_km_car_to_rail: z.union([z.number(), z.null()]).optional(),
    delta_rail_km_rail_to_car: z.union([z.number(), z.null()]).optional(),
    delta_rail_km_air_to_rail: z.union([z.number(), z.null()]).optional(),
    delta_rail_km_induced: z.union([z.number(), z.null()]).optional(),
    delta_travel_time_rail: z.union([z.number(), z.null()]).optional(),
    delta_travel_time_car_to_rail: z.union([z.number(), z.null()]).optional(),
    delta_travel_time_rail_to_car: z.union([z.number(), z.null()]).optional(),
    delta_travel_time_air_to_rail: z.union([z.number(), z.null()]).optional(),
    delta_travel_time_induced: z.union([z.number(), z.null()]).optional(),
    relocation_truck_to_rail: z.union([z.number(), z.null()]).optional(),
    relocation_ship_to_rail: z.union([z.number(), z.null()]).optional(),
    delta_truck_km: z.union([z.number(), z.null()]).optional(),
    delta_truck_count: z.union([z.number(), z.null()]).optional(),
    delta_rail_cargo_count: z.union([z.number(), z.null()]).optional(),
    delta_rail_cargo_running_time: z.union([z.number(), z.null()]).optional(),
    delta_rail_cargo_km_lkw_to_rail: z.union([z.number(), z.null()]).optional(),
    delta_rail_cargo_km_ship_to_rail: z
      .union([z.number(), z.null()])
      .optional(),
    delta_rail_cargo_time_rail: z.union([z.number(), z.null()]).optional(),
    delta_rail_cargo_time_lkw_to_rail: z
      .union([z.number(), z.null()])
      .optional(),
    delta_rail_cargo_time_ship_to_rail: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_operation_cost_car_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_operating_cost_rail_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_operating_cost_air_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_pollution_car_yearly: z.union([z.number(), z.null()]).optional(),
    use_change_pollution_rail_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_pollution_air_yearly: z.union([z.number(), z.null()]).optional(),
    use_change_safety_car_yearly: z.union([z.number(), z.null()]).optional(),
    use_change_safety_rail_yearly: z.union([z.number(), z.null()]).optional(),
    use_change_travel_time_rail_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_travel_time_induced_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_travel_time_pkw_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_travel_time_air_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_travel_time_less_2min_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_implicit_benefit_induced_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_implicit_benefit_pkw_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_implicit_benefit_air_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_sum_passenger_yearly: z.union([z.number(), z.null()]).optional(),
    use_change_operation_cost_car_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_operating_cost_rail_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_operating_cost_air_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_pollution_car_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_pollution_rail_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_pollution_air_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_safety_car_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_safety_rail_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_travel_time_rail_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_travel_time_induced_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_travel_time_pkw_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_travel_time_air_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_travel_time_less_2min_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_implicit_benefit_induced_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_implicit_benefit_pkw_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_implicit_benefit_air_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_sum_passenger_present_value: z.union([z.number(), z.null()]).optional(),
    use_change_operating_cost_truck_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_operating_cost_rail_cargo_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_operating_cost_ship_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_pollution_truck_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_pollution_rail_cargo_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_pollution_ship_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_safety_truck_yearly: z.union([z.number(), z.null()]).optional(),
    use_change_safety_rail_cargo_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_safety_ship_yearly: z.union([z.number(), z.null()]).optional(),
    use_change_running_time_rail_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_running_time_lkw_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_running_time_ship_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_implicit_benefit_truck_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_implicit_benefit_ship_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_reliability_yearly: z.union([z.number(), z.null()]).optional(),
    use_sum_cargo_yearly: z.union([z.number(), z.null()]).optional(),
    use_change_operating_cost_truck_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_operating_cost_rail_cargo_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_operating_cost_ship_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_pollution_truck_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_pollution_rail_cargo_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_pollution_ship_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_safety_truck_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_safety_rail_cargo_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_safety_ship_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_running_time_rail_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_running_time_lkw_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_running_time_ship_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_implicit_benefit_truck_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_implicit_benefit_ship_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_reliability_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_sum_cargo_present_value: z.union([z.number(), z.null()]).optional(),
    use_change_maintenance_cost_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_lcc_infrastructure_yearly: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_noise_intown_yearly: z.union([z.number(), z.null()]).optional(),
    use_change_noise_outtown_yearly: z.union([z.number(), z.null()]).optional(),
    sum_use_change_yearly: z.union([z.number(), z.null()]).optional(),
    use_change_maintenance_cost_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_lcc_infrastructure_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_noise_intown_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    use_change_noise_outtown_present_value: z
      .union([z.number(), z.null()])
      .optional(),
    sum_use_change_present_value: z.union([z.number(), z.null()]).optional(),
    bvwp_environmental_impact: z.union([z.string(), z.null()]).optional(),
    delta_nox: z.union([z.number(), z.null()]).optional(),
    delta_co: z.union([z.number(), z.null()]).optional(),
    delta_co2: z.union([z.number(), z.null()]).optional(),
    delta_hc: z.union([z.number(), z.null()]).optional(),
    delta_pm: z.union([z.number(), z.null()]).optional(),
    delta_so2: z.union([z.number(), z.null()]).optional(),
    bvwp_sum_use_environment: z.union([z.number(), z.null()]).optional(),
    bvwp_sum_environmental_affectedness: z
      .union([z.string(), z.null()])
      .optional(),
    bvwp_sum_environmental_affectedness_text: z
      .union([z.string(), z.null()])
      .optional(),
    noise_new_affected: z.union([z.number(), z.null()]).optional(),
    noise_relieved: z.union([z.number(), z.null()]).optional(),
    change_noise_outtown: z.union([z.number(), z.null()]).optional(),
    area_nature_high_importance: z.union([z.number(), z.null()]).optional(),
    area_nature_high_importance_per_km: z
      .union([z.number(), z.null()])
      .optional(),
    area_nature_high_importance_rating: z
      .union([z.string(), z.null()])
      .optional(),
    natura2000_rating: z.union([z.string(), z.null()]).optional(),
    natura2000_not_excluded: z.union([z.number(), z.null()]).optional(),
    natura2000_probably: z.union([z.number(), z.null()]).optional(),
    ufr_250: z.union([z.number(), z.null()]).optional(),
    ufr_250_per_km: z.union([z.number(), z.null()]).optional(),
    ufra_250_rating: z.union([z.string(), z.null()]).optional(),
    bfn_rating: z.union([z.string(), z.null()]).optional(),
    ufr_1000_undissacted_large_area: z.union([z.number(), z.null()]).optional(),
    ufr_1000_undissacted_large_area_per_km: z
      .union([z.number(), z.null()])
      .optional(),
    ufr_1000_undissacted_large_mammals: z
      .union([z.number(), z.null()])
      .optional(),
    ufr_1000_undissacted_large_mammals_per_km: z
      .union([z.number(), z.null()])
      .optional(),
    count_undissacted_area: z.union([z.number(), z.null()]).optional(),
    count_reconnect_area: z.union([z.number(), z.null()]).optional(),
    land_consumption: z.union([z.number(), z.null()]).optional(),
    flooding_area: z.union([z.number(), z.null()]).optional(),
    flooding_area_per_km: z.union([z.number(), z.null()]).optional(),
    flooding_area_rating: z.union([z.string(), z.null()]).optional(),
    water_protection_area: z.union([z.number(), z.null()]).optional(),
    water_protection_area_per_km: z.union([z.number(), z.null()]).optional(),
    water_protection_area_rating: z.union([z.string(), z.null()]).optional(),
    uzvr: z.union([z.number(), z.null()]).optional(),
    uvzr_rating: z.union([z.string(), z.null()]).optional(),
    priortiy_area_landscape_protection: z
      .union([z.number(), z.null()])
      .optional(),
    priority_area_landscape_protection_per_km: z
      .union([z.number(), z.null()])
      .optional(),
    priority_area_landscape_protection_rating: z
      .union([z.string(), z.null()])
      .optional(),
    environmental_additional_informations: z
      .union([z.string(), z.null()])
      .optional(),
    bvwp_regional_significance: z.union([z.string(), z.null()]).optional(),
    spatial_significance_overall_result: z
      .union([z.string(), z.null()])
      .optional(),
    spatial_significance_reasons: z.union([z.string(), z.null()]).optional(),
    spatial_significance_street: z.union([z.string(), z.null()]).optional(),
    spatial_significance_accessibility_deficits: z
      .union([z.string(), z.null()])
      .optional(),
    spatial_significance_conclusion: z.union([z.string(), z.null()]).optional(),
    bvwp_congested_rail_reference_6to9_km: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_reference_6to9_perc: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_plancase_6to9_km: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_plancase_6to9_perc: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_reference_9to16_km: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_reference_9to16_perc: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_plancase_9to16_km: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_plancase_9to16_perc: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_reference_16to19_km: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_reference_16to19_perc: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_plancase_16to19_km: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_plancase_16to19_perc: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_reference_19to22_km: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_reference_19to22_perc: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_plancase_19to22_km: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_plancase_19to22_perc: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_reference_22to6_km: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_reference_22to6_perc: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_plancase_22to6_km: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_plancase_22to6_perc: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_reference_day_km: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_reference_day_perc: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_plancase_day_km: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_congested_rail_plancase_day_perc: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_unscheduled_waiting_period_reference: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_unscheduled_waiting_period_plancase: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_punctuality_cargo_reference: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_delta_punctuality_relativ: z.union([z.number(), z.null()]).optional(),
    bvwp_delta_punctuality_absolut: z.union([z.number(), z.null()]).optional(),
    traveltime_reduction: z.union([z.number(), z.null()]).optional(),
    bvwp_traveltime_examples: z.union([z.string(), z.null()]).optional(),
    bvwp_duration_of_outstanding_planning: z
      .union([z.number(), z.null()])
      .optional(),
    bvwp_duration_of_build: z.union([z.number(), z.null()]).optional(),
    bvwp_duration_operating: z.union([z.number(), z.null()]).optional(),
    bvwp_additional_informations: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const TitelEntrySchema = z
  .object({
    titel_key: z.string(),
    kapitel: z.string(),
    titel_nr: z.string(),
    label: z.string(),
    is_nachrichtlich: z.boolean(),
    cost_estimate_last_year: z.union([z.number(), z.null()]).optional(),
    cost_estimate_aktuell: z.union([z.number(), z.null()]).optional(),
    verausgabt_bis: z.union([z.number(), z.null()]).optional(),
    bewilligt: z.union([z.number(), z.null()]).optional(),
    ausgabereste_transferred: z.union([z.number(), z.null()]).optional(),
    veranschlagt: z.union([z.number(), z.null()]).optional(),
    vorhalten_future: z.union([z.number(), z.null()]).optional(),
  })
  .passthrough();
const BudgetSummarySchema = z
  .object({
    budget_year: z.number().int(),
    lfd_nr: z.union([z.string(), z.null()]).optional(),
    bedarfsplan_number: z.union([z.string(), z.null()]).optional(),
    cost_estimate_original: z.union([z.number(), z.null()]).optional(),
    cost_estimate_last_year: z.union([z.number(), z.null()]).optional(),
    cost_estimate_actual: z.union([z.number(), z.null()]).optional(),
    delta_previous_year: z.union([z.number(), z.null()]).optional(),
    delta_previous_year_relativ: z.union([z.number(), z.null()]).optional(),
    spent_two_years_previous: z.union([z.number(), z.null()]).optional(),
    allowed_previous_year: z.union([z.number(), z.null()]).optional(),
    spending_residues: z.union([z.number(), z.null()]).optional(),
    year_planned: z.union([z.number(), z.null()]).optional(),
    next_years: z.union([z.number(), z.null()]).optional(),
    titel_entries: z.array(TitelEntrySchema).optional().default([]),
  })
  .passthrough();
const FinveWithBudgetsSchema = z
  .object({
    id: z.number().int(),
    name: z.union([z.string(), z.null()]).optional(),
    starting_year: z.union([z.number(), z.null()]).optional(),
    cost_estimate_original: z.union([z.number(), z.null()]).optional(),
    is_sammel_finve: z.boolean().optional().default(false),
    budgets: z.array(BudgetSummarySchema).optional().default([]),
  })
  .passthrough();
const ChangeLogEntryRead = z
  .object({
    id: z.number().int(),
    field_name: z.string(),
    old_value: z.union([z.string(), z.null()]).optional(),
    new_value: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const ChangeLogRead = z
  .object({
    id: z.number().int(),
    project_id: z.number().int(),
    user_id: z.union([z.number(), z.null()]).optional(),
    username_snapshot: z.union([z.string(), z.null()]).optional(),
    timestamp: z.string().datetime({ offset: true }),
    action: z.string(),
    entries: z.array(ChangeLogEntryRead).optional().default([]),
  })
  .passthrough();
const RevertFieldRequest = z
  .object({ changelog_entry_id: z.number().int() })
  .passthrough();
const ProjectGroupSchema = z
  .object({
    id: z.union([z.number(), z.null()]).optional(),
    name: z.string(),
    short_name: z.string(),
    description: z.union([z.string(), z.null()]).optional(),
    public: z.boolean().optional().default(false),
    color: z.string().optional().default("#FF0000"),
    plot_only_superior_projects: z.boolean().optional().default(true),
    is_visible: z.boolean().optional().default(true),
    is_default_selected: z.boolean().optional().default(false),
    id_old: z.union([z.number(), z.null()]).optional(),
    projects: z.array(ProjectSchema).optional(),
  })
  .passthrough();
const ProjectGroupUpdate = z
  .object({
    is_visible: z.union([z.boolean(), z.null()]),
    is_default_selected: z.union([z.boolean(), z.null()]),
  })
  .partial()
  .passthrough();
const UserRole = z.enum(["viewer", "editor", "admin"]);
const UserRead = z
  .object({
    username: z.string().min(3).max(50),
    role: UserRole,
    id: z.number().int(),
    created_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const UserCreate = z
  .object({
    username: z.string().min(3).max(50),
    role: UserRole,
    password: z.string().min(8).max(128),
  })
  .passthrough();
const UserUpdate = z.object({ role: UserRole }).passthrough();
const UserPasswordUpdate = z
  .object({ password: z.string().min(8).max(128) })
  .passthrough();
const Waypoint = z
  .object({
    lat: z.number().gte(-90).lte(90),
    lon: z.number().gte(-180).lte(180),
  })
  .passthrough();
const RouteIn = z
  .object({
    waypoints: z.array(Waypoint).min(2),
    profile: z.string().optional().default("rail_default"),
    options: z.object({}).partial().passthrough().optional(),
  })
  .passthrough();
const RoutePreviewOut = z
  .object({
    type: z.string().optional().default("Feature"),
    geometry: z.object({}).partial().passthrough(),
    properties: z.object({}).partial().passthrough(),
  })
  .passthrough();
const RouteConfirmIn = z
  .object({ feature: z.object({}).partial().passthrough() })
  .passthrough();
const RouteOut = z
  .object({
    route_id: z.string().uuid(),
    project_id: z.string().uuid(),
    distance_m: z.number(),
    duration_ms: z.number().int(),
    bbox: z.array(z.number()),
    geom_geojson: z.object({}).partial().passthrough(),
    details: z.object({}).partial().passthrough(),
  })
  .passthrough();
const ProjectTextTypeSchema = z
  .object({ id: z.number().int(), name: z.string() })
  .passthrough();
const ProjectTextTypeCreate = z.object({ name: z.string() }).passthrough();
const ProjectTextSchema = z
  .object({
    id: z.number().int(),
    header: z.string(),
    weblink: z.union([z.string(), z.null()]).optional(),
    text: z.union([z.string(), z.null()]).optional(),
    type: z.number().int(),
    logo_url: z.union([z.string(), z.null()]).optional(),
    created_at: z.number().int(),
    updated_at: z.number().int(),
    text_type: ProjectTextTypeSchema,
  })
  .passthrough();
const ProjectTextCreate = z
  .object({
    header: z.string(),
    weblink: z.union([z.string(), z.null()]).optional(),
    text: z.union([z.string(), z.null()]).optional(),
    type: z.number().int(),
    logo_url: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const TextChangeLogEntryRead = z
  .object({
    id: z.number().int(),
    field_name: z.string(),
    old_value: z.union([z.string(), z.null()]).optional(),
    new_value: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const TextChangeLogRead = z
  .object({
    id: z.number().int(),
    text_id: z.union([z.number(), z.null()]).optional(),
    project_id: z.union([z.number(), z.null()]).optional(),
    user_id: z.union([z.number(), z.null()]).optional(),
    username_snapshot: z.union([z.string(), z.null()]).optional(),
    text_header_snapshot: z.union([z.string(), z.null()]).optional(),
    timestamp: z.string().datetime({ offset: true }),
    action: z.string(),
    entries: z.array(TextChangeLogEntryRead).optional().default([]),
  })
  .passthrough();
const ProjectTextUpdate = z
  .object({
    header: z.union([z.string(), z.null()]),
    weblink: z.union([z.string(), z.null()]),
    text: z.union([z.string(), z.null()]),
    type: z.union([z.number(), z.null()]),
    logo_url: z.union([z.string(), z.null()]),
  })
  .partial()
  .passthrough();
const TaskStatusResponse = z
  .object({
    task_id: z.string(),
    status: z.string(),
    result: z.unknown().optional(),
    error: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const DebugTaskRequest = z
  .object({ x: z.number().int(), y: z.number().int() })
  .passthrough();
const TaskLaunchResponse = z.object({ task_id: z.string() }).passthrough();
const Body_start_parse_api_v1_import_haushalt_parse_post = z
  .object({ pdf: z.string(), year: z.number().int() })
  .passthrough();
const ParseResultPublicSchema = z
  .object({
    id: z.number().int(),
    haushalt_year: z.number().int(),
    pdf_filename: z.string(),
    parsed_at: z.string().datetime({ offset: true }),
    username_snapshot: z.union([z.string(), z.null()]).optional(),
    status: z.string(),
    error_message: z.union([z.string(), z.null()]).optional(),
    confirmed_at: z.union([z.string(), z.null()]).optional(),
    confirmed_by_snapshot: z.union([z.string(), z.null()]).optional(),
    result_json: z
      .union([z.object({}).partial().passthrough(), z.null()])
      .optional(),
  })
  .passthrough();
const ProposedFinve = z
  .object({
    id: z.number().int(),
    name: z.string(),
    starting_year: z.union([z.number(), z.null()]).optional(),
    cost_estimate_original: z.union([z.number(), z.null()]).optional(),
    is_sammel_finve: z.boolean().optional().default(false),
  })
  .passthrough();
const ProposedBudget = z
  .object({
    budget_year: z.number().int(),
    lfd_nr: z.union([z.string(), z.null()]).optional(),
    fin_ve: z.number().int(),
    bedarfsplan_number: z.union([z.string(), z.null()]).optional(),
    cost_estimate_original: z.union([z.number(), z.null()]).optional(),
    cost_estimate_last_year: z.union([z.number(), z.null()]).optional(),
    cost_estimate_actual: z.union([z.number(), z.null()]).optional(),
    delta_previous_year: z.union([z.number(), z.null()]).optional(),
    delta_previous_year_relativ: z.union([z.number(), z.null()]).optional(),
    delta_previous_year_reasons: z.union([z.string(), z.null()]).optional(),
    spent_two_years_previous: z.union([z.number(), z.null()]).optional(),
    allowed_previous_year: z.union([z.number(), z.null()]).optional(),
    spending_residues: z.union([z.number(), z.null()]).optional(),
    year_planned: z.union([z.number(), z.null()]).optional(),
    next_years: z.union([z.number(), z.null()]).optional(),
    sammel_finve: z.boolean().optional().default(false),
  })
  .passthrough();
const TitelEntryProposed = z
  .object({
    titel_key: z.string(),
    kapitel: z.string(),
    titel_nr: z.string(),
    label: z.string(),
    is_nachrichtlich: z.boolean().optional().default(false),
    cost_estimate_last_year: z.union([z.number(), z.null()]).optional(),
    cost_estimate_aktuell: z.union([z.number(), z.null()]).optional(),
    verausgabt_bis: z.union([z.number(), z.null()]).optional(),
    bewilligt: z.union([z.number(), z.null()]).optional(),
    ausgabereste_transferred: z.union([z.number(), z.null()]).optional(),
    veranschlagt: z.union([z.number(), z.null()]).optional(),
    vorhalten_future: z.union([z.number(), z.null()]).optional(),
  })
  .passthrough();
const HaushaltsConfirmRowInput = z
  .object({
    finve_number: z.number().int(),
    status: z.string(),
    is_sammel_finve: z.boolean().optional().default(false),
    erlaeuterung_projects: z.array(z.string()).optional().default([]),
    erlaeuterung_suggestions: z
      .array(z.union([z.number(), z.null()]))
      .optional()
      .default([]),
    proposed_finve: z.union([ProposedFinve, z.null()]).optional(),
    proposed_budget: z.union([ProposedBudget, z.null()]).optional(),
    proposed_titel_entries: z.array(TitelEntryProposed).optional().default([]),
    project_ids: z.array(z.number().int()).optional().default([]),
  })
  .passthrough();
const HaushaltsConfirmRequest = z
  .object({
    parse_result_id: z.number().int(),
    rows: z.array(HaushaltsConfirmRowInput).optional().default([]),
    unmatched_action: z.enum(["save", "discard"]).optional().default("save"),
  })
  .passthrough();
const HaushaltsConfirmResponse = z
  .object({
    finves_created: z.number().int(),
    finves_updated: z.number().int(),
    budgets_created: z.number().int(),
    budgets_updated: z.number().int(),
    unmatched_saved: z.number().int(),
  })
  .passthrough();
const resolved = z.union([z.boolean(), z.null()]).optional();
const UnmatchedBudgetRowSchema = z
  .object({
    id: z.number().int(),
    haushalt_year: z.number().int(),
    raw_finve_number: z.string(),
    raw_name: z.string(),
    raw_data: z
      .union([z.object({}).partial().passthrough(), z.null()])
      .optional(),
    resolved: z.boolean(),
    resolved_finve_id: z.union([z.number(), z.null()]).optional(),
    resolved_at: z.union([z.string(), z.null()]).optional(),
    resolved_by_snapshot: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const UnmatchedBudgetRowResolveRequest = z
  .object({ finve_id: z.number().int() })
  .passthrough();
const ProjectRefSchema = z
  .object({ id: z.number().int(), name: z.string() })
  .passthrough();
const FinveListItemSchema = z
  .object({
    id: z.number().int(),
    name: z.union([z.string(), z.null()]).optional(),
    starting_year: z.union([z.number(), z.null()]).optional(),
    cost_estimate_original: z.union([z.number(), z.null()]).optional(),
    is_sammel_finve: z.boolean(),
    temporary_finve_number: z.boolean(),
    project_count: z.number().int(),
    project_names: z.array(z.string()),
    projects: z.array(ProjectRefSchema).optional().default([]),
    budgets: z.array(BudgetSummarySchema).optional().default([]),
  })
  .passthrough();
const AppSettingsSchema = z
  .object({
    map_group_mode: z.enum(["preconfigured", "all"]).default("preconfigured"),
  })
  .partial()
  .passthrough();
const AppSettingsUpdate = z
  .object({ map_group_mode: z.enum(["preconfigured", "all"]) })
  .passthrough();

export const schemas = {
  SessionCredentials,
  ValidationError,
  HTTPValidationError,
  RouteRequest,
  RouteResponse,
  ProjectSchema,
  ProjectUpdate,
  BvwpProjectDataSchema,
  TitelEntrySchema,
  BudgetSummarySchema,
  FinveWithBudgetsSchema,
  ChangeLogEntryRead,
  ChangeLogRead,
  RevertFieldRequest,
  ProjectGroupSchema,
  ProjectGroupUpdate,
  UserRole,
  UserRead,
  UserCreate,
  UserUpdate,
  UserPasswordUpdate,
  Waypoint,
  RouteIn,
  RoutePreviewOut,
  RouteConfirmIn,
  RouteOut,
  ProjectTextTypeSchema,
  ProjectTextTypeCreate,
  ProjectTextSchema,
  ProjectTextCreate,
  TextChangeLogEntryRead,
  TextChangeLogRead,
  ProjectTextUpdate,
  TaskStatusResponse,
  DebugTaskRequest,
  TaskLaunchResponse,
  Body_start_parse_api_v1_import_haushalt_parse_post,
  ParseResultPublicSchema,
  ProposedFinve,
  ProposedBudget,
  TitelEntryProposed,
  HaushaltsConfirmRowInput,
  HaushaltsConfirmRequest,
  HaushaltsConfirmResponse,
  resolved,
  UnmatchedBudgetRowSchema,
  UnmatchedBudgetRowResolveRequest,
  ProjectRefSchema,
  FinveListItemSchema,
  AppSettingsSchema,
  AppSettingsUpdate,
};

const endpoints = makeApi([
  {
    method: "post",
    path: "/api/v1/auth/session",
    alias: "create_session_api_v1_auth_session_post",
    description: `Validate credentials and issue an httpOnly session cookie.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: SessionCredentials,
      },
    ],
    response: z.void(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/auth/session",
    alias: "delete_session_api_v1_auth_session_delete",
    description: `Clear the session cookie (logout).`,
    requestFormat: "json",
    response: z.void(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/finves/",
    alias: "get_finves_api_v1_finves__get",
    description: `Return all Finanzierungsvereinbarungen with linked project info.`,
    requestFormat: "json",
    response: z.array(FinveListItemSchema),
  },
  {
    method: "post",
    path: "/api/v1/import/haushalt/confirm",
    alias: "confirm_import_api_v1_import_haushalt_confirm_post",
    description: `Confirm a parse result and import Finve/Budget data.

Guard: if the parse result is already confirmed, returns 409 Conflict.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: HaushaltsConfirmRequest,
      },
    ],
    response: HaushaltsConfirmResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/import/haushalt/parse",
    alias: "start_parse_api_v1_import_haushalt_parse_post",
    description: `Upload a Haushalt PDF and start a background parse task.

Returns the Celery task_id for polling via GET /api/v1/tasks/{task_id}.`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: Body_start_parse_api_v1_import_haushalt_parse_post,
      },
    ],
    response: z.object({ task_id: z.string() }).passthrough(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/import/haushalt/parse-result",
    alias: "list_parse_run_results_api_v1_import_haushalt_parse_result_get",
    description: `Return metadata for all past parse runs, newest first.`,
    requestFormat: "json",
    response: z.array(ParseResultPublicSchema),
  },
  {
    method: "get",
    path: "/api/v1/import/haushalt/parse-result/:parse_result_id",
    alias:
      "get_parse_run_result_api_v1_import_haushalt_parse_result__parse_result_id__get",
    requestFormat: "json",
    parameters: [
      {
        name: "parse_result_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ParseResultPublicSchema,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/import/haushalt/parse-result/:parse_result_id",
    alias:
      "delete_parse_run_result_api_v1_import_haushalt_parse_result__parse_result_id__delete",
    description: `Delete a parse result.

If the result was already confirmed, all Budget and BudgetTitelEntry rows
for that haushalt_year are also removed so the year can be re-imported.`,
    requestFormat: "json",
    parameters: [
      {
        name: "parse_result_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.void(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/import/haushalt/unmatched",
    alias: "list_unmatched_api_v1_import_haushalt_unmatched_get",
    description: `Return unmatched budget rows. Pass ?resolved&#x3D;false to see only open items.`,
    requestFormat: "json",
    parameters: [
      {
        name: "resolved",
        type: "Query",
        schema: resolved,
      },
    ],
    response: z.array(UnmatchedBudgetRowSchema),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "patch",
    path: "/api/v1/import/haushalt/unmatched/:row_id",
    alias: "patch_unmatched_api_v1_import_haushalt_unmatched__row_id__patch",
    description: `Assign a Finve to an unmatched row. Triggers Budget + BudgetTitelEntry creation.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ finve_id: z.number().int() }).passthrough(),
      },
      {
        name: "row_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: UnmatchedBudgetRowSchema,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/project_groups/",
    alias: "read_project_groups_api_v1_project_groups__get",
    requestFormat: "json",
    response: z.array(ProjectGroupSchema),
  },
  {
    method: "get",
    path: "/api/v1/project_groups/:group_id",
    alias: "read_project_group_api_v1_project_groups__group_id__get",
    requestFormat: "json",
    parameters: [
      {
        name: "group_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "patch",
    path: "/api/v1/project_groups/:group_id",
    alias: "patch_project_group_api_v1_project_groups__group_id__patch",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ProjectGroupUpdate,
      },
      {
        name: "group_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ProjectGroupSchema,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/projects/",
    alias: "read_all_projects_api_v1_projects__get",
    description: `Retrieve all projects.`,
    requestFormat: "json",
    response: z.array(ProjectSchema),
  },
  {
    method: "get",
    path: "/api/v1/projects/:project_id",
    alias: "read_project_api_v1_projects__project_id__get",
    description: `Retrieve a single project by ID.`,
    requestFormat: "json",
    parameters: [
      {
        name: "project_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ProjectSchema,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "patch",
    path: "/api/v1/projects/:project_id",
    alias: "patch_project_api_v1_projects__project_id__patch",
    description: `Update project fields. All changed fields are recorded in the changelog.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ProjectUpdate,
      },
      {
        name: "project_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ProjectSchema,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/projects/:project_id/bvwp",
    alias: "get_project_bvwp_api_v1_projects__project_id__bvwp_get",
    description: `Return BVWP assessment data for a project. Returns 404 if no BVWP data exists.`,
    requestFormat: "json",
    parameters: [
      {
        name: "project_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: BvwpProjectDataSchema,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/projects/:project_id/changelog",
    alias: "read_project_changelog_api_v1_projects__project_id__changelog_get",
    description: `Return the full changelog for a project, newest entries first.`,
    requestFormat: "json",
    parameters: [
      {
        name: "project_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.array(ChangeLogRead),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/projects/:project_id/changelog/revert",
    alias:
      "revert_project_field_api_v1_projects__project_id__changelog_revert_post",
    description: `Revert a single field to its previous value as recorded in the given ChangeLogEntry.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ changelog_entry_id: z.number().int() })
          .passthrough(),
      },
      {
        name: "project_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ProjectSchema,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/projects/:project_id/finves",
    alias: "get_project_finves_api_v1_projects__project_id__finves_get",
    description: `Return all FinVes linked to a project, each with their full budget history
including per-Haushaltstiteln breakdown.`,
    requestFormat: "json",
    parameters: [
      {
        name: "project_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.array(FinveWithBudgetsSchema),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/projects/:project_id/routes",
    alias: "confirm_route_api_v1_projects__project_id__routes_post",
    description: `Confirm a calculated route and add it to the project.

The frontend sends back the GeoJSON Feature it received from /routes/calculate.
The route is persisted to the database and linked to the given project.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ feature: z.object({}).partial().passthrough() })
          .passthrough(),
      },
      {
        name: "project_id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: RouteOut,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/projects/:project_id/routes",
    alias: "list_routes_api_v1_projects__project_id__routes_get",
    requestFormat: "json",
    parameters: [
      {
        name: "project_id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().gte(1).lte(100).optional().default(50),
      },
      {
        name: "offset",
        type: "Query",
        schema: z.number().int().gte(0).optional().default(0),
      },
    ],
    response: z.array(RouteOut),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "put",
    path: "/api/v1/projects/:project_id/routes/:route_id",
    alias: "replace_route_api_v1_projects__project_id__routes__route_id__put",
    description: `Confirm a calculated route and replace an existing one in the project.

The frontend sends back the GeoJSON Feature it received from /routes/calculate.
The existing route (identified by route_id) is updated in-place.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ feature: z.object({}).partial().passthrough() })
          .passthrough(),
      },
      {
        name: "project_id",
        type: "Path",
        schema: z.string().uuid(),
      },
      {
        name: "route_id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: RouteOut,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/projects/:project_id/texts",
    alias: "list_project_texts_api_v1_projects__project_id__texts_get",
    description: `Return all texts linked to a project.`,
    requestFormat: "json",
    parameters: [
      {
        name: "project_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.array(ProjectTextSchema),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/projects/:project_id/texts",
    alias: "create_project_text_api_v1_projects__project_id__texts_post",
    description: `Create a new text and link it to a project. Requires editor or admin role.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ProjectTextCreate,
      },
      {
        name: "project_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ProjectTextSchema,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/projects/:project_id/texts/changelog",
    alias:
      "get_texts_changelog_api_v1_projects__project_id__texts_changelog_get",
    description: `Return the text change history for a project. Requires authentication.`,
    requestFormat: "json",
    parameters: [
      {
        name: "project_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.array(TextChangeLogRead),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "patch",
    path: "/api/v1/projects/texts/:text_id",
    alias: "update_text_api_v1_projects_texts__text_id__patch",
    description: `Update an existing project text. Requires editor or admin role.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ProjectTextUpdate,
      },
      {
        name: "text_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: ProjectTextSchema,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/projects/texts/:text_id",
    alias: "delete_text_api_v1_projects_texts__text_id__delete",
    description: `Delete a project text. Requires editor or admin role.`,
    requestFormat: "json",
    parameters: [
      {
        name: "text_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.void(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/route/",
    alias: "get_route_api_v1_route__post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: RouteRequest,
      },
    ],
    response: RouteResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/routes/:route_id",
    alias: "get_route_api_v1_routes__route_id__get",
    requestFormat: "json",
    parameters: [
      {
        name: "route_id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: RouteOut,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/routes/calculate",
    alias: "calculate_route_api_v1_routes_calculate_post",
    description: `Calculate a route and return it as a GeoJSON Feature preview.

Nothing is saved to the database. The frontend can evaluate the result
and then call the confirm endpoint to persist it.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: RouteIn,
      },
    ],
    response: RoutePreviewOut,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/settings/",
    alias: "get_settings_api_v1_settings__get",
    requestFormat: "json",
    response: AppSettingsSchema,
  },
  {
    method: "patch",
    path: "/api/v1/settings/",
    alias: "patch_settings_api_v1_settings__patch",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: AppSettingsUpdate,
      },
    ],
    response: AppSettingsSchema,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/tasks/:task_id",
    alias: "get_task_status_api_v1_tasks__task_id__get",
    description: `Return the current status and result of a Celery task.`,
    requestFormat: "json",
    parameters: [
      {
        name: "task_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: TaskStatusResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/tasks/debug",
    alias: "start_debug_task_api_v1_tasks_debug_post",
    description: `Start the debug add-task and return its task_id for polling.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: DebugTaskRequest,
      },
    ],
    response: z.object({ task_id: z.string() }).passthrough(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/text_types",
    alias: "list_text_types_api_v1_text_types_get",
    description: `Return all available project text types.`,
    requestFormat: "json",
    response: z.array(ProjectTextTypeSchema),
  },
  {
    method: "post",
    path: "/api/v1/text_types",
    alias: "create_project_text_type_api_v1_text_types_post",
    description: `Create a new project text type. Requires editor or admin role.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ name: z.string() }).passthrough(),
      },
    ],
    response: ProjectTextTypeSchema,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/users/",
    alias: "list_users_api_v1_users__get",
    requestFormat: "json",
    response: z.array(UserRead),
  },
  {
    method: "post",
    path: "/api/v1/users/",
    alias: "create_user_api_v1_users__post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: UserCreate,
      },
    ],
    response: UserRead,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "patch",
    path: "/api/v1/users/:user_id",
    alias: "update_user_api_v1_users__user_id__patch",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: UserUpdate,
      },
      {
        name: "user_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: UserRead,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/users/:user_id",
    alias: "delete_user_api_v1_users__user_id__delete",
    requestFormat: "json",
    parameters: [
      {
        name: "user_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.void(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "patch",
    path: "/api/v1/users/:user_id/password",
    alias: "set_user_password_api_v1_users__user_id__password_patch",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ password: z.string().min(8).max(128) })
          .passthrough(),
      },
      {
        name: "user_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.void(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/users/me",
    alias: "get_current_user_info_api_v1_users_me_get",
    requestFormat: "json",
    response: UserRead,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
]);

export const api = new Zodios(endpoints);

export function createApiClient(baseUrl: string, options?: ZodiosOptions) {
  return new Zodios(baseUrl, endpoints, options);
}
