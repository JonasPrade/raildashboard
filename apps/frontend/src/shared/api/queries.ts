import { useQuery } from "@tanstack/react-query";

import { api } from "./client";
import type { components } from "./types.gen";

export type Project = components["schemas"]["ProjectSchema"];
export type ProjectGroup = components["schemas"]["ProjectGroupSchema"];

export function useProjects() {
    return useQuery({
        queryKey: ["projects"],
        queryFn: () => api<Project[]>("/api/v1/projects/"),
    });
}

export function useProject(id: number) {
    return useQuery({
        queryKey: ["project", id],
        enabled: Number.isFinite(id),
        queryFn: () =>
            api<Project>("/api/v1/projects/:project_id", {
                params: { path: { project_id: id } },
            }),
    });
}

export function useProjectGroups() {
    return useQuery({
        queryKey: ["projectGroups"],
        queryFn: () => api<ProjectGroup[]>("/api/v1/project_groups/"),
    });
}
