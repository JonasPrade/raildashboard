import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type { components } from "./types.gen";

export type Project = components["schemas"]["ProjectSchema"];
export type ProjectGroup = components["schemas"]["ProjectGroupSchema"];
export type ProjectRoute = components["schemas"]["RouteOut"];
export type User = components["schemas"]["UserRead"];

export type ProjectUpdatePayload = {
    name: string;
    project_number?: string | null;
    description?: string | null;
    justification?: string | null;
    length?: number | null;
    elektrification?: boolean;
    second_track?: boolean;
    new_station?: boolean | null;
};

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
