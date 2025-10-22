import { useQuery } from "@tanstack/react-query"
import { api } from "./client"

export function useProjects() {
    return useQuery({
        queryKey: ["projects"],
        queryFn: () => api("/api/v1/projects/"),
    })
}

export function useProject(id: number) {
    return useQuery({
        queryKey: ["project", id],
        queryFn: () => api("/api/v1/projects/:project_id", {
            params: { path: { project_id: id } },
        }),
    })
}