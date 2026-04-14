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
const OperationalPointRef = z
  .object({
    id: z.number().int(),
    op_id: z.union([z.string(), z.null()]).optional(),
    name: z.union([z.string(), z.null()]).optional(),
    type: z.union([z.string(), z.null()]).optional(),
    latitude: z.union([z.number(), z.null()]).optional(),
    longitude: z.union([z.number(), z.null()]).optional(),
  })
  .passthrough();
const RouteRequest = z
  .object({ start_op: z.string(), end_op: z.string() })
  .passthrough();
const RouteResponse = z
  .object({ sectionofline_ids: z.array(z.number().int()) })
  .passthrough();
const ProjectGroupRef = z
  .object({
    id: z.number().int(),
    name: z.string(),
    short_name: z.string(),
    color: z.string(),
  })
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
    project_groups: z.array(ProjectGroupRef).optional().default([]),
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
    project_group_ids: z.union([z.array(z.number().int()), z.null()]),
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
const VibPfaEntrySchema = z
  .object({
    id: z.number().int(),
    abschnitt_label: z.union([z.string(), z.null()]).optional(),
    nr_pfa: z.union([z.string(), z.null()]).optional(),
    oertlichkeit: z.union([z.string(), z.null()]).optional(),
    entwurfsplanung: z.union([z.string(), z.null()]).optional(),
    abschluss_finve: z.union([z.string(), z.null()]).optional(),
    datum_pfb: z.union([z.string(), z.null()]).optional(),
    baubeginn: z.union([z.string(), z.null()]).optional(),
    inbetriebnahme: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const VibEntryForProjectSchema = z
  .object({
    id: z.number().int(),
    year: z.number().int(),
    drucksache_nr: z.union([z.string(), z.null()]).optional(),
    vib_section: z.union([z.string(), z.null()]).optional(),
    vib_name_raw: z.string(),
    category: z.string(),
    bauaktivitaeten: z.union([z.string(), z.null()]).optional(),
    teilinbetriebnahmen: z.union([z.string(), z.null()]).optional(),
    verkehrliche_zielsetzung: z.union([z.string(), z.null()]).optional(),
    durchgefuehrte_massnahmen: z.union([z.string(), z.null()]).optional(),
    noch_umzusetzende_massnahmen: z.union([z.string(), z.null()]).optional(),
    raw_text: z.union([z.string(), z.null()]).optional(),
    strecklaenge_km: z.union([z.number(), z.null()]).optional(),
    gesamtkosten_mio_eur: z.union([z.number(), z.null()]).optional(),
    entwurfsgeschwindigkeit: z.union([z.string(), z.null()]).optional(),
    planungsstand: z.union([z.string(), z.null()]).optional(),
    status_planung: z.boolean().optional().default(false),
    status_bau: z.boolean().optional().default(false),
    status_abgeschlossen: z.boolean().optional().default(false),
    ai_extracted: z.boolean().optional().default(false),
    pfa_entries: z.array(VibPfaEntrySchema).optional().default([]),
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
    project_id: z.number().int(),
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
const TextAttachmentSchema = z
  .object({
    id: z.number().int(),
    text_id: z.number().int(),
    filename: z.string(),
    mime_type: z.string(),
    file_size: z.number().int(),
    uploaded_at: z.string().datetime({ offset: true }),
    uploaded_by_user_id: z.union([z.number(), z.null()]).optional(),
  })
  .passthrough();
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
    attachments: z.array(TextAttachmentSchema).optional().default([]),
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
const Body_upload_attachment_api_v1_projects_texts__text_id__attachments_post =
  z.object({ file: z.instanceof(File) }).passthrough();
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
  .object({ pdf: z.instanceof(File), year: z.number().int() })
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
const VibAiAvailableResponse = z
  .object({
    available: z.boolean(),
    model: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const VibOcrAvailableResponse = z
  .object({
    available: z.boolean(),
    model: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const Body_start_vib_parse_api_v1_import_vib_parse_post = z
  .object({
    pdf: z.instanceof(File),
    year: z.number().int(),
    start_page: z.union([z.number(), z.null()]).optional(),
    end_page: z.union([z.number(), z.null()]).optional(),
    strip_headers_footers: z.boolean().optional().default(true),
  })
  .passthrough();
const VibPfaEntryProposed = z
  .object({
    abschnitt_label: z.union([z.string(), z.null()]),
    nr_pfa: z.union([z.string(), z.null()]),
    oertlichkeit: z.union([z.string(), z.null()]),
    entwurfsplanung: z.union([z.string(), z.null()]),
    abschluss_finve: z.union([z.string(), z.null()]),
    datum_pfb: z.union([z.string(), z.null()]),
    baubeginn: z.union([z.string(), z.null()]),
    inbetriebnahme: z.union([z.string(), z.null()]),
  })
  .partial()
  .passthrough();
const VibEntryProposed = z
  .object({
    vib_section: z.union([z.string(), z.null()]).optional(),
    vib_lfd_nr: z.union([z.string(), z.null()]).optional(),
    vib_name_raw: z.string(),
    category: z.string().optional().default("laufend"),
    verkehrliche_zielsetzung: z.union([z.string(), z.null()]).optional(),
    durchgefuehrte_massnahmen: z.union([z.string(), z.null()]).optional(),
    noch_umzusetzende_massnahmen: z.union([z.string(), z.null()]).optional(),
    bauaktivitaeten: z.union([z.string(), z.null()]).optional(),
    teilinbetriebnahmen: z.union([z.string(), z.null()]).optional(),
    raw_text: z.union([z.string(), z.null()]).optional(),
    strecklaenge_km: z.union([z.number(), z.null()]).optional(),
    gesamtkosten_mio_eur: z.union([z.number(), z.null()]).optional(),
    entwurfsgeschwindigkeit: z.union([z.string(), z.null()]).optional(),
    planungsstand: z.union([z.string(), z.null()]).optional(),
    status_planung: z.boolean().optional().default(false),
    status_bau: z.boolean().optional().default(false),
    status_abgeschlossen: z.boolean().optional().default(false),
    pfa_entries: z.array(VibPfaEntryProposed).optional().default([]),
    pfa_raw_markdown: z.union([z.string(), z.null()]).optional(),
    sonstiges: z.union([z.string(), z.null()]).optional(),
    project_ids: z.array(z.number().int()).optional().default([]),
    suggested_project_ids: z.array(z.number().int()).optional().default([]),
    ai_extracted: z.boolean().optional().default(false),
    ai_extraction_failed: z.boolean().optional().default(false),
    ai_extraction_error: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const VibParseTaskResult_Output = z
  .object({
    year: z.number().int(),
    drucksache_nr: z.union([z.string(), z.null()]).optional(),
    report_date: z.union([z.string(), z.null()]).optional(),
    entries: z.array(VibEntryProposed).optional().default([]),
  })
  .passthrough();
const VibConfirmEntryInput = z
  .object({
    vib_section: z.union([z.string(), z.null()]).optional(),
    vib_lfd_nr: z.union([z.string(), z.null()]).optional(),
    vib_name_raw: z.string(),
    category: z.string().optional().default("laufend"),
    verkehrliche_zielsetzung: z.union([z.string(), z.null()]).optional(),
    durchgefuehrte_massnahmen: z.union([z.string(), z.null()]).optional(),
    noch_umzusetzende_massnahmen: z.union([z.string(), z.null()]).optional(),
    bauaktivitaeten: z.union([z.string(), z.null()]).optional(),
    teilinbetriebnahmen: z.union([z.string(), z.null()]).optional(),
    raw_text: z.union([z.string(), z.null()]).optional(),
    strecklaenge_km: z.union([z.number(), z.null()]).optional(),
    gesamtkosten_mio_eur: z.union([z.number(), z.null()]).optional(),
    entwurfsgeschwindigkeit: z.union([z.string(), z.null()]).optional(),
    planungsstand: z.union([z.string(), z.null()]).optional(),
    status_planung: z.boolean().optional().default(false),
    status_bau: z.boolean().optional().default(false),
    status_abgeschlossen: z.boolean().optional().default(false),
    pfa_entries: z.array(VibPfaEntryProposed).optional().default([]),
    pfa_raw_markdown: z.union([z.string(), z.null()]).optional(),
    sonstiges: z.union([z.string(), z.null()]).optional(),
    project_ids: z.array(z.number().int()).optional().default([]),
  })
  .passthrough();
const VibConfirmRequest = z
  .object({
    task_id: z.string(),
    year: z.number().int(),
    drucksache_nr: z.union([z.string(), z.null()]).optional(),
    report_date: z.union([z.string(), z.null()]).optional(),
    entries: z.array(VibConfirmEntryInput).optional().default([]),
  })
  .passthrough();
const VibConfirmResponse = z
  .object({
    report_id: z.number().int(),
    entries_created: z.number().int(),
    pfa_entries_created: z.number().int(),
  })
  .passthrough();
const VibDraftSchema = z
  .object({
    task_id: z.string(),
    year: z.number().int(),
    created_at: z.string(),
  })
  .passthrough();
const VibParseTaskResult_Input = z
  .object({
    year: z.number().int(),
    drucksache_nr: z.union([z.string(), z.null()]).optional(),
    report_date: z.union([z.string(), z.null()]).optional(),
    entries: z.array(VibEntryProposed).optional().default([]),
  })
  .passthrough();
const VibReportSchema = z
  .object({
    id: z.number().int(),
    year: z.number().int(),
    drucksache_nr: z.union([z.string(), z.null()]).optional(),
    report_date: z.union([z.string(), z.null()]).optional(),
    imported_at: z.string(),
    entry_count: z.number().int().optional().default(0),
  })
  .passthrough();
const UnassignedFinveSchema = z
  .object({
    id: z.number().int(),
    name: z.union([z.string(), z.null()]),
    is_sammel_finve: z.boolean(),
    starting_year: z.union([z.number(), z.null()]),
  })
  .passthrough();
const UnassignedVibEntrySchema = z
  .object({
    id: z.number().int(),
    vib_name_raw: z.string(),
    vib_section: z.union([z.string(), z.null()]),
    category: z.string(),
    report_year: z.number().int(),
  })
  .passthrough();
const AssignProjectsInput = z
  .object({ project_ids: z.array(z.number().int()) })
  .passthrough();

export const schemas = {
  SessionCredentials,
  ValidationError,
  HTTPValidationError,
  OperationalPointRef,
  RouteRequest,
  RouteResponse,
  ProjectGroupRef,
  ProjectSchema,
  ProjectUpdate,
  BvwpProjectDataSchema,
  VibPfaEntrySchema,
  VibEntryForProjectSchema,
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
  TextAttachmentSchema,
  ProjectTextSchema,
  ProjectTextCreate,
  TextChangeLogEntryRead,
  TextChangeLogRead,
  ProjectTextUpdate,
  Body_upload_attachment_api_v1_projects_texts__text_id__attachments_post,
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
  VibAiAvailableResponse,
  VibOcrAvailableResponse,
  Body_start_vib_parse_api_v1_import_vib_parse_post,
  VibPfaEntryProposed,
  VibEntryProposed,
  VibParseTaskResult_Output,
  VibConfirmEntryInput,
  VibConfirmRequest,
  VibConfirmResponse,
  VibDraftSchema,
  VibParseTaskResult_Input,
  VibReportSchema,
  UnassignedFinveSchema,
  UnassignedVibEntrySchema,
  AssignProjectsInput,
};

const endpoints = makeApi([
  {
    method: "get",
    path: "/api/v1/admin/unassigned-finves",
    alias: "get_unassigned_finves_api_v1_admin_unassigned_finves_get",
    requestFormat: "json",
    response: z.array(UnassignedFinveSchema),
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
    path: "/api/v1/admin/unassigned-finves/:finve_id/assign",
    alias:
      "assign_finve_api_v1_admin_unassigned_finves__finve_id__assign_patch",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: AssignProjectsInput,
      },
      {
        name: "finve_id",
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
    path: "/api/v1/admin/unassigned-vib-entries",
    alias: "get_unassigned_vib_entries_api_v1_admin_unassigned_vib_entries_get",
    requestFormat: "json",
    response: z.array(UnassignedVibEntrySchema),
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
    path: "/api/v1/admin/unassigned-vib-entries/:entry_id/assign",
    alias:
      "assign_vib_entry_api_v1_admin_unassigned_vib_entries__entry_id__assign_patch",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: AssignProjectsInput,
      },
      {
        name: "entry_id",
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
    path: "/api/v1/import/vib/ai-available",
    alias: "vib_ai_available_api_v1_import_vib_ai_available_get",
    description: `Return whether LLM-based AI extraction is configured.`,
    requestFormat: "json",
    response: VibAiAvailableResponse,
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
    path: "/api/v1/import/vib/confirm",
    alias: "confirm_vib_import_api_v1_import_vib_confirm_post",
    description: `Confirm a VIB parse result and write VibReport + VibEntry rows to DB.

Guard: if a VibReport for the given year already exists, returns 409.
Delete the existing report first if re-import is needed.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: VibConfirmRequest,
      },
    ],
    response: VibConfirmResponse,
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
    path: "/api/v1/import/vib/draft/:parse_task_id",
    alias: "save_vib_draft_api_v1_import_vib_draft__parse_task_id__patch",
    description: `Overwrite the draft&#x27;s raw_result_json with the current review state.

Called by the review UI to persist edits so work survives page reloads.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: VibParseTaskResult_Input,
      },
      {
        name: "parse_task_id",
        type: "Path",
        schema: z.string(),
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
    path: "/api/v1/import/vib/draft/:task_id/image/:image_id",
    alias:
      "get_vib_draft_image_api_v1_import_vib_draft__task_id__image__image_id__get",
    description: `Return a single OCR image extracted from the Mistral OCR response.

image_id matches the id returned by the OCR API, e.g. &quot;img-0.jpeg&quot;.
The image bytes are decoded from base64 and returned with the appropriate
content type (image/jpeg or image/png).`,
    requestFormat: "json",
    parameters: [
      {
        name: "task_id",
        type: "Path",
        schema: z.string(),
      },
      {
        name: "image_id",
        type: "Path",
        schema: z.string(),
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
    method: "get",
    path: "/api/v1/import/vib/draft/:task_id/images",
    alias: "list_vib_draft_images_api_v1_import_vib_draft__task_id__images_get",
    description: `Return metadata for all OCR images extracted from a draft (id, page_index).

Does NOT return base64 data — fetch individual images via
GET /draft/{task_id}/image/{image_id}.`,
    requestFormat: "json",
    parameters: [
      {
        name: "task_id",
        type: "Path",
        schema: z.string(),
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
    method: "get",
    path: "/api/v1/import/vib/drafts",
    alias: "list_vib_drafts_api_v1_import_vib_drafts_get",
    description: `Return metadata for all unconfirmed VIB drafts, newest first.`,
    requestFormat: "json",
    response: z.array(VibDraftSchema),
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
    path: "/api/v1/import/vib/drafts/:task_id",
    alias: "delete_vib_draft_api_v1_import_vib_drafts__task_id__delete",
    description: `Discard an unconfirmed VIB draft.`,
    requestFormat: "json",
    parameters: [
      {
        name: "task_id",
        type: "Path",
        schema: z.string(),
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
    path: "/api/v1/import/vib/extract-ai/:parse_task_id",
    alias:
      "start_vib_ai_extraction_api_v1_import_vib_extract_ai__parse_task_id__post",
    description: `Start the LLM extraction Celery task for a parsed VIB draft.

The parse_task_id must refer to a completed parse task whose draft is saved in DB.
Returns a new task_id for polling via GET /api/v1/tasks/{task_id}.
When the task reaches SUCCESS, the draft in DB is updated with AI-extracted content.
Retrieve the updated parse result via GET /parse-result/{parse_task_id}.`,
    requestFormat: "json",
    parameters: [
      {
        name: "parse_task_id",
        type: "Path",
        schema: z.string(),
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
    method: "post",
    path: "/api/v1/import/vib/extract-ai/:parse_task_id/entry/:entry_idx",
    alias:
      "retry_vib_ai_for_entry_api_v1_import_vib_extract_ai__parse_task_id__entry__entry_idx__post",
    description: `Re-run LLM extraction synchronously for a single entry and persist the result.`,
    requestFormat: "json",
    parameters: [
      {
        name: "parse_task_id",
        type: "Path",
        schema: z.string(),
      },
      {
        name: "entry_idx",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: VibEntryProposed,
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
    path: "/api/v1/import/vib/ocr-available",
    alias: "vib_ocr_available_api_v1_import_vib_ocr_available_get",
    description: `Return whether Mistral OCR is configured.`,
    requestFormat: "json",
    response: VibOcrAvailableResponse,
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
    path: "/api/v1/import/vib/parse",
    alias: "start_vib_parse_api_v1_import_vib_parse_post",
    description: `Upload a VIB PDF and start a background parse task.

start_page / end_page (optional, 1-indexed): restrict OCR to these pages only.
strip_headers_footers: remove repeated page headers/footers from OCR output (default True).

Returns the Celery task_id for polling via GET /api/v1/tasks/{task_id}.`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: Body_start_vib_parse_api_v1_import_vib_parse_post,
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
    path: "/api/v1/import/vib/parse-result/:task_id",
    alias: "get_vib_parse_result_api_v1_import_vib_parse_result__task_id__get",
    description: `Retrieve the parse result for a completed Celery task.

Tries Redis first (Celery result backend). Falls back to the
vib_draft_report DB table if the Redis entry has been evicted.
Returns 202 if the task is still running; 422 if it failed.`,
    requestFormat: "json",
    parameters: [
      {
        name: "task_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: VibParseTaskResult_Output,
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
    path: "/api/v1/import/vib/reports",
    alias: "list_vib_reports_api_v1_import_vib_reports_get",
    description: `Return metadata for all imported VIB reports, newest year first.`,
    requestFormat: "json",
    response: z.array(VibReportSchema),
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
    path: "/api/v1/import/vib/reports/:report_id",
    alias: "delete_vib_report_api_v1_import_vib_reports__report_id__delete",
    description: `Delete a VIB report and all associated VibEntry / VibPfaEntry rows.`,
    requestFormat: "json",
    parameters: [
      {
        name: "report_id",
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
    path: "/api/v1/operational-points/",
    alias: "search_ops_api_v1_operational_points__get",
    description: `Search operational points (stations/stops) by name or ID. Public endpoint.`,
    requestFormat: "json",
    parameters: [
      {
        name: "q",
        type: "Query",
        schema: z.string().optional().default(""),
      },
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().gte(1).lte(100).optional().default(20),
      },
    ],
    response: z.array(OperationalPointRef),
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
        schema: z.number().int(),
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
        schema: z.number().int(),
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
        schema: z.number().int(),
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
    method: "get",
    path: "/api/v1/projects/:project_id/vib",
    alias: "get_project_vib_api_v1_projects__project_id__vib_get",
    description: `Return all VIB entries linked to a project, newest year first.`,
    requestFormat: "json",
    parameters: [
      {
        name: "project_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.array(VibEntryForProjectSchema),
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
    path: "/api/v1/projects/texts/:text_id/attachments",
    alias: "upload_attachment_api_v1_projects_texts__text_id__attachments_post",
    description: `Upload a file attachment to a project text. Requires editor or admin role.

Accepted types: PDF, Word (.doc/.docx), Excel (.xls/.xlsx), JPEG, PNG.
Maximum file size: 50 MB.`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ file: z.instanceof(File) }).passthrough(),
      },
      {
        name: "text_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: TextAttachmentSchema,
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
    path: "/api/v1/projects/texts/:text_id/attachments",
    alias: "list_attachments_api_v1_projects_texts__text_id__attachments_get",
    description: `List all attachments for a project text.

Requires authentication if the parent text belongs to an authenticated-only project.
For now all texts are publicly readable (mirrors list_project_texts behaviour).`,
    requestFormat: "json",
    parameters: [
      {
        name: "text_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.array(TextAttachmentSchema),
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
    path: "/api/v1/projects/texts/:text_id/attachments/:attachment_id",
    alias:
      "remove_attachment_api_v1_projects_texts__text_id__attachments__attachment_id__delete",
    description: `Delete an attachment. Requires editor or admin role.`,
    requestFormat: "json",
    parameters: [
      {
        name: "text_id",
        type: "Path",
        schema: z.number().int(),
      },
      {
        name: "attachment_id",
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
    path: "/api/v1/projects/texts/:text_id/attachments/:attachment_id/download",
    alias:
      "download_attachment_api_v1_projects_texts__text_id__attachments__attachment_id__download_get",
    description: `Stream an attachment file.

Security:
- Content-Type is set from the DB-stored mime_type (never re-detected).
- Content-Disposition forces download by default (prevents stored XSS via HTML/SVG).
- Pass ?inline&#x3D;true to serve PDFs inline (for in-browser preview); ignored for other types.
- Filename is RFC 5987-encoded to prevent header injection.
- X-Content-Type-Options: nosniff is set.`,
    requestFormat: "json",
    parameters: [
      {
        name: "text_id",
        type: "Path",
        schema: z.number().int(),
      },
      {
        name: "attachment_id",
        type: "Path",
        schema: z.number().int(),
      },
      {
        name: "inline",
        type: "Query",
        schema: z.boolean().optional().default(false),
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
