import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type { components } from "./types.gen";

export type Project = components["schemas"]["ProjectSchema"];
export type ProjectGroup = components["schemas"]["ProjectGroupSchema"];
export type ProjectRoute = components["schemas"]["RouteOut"];
export type User = components["schemas"]["UserRead"];

export type ProjectUpdatePayload = {
    name?: string;
    project_number?: string | null;
    description?: string | null;
    justification?: string | null;
    length?: number | null;
    new_vmax?: number | null;
    etcs_level?: number | null;
    number_junction_station?: number | null;
    number_overtaking_station?: number | null;
    filling_stations_count?: number | null;
    effects_passenger_long_rail?: boolean;
    effects_passenger_local_rail?: boolean;
    effects_cargo_rail?: boolean;
    nbs?: boolean;
    abs?: boolean;
    second_track?: boolean;
    third_track?: boolean;
    fourth_track?: boolean;
    curve?: boolean;
    increase_speed?: boolean;
    tunnel_structural_gauge?: boolean;
    tilting?: boolean;
    new_station?: boolean | null;
    platform?: boolean;
    junction_station?: boolean;
    overtaking_station?: boolean;
    depot?: boolean;
    level_free_platform_entrance?: boolean;
    double_occupancy?: boolean;
    simultaneous_train_entries?: boolean;
    buffer_track?: boolean;
    overpass?: boolean;
    noise_barrier?: boolean;
    railroad_crossing?: boolean;
    gwb?: boolean;
    etcs?: boolean;
    new_estw?: boolean;
    new_dstw?: boolean;
    block_increase?: boolean;
    station_railroad_switches?: boolean;
    flying_junction?: boolean;
    elektrification?: boolean;
    optimised_electrification?: boolean;
    charging_station?: boolean;
    small_charging_station?: boolean;
    battery?: boolean;
    h2?: boolean;
    efuel?: boolean;
    filling_stations_efuel?: boolean;
    filling_stations_h2?: boolean;
    filling_stations_diesel?: boolean;
    sgv740m?: boolean;
    sanierung?: boolean;
    closure?: boolean;
};

// ---------------------------------------------------------------------------
// Project texts
// ---------------------------------------------------------------------------

export type ProjectTextType = { id: number; name: string };

export type ProjectText = {
    id: number;
    header: string;
    weblink: string | null;
    text: string | null;
    type: number;
    logo_url: string | null;
    created_at: number;
    updated_at: number;
    text_type: ProjectTextType;
};

export type ProjectTextCreate = {
    header: string;
    weblink?: string | null;
    text?: string | null;
    type: number;
    logo_url?: string | null;
};

export type ProjectTextUpdate = Partial<ProjectTextCreate>;

export function useTextTypes() {
    return useQuery({
        queryKey: ["textTypes"],
        queryFn: () => api<ProjectTextType[]>("/api/v1/text_types"),
    });
}

export function useCreateTextType() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (name: string) =>
            api<ProjectTextType>("/api/v1/text_types", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["textTypes"] });
        },
    });
}

export function useProjectTexts(projectId: number) {
    return useQuery({
        queryKey: ["projectTexts", projectId],
        enabled: Number.isFinite(projectId),
        queryFn: () =>
            api<ProjectText[]>(`/api/v1/projects/${projectId}/texts`),
    });
}

export function useCreateProjectText(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: ProjectTextCreate) =>
            api<ProjectText>(`/api/v1/projects/${projectId}/texts`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["projectTexts", projectId] });
        },
    });
}

export function useUpdateProjectText(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ textId, payload }: { textId: number; payload: ProjectTextUpdate }) =>
            api<ProjectText>(`/api/v1/projects/texts/${textId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["projectTexts", projectId] });
        },
    });
}

export function useDeleteProjectText(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (textId: number) =>
            api<void>(`/api/v1/projects/texts/${textId}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["projectTexts", projectId] });
        },
    });
}

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

export const projectRoutesQueryKey = (projectId: number) => ["projectRoutes", projectId];

export const getProjectRoutesQueryOptions = (projectId: number) => ({
    queryKey: projectRoutesQueryKey(projectId),
    enabled: Number.isFinite(projectId),
    queryFn: () =>
        api<ProjectRoute[]>("/api/v1/projects/:project_id/routes", {
            params: { path: { project_id: projectId } },
        }),
});

export function useProjectRoutes(projectId: number) {
    return useQuery(getProjectRoutesQueryOptions(projectId));
}

export function updateProject(id: number, payload: ProjectUpdatePayload) {
    return api<Project>("/api/v1/projects/:project_id", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        params: { path: { project_id: id } },
    });
}

// ---------------------------------------------------------------------------
// Change tracking
// ---------------------------------------------------------------------------

export type ChangeLogEntry = {
    id: number;
    field_name: string;
    old_value: string | null;
    new_value: string | null;
};

export type ChangeLog = {
    id: number;
    project_id: number;
    user_id: number | null;
    username_snapshot: string | null;
    timestamp: string;
    action: string;
    entries: ChangeLogEntry[];
};

export type TextChangeLogEntry = {
    id: number;
    field_name: string;
    old_value: string | null;
    new_value: string | null;
};

export type TextChangeLog = {
    id: number;
    text_id: number | null;
    project_id: number | null;
    user_id: number | null;
    username_snapshot: string | null;
    text_header_snapshot: string | null;
    timestamp: string;
    action: string;
    entries: TextChangeLogEntry[];
};

export function useProjectChangelog(projectId: number) {
    return useQuery({
        queryKey: ["project-changelog", projectId],
        enabled: Number.isFinite(projectId),
        queryFn: () => api<ChangeLog[]>(`/api/v1/projects/${projectId}/changelog`),
    });
}

export function useProjectTextChangelog(projectId: number) {
    return useQuery({
        queryKey: ["project-text-changelog", projectId],
        enabled: Number.isFinite(projectId),
        queryFn: () => api<TextChangeLog[]>(`/api/v1/projects/${projectId}/texts/changelog`),
    });
}

export function useRevertProjectField(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (changelogEntryId: number) =>
            api<Project>(`/api/v1/projects/${projectId}/changelog/revert`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ changelog_entry_id: changelogEntryId }),
            }),
        onSuccess: (updatedProject) => {
            queryClient.setQueryData(["project", projectId], updatedProject);
            queryClient.invalidateQueries({ queryKey: ["projects"] });
            queryClient.invalidateQueries({ queryKey: ["project-changelog", projectId] });
        },
    });
}

// ---------------------------------------------------------------------------
// User management hooks (admin only)
// ---------------------------------------------------------------------------

export function useUsers() {
    return useQuery({
        queryKey: ["users"],
        queryFn: () => api<User[]>("/api/v1/users/"),
    });
}

export function useCreateUser() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: { username: string; password: string; role: string }) =>
            api<User>("/api/v1/users/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["users"] });
        },
    });
}

export function useUpdateUserRole() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ userId, role }: { userId: number; role: string }) =>
            api<User>(`/api/v1/users/${userId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ role }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["users"] });
        },
    });
}

export function useDeleteUser() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (userId: number) =>
            api<void>(`/api/v1/users/${userId}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["users"] });
        },
    });
}

export function useSetUserPassword() {
    return useMutation({
        mutationFn: ({ userId, password }: { userId: number; password: string }) =>
            api<void>(`/api/v1/users/${userId}/password`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password }),
            }),
    });
}
