import { makeApi, Zodios, type ZodiosOptions } from "@zodios/core";
import { z } from "zod";

const RouteRequest = z
  .object({ start_op: z.string(), end_op: z.string() })
  .passthrough();
const RouteResponse = z
  .object({ sectionofline_ids: z.array(z.number().int()) })
  .passthrough();
const ValidationError = z
  .object({
    loc: z.array(z.union([z.string(), z.number()])),
    msg: z.string(),
    type: z.string(),
  })
  .passthrough();
const HTTPValidationError = z
  .object({ detail: z.array(ValidationError) })
  .partial()
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
const ProjectGroupSchema = z
  .object({
    id: z.union([z.number(), z.null()]).optional(),
    name: z.string(),
    short_name: z.string(),
    description: z.union([z.string(), z.null()]).optional(),
    public: z.boolean().optional().default(false),
    color: z.string().optional().default("#FF0000"),
    plot_only_superior_projects: z.boolean().optional().default(true),
    id_old: z.union([z.number(), z.null()]).optional(),
    projects: z.array(ProjectSchema).optional(),
  })
  .passthrough();

export const schemas = {
  RouteRequest,
  RouteResponse,
  ValidationError,
  HTTPValidationError,
  ProjectSchema,
  ProjectGroupSchema,
};

const endpoints = makeApi([
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
]);

export const api = new Zodios(endpoints);

export function createApiClient(baseUrl: string, options?: ZodiosOptions) {
  return new Zodios(baseUrl, endpoints, options);
}
