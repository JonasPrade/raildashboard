import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type { components } from "./types.gen";

function mergeDefined<T extends object>(entry: T, patch: object): T {
    const next = { ...entry } as Record<string, unknown>;
    for (const [key, value] of Object.entries(patch)) {
        if (value !== undefined) next[key] = value;
    }
    return next as T;
}

export type Project = components["schemas"]["ProjectSchema"];
export type ProjectGroup = components["schemas"]["ProjectGroupSchema"];
export type ProjectRoute = components["schemas"]["RouteOut"];
export type User = components["schemas"]["UserRead"];
export type Role = components["schemas"]["RoleRead"];
export type Permission = components["schemas"]["PermissionSchema"];

export type ProjectUpdatePayload = components["schemas"]["ProjectUpdate"];

// ---------------------------------------------------------------------------
// Project texts
// ---------------------------------------------------------------------------

export type ProjectTextType = components["schemas"]["ProjectTextTypeSchema"];

export type TextAttachment = components["schemas"]["TextAttachmentSchema"];

export type ProjectText = components["schemas"]["ProjectTextSchema"];

export type ProjectTextCreate = components["schemas"]["ProjectTextCreate"];

export type ProjectTextUpdate = components["schemas"]["ProjectTextUpdate"];

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

export function useUploadTextAttachment(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ textId, file }: { textId: number; file: File }) => {
            const formData = new FormData();
            formData.append("file", file);
            // No Content-Type header — browser sets multipart/form-data with boundary
            return api<TextAttachment>(`/api/v1/projects/texts/${textId}/attachments`, {
                method: "POST",
                body: formData,
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["projectTexts", projectId] });
        },
    });
}

export function useDeleteTextAttachment(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ textId, attachmentId }: { textId: number; attachmentId: number }) =>
            api<void>(`/api/v1/projects/texts/${textId}/attachments/${attachmentId}`, {
                method: "DELETE",
            }),
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

// ---------------------------------------------------------------------------
// Project progress / planning state (Planungsstand)
// ---------------------------------------------------------------------------

export type ProjectProgress = components["schemas"]["ProjectProgressSchema"];
export type ProgressObservation = components["schemas"]["ProgressObservationSchema"];
export type ProgressObservationCreate = components["schemas"]["ProgressObservationCreate"];
export type ProjectProgressUpdate = components["schemas"]["ProjectProgressUpdate"];
export type TrackDocument = components["schemas"]["TrackDocumentSchema"];
export type SourceContribution = components["schemas"]["SourceContributionSchema"];
export type ProgressChild = components["schemas"]["ProgressChildSchema"];
export type ProgressForecast = components["schemas"]["ProgressForecastSchema"];
export type ForecastStep = components["schemas"]["ForecastStepSchema"];

const progressKey = (projectId: number) => ["project-progress", projectId];

export function useProjectProgress(projectId: number) {
    return useQuery({
        queryKey: progressKey(projectId),
        enabled: Number.isFinite(projectId),
        queryFn: () => api<ProjectProgress>(`/api/v1/projects/${projectId}/progress`),
    });
}

export function useUpdateProjectProgress(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: ProjectProgressUpdate) =>
            api<ProjectProgress>(`/api/v1/projects/${projectId}/progress`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: progressKey(projectId) });
        },
    });
}

export function useAddProgressObservation(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: ProgressObservationCreate) =>
            api<ProjectProgress>(`/api/v1/projects/${projectId}/progress/observations`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: progressKey(projectId) });
        },
    });
}

export function useDeleteProgressObservation(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (observationId: number) =>
            api<ProjectProgress>(
                `/api/v1/projects/${projectId}/progress/observations/${observationId}`,
                { method: "DELETE" },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: progressKey(projectId) });
        },
    });
}

export type SammelFinveProgress = components["schemas"]["SammelFinveProgressSchema"];

export function useSammelFinveProgress() {
    return useQuery({
        queryKey: ["sammel-finve-progress"],
        queryFn: () => api<SammelFinveProgress[]>("/api/v1/finves/sammel-progress"),
    });
}

export function useSetFinveProgressPhase() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ finveId, phase }: { finveId: number; phase: string | null }) =>
            api<SammelFinveProgress[]>(`/api/v1/finves/${finveId}/progress-phase`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ progress_phase: phase }),
            }),
        onSuccess: (data) => {
            queryClient.setQueryData(["sammel-finve-progress"], data);
            // A changed mapping affects derived progress on linked projects.
            queryClient.invalidateQueries({ queryKey: ["project-progress"] });
        },
    });
}

export function useRecomputeProgress(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: () =>
            api<ProjectProgress>(`/api/v1/projects/${projectId}/progress/recompute`, {
                method: "POST",
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: progressKey(projectId) });
        },
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

export type ProjectGroupCreatePayload = components["schemas"]["ProjectGroupCreate"];

export type ProjectGroupUpdatePayload = components["schemas"]["ProjectGroupUpdate"];

export function useCreateProjectGroup() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: ProjectGroupCreatePayload) =>
            api<ProjectGroup>("/api/v1/project_groups/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["projectGroups"] }),
    });
}

export function useUpdateProjectGroup() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ groupId, ...payload }: { groupId: number } & ProjectGroupUpdatePayload) =>
            api<ProjectGroup>(`/api/v1/project_groups/${groupId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["projectGroups"] }),
    });
}

export function useDeleteProjectGroup() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (groupId: number) =>
            api<void>(`/api/v1/project_groups/${groupId}`, { method: "DELETE" }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["projectGroups"] }),
    });
}

export type MapGroupMode = AppSettings["map_group_mode"];
export type AppSettings = components["schemas"]["AppSettingsSchema"];

export function useAppSettings() {
    return useQuery({
        queryKey: ["appSettings"],
        queryFn: () => api<AppSettings>("/api/v1/settings/"),
    });
}

export function useUpdateAppSettings() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (map_group_mode: MapGroupMode) =>
            api<AppSettings>("/api/v1/settings/", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ map_group_mode }),
            }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["appSettings"] }),
    });
}

const projectRoutesQueryKey = (projectId: number) => ["projectRoutes", projectId];

export function updateProject(id: number, payload: ProjectUpdatePayload) {
    return api<Project>("/api/v1/projects/:project_id", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        params: { path: { project_id: id } },
    });
}

// ---------------------------------------------------------------------------
// Project wizard (POST /api/v1/projects + link helpers)
// ---------------------------------------------------------------------------

export type ProjectCreatePayload = components["schemas"]["ProjectCreate"];

export function useCreateProject() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: ProjectCreatePayload) =>
            api<Project>("/api/v1/projects/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: (created) => {
            queryClient.invalidateQueries({ queryKey: ["projects"] });
            queryClient.invalidateQueries({ queryKey: ["projectDrafts"] });
            if (created.id != null) {
                queryClient.setQueryData(["project", created.id], created);
            }
        },
    });
}

// ---------------------------------------------------------------------------
// Project drafts (admin board)
// ---------------------------------------------------------------------------

/** List all draft (not yet finalized) projects. Admin-only (project.create). */
export function useDraftProjects(enabled = true) {
    return useQuery({
        queryKey: ["projectDrafts"],
        enabled,
        queryFn: () => api<Project[]>("/api/v1/projects/drafts"),
    });
}

/** Finalize a draft project (clears its draft state). */
export function useFinalizeProject() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (projectId: number) =>
            api<Project>(`/api/v1/projects/${projectId}/finalize`, { method: "POST" }),
        onSuccess: (project) => {
            queryClient.invalidateQueries({ queryKey: ["projects"] });
            queryClient.invalidateQueries({ queryKey: ["projectDrafts"] });
            if (project.id != null) {
                queryClient.setQueryData(["project", project.id], project);
            }
        },
    });
}

/** Delete a project (used to discard drafts). */
export function useDeleteProject() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (projectId: number) =>
            api<void>(`/api/v1/projects/${projectId}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["projects"] });
            queryClient.invalidateQueries({ queryKey: ["projectDrafts"] });
        },
    });
}

export function useLinkFinvesToProject(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (finveIds: number[]) =>
            api<void>(`/api/v1/projects/${projectId}/finves`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ finve_ids: finveIds }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["project-finves", projectId] });
            queryClient.invalidateQueries({ queryKey: ["finves"] });
            queryClient.invalidateQueries({ queryKey: ["admin-unassigned-finves"] });
        },
    });
}

export type ConfirmedVibEntry = components["schemas"]["VibEntryListItemSchema"];

export function useConfirmedVibEntries(enabled: boolean = true) {
    return useQuery({
        queryKey: ["vib-entries-confirmed"],
        queryFn: () => api<ConfirmedVibEntry[]>("/api/v1/import/vib/entries"),
        enabled,
    });
}

// ---------------------------------------------------------------------------
// Change tracking
// ---------------------------------------------------------------------------

export type ChangeLogEntry = components["schemas"]["ChangeLogEntryRead"];

export type ChangeLog = components["schemas"]["ChangeLogRead"];

export type TextChangeLogEntry = components["schemas"]["TextChangeLogEntryRead"];

export type TextChangeLog = components["schemas"]["TextChangeLogRead"];

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

export function useUpdateUser() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ userId, username, role }: { userId: number; username?: string; role?: string }) =>
            api<User>(`/api/v1/users/${userId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ...(username !== undefined ? { username } : {}),
                    ...(role !== undefined ? { role } : {}),
                }),
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

// ---------------------------------------------------------------------------
// Roles & permissions (admin)
// ---------------------------------------------------------------------------

export function useRoles() {
    return useQuery({
        queryKey: ["roles"],
        queryFn: () => api<Role[]>("/api/v1/roles/"),
    });
}

export function usePermissions() {
    return useQuery({
        queryKey: ["permissions"],
        queryFn: () => api<Permission[]>("/api/v1/permissions/"),
    });
}

export function useCreateRole() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: { name: string; description?: string | null; permissions: string[] }) =>
            api<Role>("/api/v1/roles/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["roles"] });
        },
    });
}

export function useUpdateRole() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({
            roleId,
            ...payload
        }: {
            roleId: number;
            name?: string;
            description?: string | null;
            permissions?: string[];
        }) =>
            api<Role>(`/api/v1/roles/${roleId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["roles"] });
        },
    });
}

export function useDeleteRole() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (roleId: number) =>
            api<void>(`/api/v1/roles/${roleId}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["roles"] });
        },
    });
}

// ---------------------------------------------------------------------------
// FinVe + Budget (Projektdetail)
// ---------------------------------------------------------------------------

export type TitelEntry = components["schemas"]["TitelEntrySchema"];

export type BudgetSummary = components["schemas"]["BudgetSummarySchema"];

export type FinveWithBudgets = components["schemas"]["FinveWithBudgetsSchema"];

export function useProjectFinves(projectId: number) {
    return useQuery({
        queryKey: ["project-finves", projectId],
        queryFn: () => api<FinveWithBudgets[]>(`/api/v1/projects/${projectId}/finves`),
        enabled: !Number.isNaN(projectId),
    });
}

export type BvwpProjectData = components["schemas"]["BvwpProjectDataSchema"];

export function useProjectBvwp(projectId: number) {
    return useQuery({
        queryKey: ["project-bvwp", projectId],
        enabled: !Number.isNaN(projectId),
        queryFn: async () => {
            try {
                return await api<BvwpProjectData>(`/api/v1/projects/${projectId}/bvwp`);
            } catch (err) {
                // 404 means no BVWP data for this project — treat as null, not an error
                if (err && typeof err === "object" && "status" in err && (err as { status: number }).status === 404) {
                    return null;
                }
                throw err;
            }
        },
    });
}

export type ProjectRef = components["schemas"]["ProjectRefSchema"];

export type FinveListItem = components["schemas"]["FinveListItemSchema"];

export function useFinves() {
    return useQuery({
        queryKey: ["finves"],
        queryFn: () => api<FinveListItem[]>("/api/v1/finves/"),
    });
}

// ---------------------------------------------------------------------------
// Haushalt-Import
// ---------------------------------------------------------------------------

export type TitelEntryProposed = components["schemas"]["TitelEntryProposed"];

export type ProposedFinve = components["schemas"]["ProposedFinve"];

export type ProposedBudget = components["schemas"]["ProposedBudget"];

export type HaushaltsParseRow = {
    finve_number: number;
    name: string;
    status: "new" | "update" | "unmatched";
    is_sammel_finve: boolean;
    erlaeuterung_projects: string[];
    erlaeuterung_suggestions: (number | null)[];
    proposed_finve: ProposedFinve | null;
    proposed_budget: ProposedBudget | null;
    proposed_titel_entries: TitelEntryProposed[];
    project_ids: number[];
    suggested_project_ids: number[];
};

export type HaushaltsParseTaskResult = {
    year: number;
    rows: HaushaltsParseRow[];
    unmatched_rows: Record<string, unknown>[];
};

export type ParseResultPublic = components["schemas"]["ParseResultPublicSchema"];

export type UnmatchedBudgetRow = components["schemas"]["UnmatchedBudgetRowSchema"];

export type HaushaltsConfirmRowInput = components["schemas"]["HaushaltsConfirmRowInput"];

export type HaushaltsConfirmRequest = components["schemas"]["HaushaltsConfirmRequest"];

export type HaushaltsConfirmResponse = components["schemas"]["HaushaltsConfirmResponse"];

export type TaskLaunchResponse = components["schemas"]["TaskLaunchResponse"];
export type TaskProgressMeta = {
    // VIB parse steps
    step?: string;
    step_label?: string;
    // legacy page-based progress (haushalt import)
    current_page?: number;
    total_pages?: number;
    rows_found?: number;
};

export type TaskStatusResponse = components["schemas"]["TaskStatusResponse"];

export function useParseResults() {
    return useQuery({
        queryKey: ["haushalt-parse-results"],
        queryFn: () => api<ParseResultPublic[]>("/api/v1/import/haushalt/parse-result"),
    });
}

export function useParseResult(id: number) {
    return useQuery({
        queryKey: ["haushalt-parse-result", id],
        enabled: Number.isFinite(id),
        queryFn: () => api<ParseResultPublic>(`/api/v1/import/haushalt/parse-result/${id}`),
    });
}

export function useTaskStatus(taskId: string | null) {
    return useQuery({
        queryKey: ["task-status", taskId],
        enabled: taskId !== null,
        refetchInterval: (query) => {
            const status = (query.state.data as TaskStatusResponse | undefined)?.status;
            return status === "SUCCESS" || status === "FAILURE" ? false : 1500;
        },
        queryFn: () => api<TaskStatusResponse>(`/api/v1/tasks/${taskId}`),
    });
}

export function useStartHaushaltsImport() {
    return useMutation({
        mutationFn: ({ pdf, year }: { pdf: File; year: number }) => {
            const form = new FormData();
            form.append("pdf", pdf);
            form.append("year", String(year));
            return api<TaskLaunchResponse>("/api/v1/import/haushalt/parse", {
                method: "POST",
                body: form,
            });
        },
    });
}

export function useDeleteParseResult() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: number) =>
            api<void>(`/api/v1/import/haushalt/parse-result/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["haushalt-parse-results"] });
        },
    });
}

export function useConfirmHaushaltsImport() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: HaushaltsConfirmRequest) =>
            api<HaushaltsConfirmResponse>("/api/v1/import/haushalt/confirm", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["haushalt-parse-results"] });
            queryClient.invalidateQueries({ queryKey: ["haushalt-unmatched"] });
        },
    });
}

export function useUnmatchedRows(resolved?: boolean) {
    return useQuery({
        queryKey: ["haushalt-unmatched", resolved],
        queryFn: () => {
            const qs = resolved !== undefined ? `?resolved=${resolved}` : "";
            return api<UnmatchedBudgetRow[]>(`/api/v1/import/haushalt/unmatched${qs}`);
        },
    });
}

export function useResolveUnmatchedRow() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ rowId, finveId }: { rowId: number; finveId: number }) =>
            api<UnmatchedBudgetRow>(`/api/v1/import/haushalt/unmatched/${rowId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ finve_id: finveId }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["haushalt-unmatched"] });
        },
    });
}

// ---------------------------------------------------------------------------
// VIB (Verkehrsinvestitionsbericht) import
// ---------------------------------------------------------------------------

export type VibPfaEntryProposed = components["schemas"]["VibPfaEntryProposed"];

export type VibEntryProposed = components["schemas"]["VibEntryProposed"];

export type VibParseTaskResult = components["schemas"]["VibParseTaskResult"];

export type VibConfirmEntryInput = components["schemas"]["VibConfirmEntryInput"];

export type VibConfirmRequest = components["schemas"]["VibConfirmRequest"];

export type VibConfirmResponse = components["schemas"]["VibConfirmResponse"];

export type VibReportSchema = components["schemas"]["VibReportSchema"];

export type VibPfaEntrySchema = components["schemas"]["VibPfaEntrySchema"];

export type VibEntrySchema = components["schemas"]["VibEntrySchema"];

export type VibEntryForProject = components["schemas"]["VibEntryForProjectSchema"];

export function useVibParseResult(taskId: string | null) {
    return useQuery({
        queryKey: ["vib-parse-result", taskId],
        enabled: taskId !== null,
        queryFn: () => api<VibParseTaskResult>(`/api/v1/import/vib/parse-result/${taskId}`),
        retry: false,
    });
}

export function useStartVibImport() {
    return useMutation({
        mutationFn: ({
            pdf,
            year,
            startPage,
            endPage,
            stripHeadersFooters = true,
        }: {
            pdf: File;
            year: number;
            startPage?: number;
            endPage?: number;
            stripHeadersFooters?: boolean;
        }) => {
            const form = new FormData();
            form.append("pdf", pdf);
            form.append("year", String(year));
            if (startPage != null) form.append("start_page", String(startPage));
            if (endPage != null) form.append("end_page", String(endPage));
            form.append("strip_headers_footers", String(stripHeadersFooters));
            return api<TaskLaunchResponse>("/api/v1/import/vib/parse", {
                method: "POST",
                body: form,
            });
        },
    });
}

export function useVibReports() {
    return useQuery({
        queryKey: ["vib-reports"],
        queryFn: () => api<VibReportSchema[]>("/api/v1/import/vib/reports"),
    });
}

export function useDeleteVibReport() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: number) =>
            api<void>(`/api/v1/import/vib/reports/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["vib-reports"] });
        },
    });
}

export function useConfirmVibImport() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: VibConfirmRequest) =>
            api<VibConfirmResponse>("/api/v1/import/vib/confirm", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["vib-reports"] });
            queryClient.invalidateQueries({ queryKey: ["vib-drafts"] });
        },
    });
}

export function useProjectVibEntries(projectId: number) {
    return useQuery({
        queryKey: ["project-vib", projectId],
        queryFn: () => api<VibEntryForProject[]>(`/api/v1/projects/${projectId}/vib`),
    });
}

export function useUpdateVibEntry() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ entryId, data }: { entryId: number; data: Partial<VibEntryProposed> }) =>
            api<VibEntrySchema>(`/api/v1/import/vib/entries/${entryId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["project-vib"] });
            queryClient.invalidateQueries({ queryKey: ["admin-unassigned-vib-entries"] });
            queryClient.invalidateQueries({ queryKey: ["vib-entries-confirmed"] });
        },
    });
}

export function useVibEntry(entryId: number | null) {
    return useQuery({
        queryKey: ["vib-entry", entryId],
        queryFn: () => api<VibEntrySchema>(`/api/v1/import/vib/entries/${entryId}`),
        enabled: entryId !== null,
    });
}

// ---------------------------------------------------------------------------
// DB-Bauportal importer (#47)
// ---------------------------------------------------------------------------

export type BauportalEntry = components["schemas"]["BauportalEntrySchema"];

export type BauportalUpdatePayload = components["schemas"]["BauportalUpdateInput"];

export type BauportalImportSummary = components["schemas"]["BauportalImportSummary"];

export function useBauportalEntries(onlyUnconfirmed = false) {
    return useQuery({
        queryKey: ["bauportal-entries", onlyUnconfirmed],
        queryFn: () =>
            api<BauportalEntry[]>(
                `/api/v1/import/bauportal/entries?only_unconfirmed=${onlyUnconfirmed}`,
            ),
    });
}

export function useFetchBauportal() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: () =>
            api<BauportalImportSummary>("/api/v1/import/bauportal/fetch", { method: "POST" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["bauportal-entries"] });
        },
    });
}

export function useUpdateBauportalEntry() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ entryId, data }: { entryId: number; data: BauportalUpdatePayload }) =>
            api<BauportalEntry>(`/api/v1/import/bauportal/entries/${entryId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            }),
        // Optimistic write-through so an assignment/confirm never appears to
        // "jump back" before the refetch; roll back if the PATCH fails.
        onMutate: async ({ entryId, data }) => {
            await queryClient.cancelQueries({ queryKey: ["bauportal-entries"] });
            const snapshots = queryClient.getQueriesData<BauportalEntry[]>({
                queryKey: ["bauportal-entries"],
            });
            queryClient.setQueriesData<BauportalEntry[]>(
                { queryKey: ["bauportal-entries"] },
                (old) => (old ? old.map((e) => (e.id === entryId ? mergeDefined(e, data) : e)) : old),
            );
            return { snapshots };
        },
        onError: (_err, _vars, context) => {
            context?.snapshots?.forEach(([key, value]) => queryClient.setQueryData(key, value));
        },
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ["bauportal-entries"] });
            queryClient.invalidateQueries({ queryKey: ["project-progress"] });
        },
    });
}

export function useConfirmAllBauportal() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: () =>
            api<{ confirmed: number }>("/api/v1/import/bauportal/confirm-all", {
                method: "POST",
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["bauportal-entries"] });
            queryClient.invalidateQueries({ queryKey: ["project-progress"] });
        },
    });
}

// ---------------------------------------------------------------------------
// Medien/Presse importer (#48)
// ---------------------------------------------------------------------------

export type MediaEntry = components["schemas"]["MediaEntrySchema"];

export type MediaUpdatePayload = components["schemas"]["MediaUpdateInput"];

export function useMediaEntries(onlyUnconfirmed = false) {
    return useQuery({
        queryKey: ["media-entries", onlyUnconfirmed],
        queryFn: () =>
            api<MediaEntry[]>(`/api/v1/import/media/entries?only_unconfirmed=${onlyUnconfirmed}`),
    });
}

export function useExtractMedia() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ url, text }: { url?: string; text?: string }) =>
            api<MediaEntry>("/api/v1/import/media/extract", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: url || null, text: text || null }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["media-entries"] });
        },
    });
}

export function useUpdateMediaEntry() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ entryId, data }: { entryId: number; data: MediaUpdatePayload }) =>
            api<MediaEntry>(`/api/v1/import/media/entries/${entryId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["media-entries"] });
            queryClient.invalidateQueries({ queryKey: ["project-progress"] });
        },
    });
}

export function useDeleteMediaEntry() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (entryId: number) =>
            api<void>(`/api/v1/import/media/entries/${entryId}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["media-entries"] });
            queryClient.invalidateQueries({ queryKey: ["project-progress"] });
        },
    });
}

// ---------------------------------------------------------------------------
// Fulda-Runde importer (#46)
// ---------------------------------------------------------------------------

export type FuldaEntry = components["schemas"]["FuldaEntrySchema"];

export type FuldaParseSummary = {
    ocr_status: string;
    created: number;
    source_label: string | null;
};

export type FuldaYearSummary = components["schemas"]["FuldaYearSummary"];

export type FuldaUpdatePayload = components["schemas"]["FuldaUpdateInput"];

export function useFuldaEntries(onlyUnconfirmed = false, year: number | null = null) {
    return useQuery({
        queryKey: ["fulda-entries", onlyUnconfirmed, year],
        queryFn: () => {
            const params = new URLSearchParams({ only_unconfirmed: String(onlyUnconfirmed) });
            if (year != null) params.set("year", String(year));
            return api<FuldaEntry[]>(`/api/v1/import/fulda/entries?${params.toString()}`);
        },
    });
}

export function useFuldaYearSummaries() {
    return useQuery({
        queryKey: ["fulda-year-summaries"],
        queryFn: () => api<FuldaYearSummary[]>("/api/v1/import/fulda/year-summaries"),
    });
}

export function useParseFulda() {
    return useMutation({
        mutationFn: ({ file, year }: { file: File; year: number }) => {
            const form = new FormData();
            form.append("pdf", file);
            form.append("year", String(year));
            // OCR + LLM run in a Celery task; poll via useTaskStatus. The
            // fulda query keys are invalidated when the task reaches SUCCESS.
            return api<TaskLaunchResponse>("/api/v1/import/fulda/parse", {
                method: "POST",
                body: form,
            });
        },
    });
}

export function useUpdateFuldaEntry() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ entryId, data }: { entryId: number; data: FuldaUpdatePayload }) =>
            api<FuldaEntry>(`/api/v1/import/fulda/entries/${entryId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            }),
        // Optimistic write-through: reflect the edit in every cached entries list
        // immediately so a change never appears to "jump back" before the refetch,
        // and roll back if the PATCH fails.
        onMutate: async ({ entryId, data }) => {
            await queryClient.cancelQueries({ queryKey: ["fulda-entries"] });
            const snapshots = queryClient.getQueriesData<FuldaEntry[]>({
                queryKey: ["fulda-entries"],
            });
            queryClient.setQueriesData<FuldaEntry[]>({ queryKey: ["fulda-entries"] }, (old) =>
                old ? old.map((e) => (e.id === entryId ? mergeDefined(e, data) : e)) : old,
            );
            return { snapshots };
        },
        onError: (_err, _vars, context) => {
            context?.snapshots?.forEach(([key, value]) =>
                queryClient.setQueryData(key, value),
            );
        },
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ["fulda-entries"] });
            queryClient.invalidateQueries({ queryKey: ["fulda-year-summaries"] });
            queryClient.invalidateQueries({ queryKey: ["project-progress"] });
        },
    });
}

export function useDeleteFuldaEntry() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (entryId: number) =>
            api<void>(`/api/v1/import/fulda/entries/${entryId}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["fulda-entries"] });
            queryClient.invalidateQueries({ queryKey: ["fulda-year-summaries"] });
            queryClient.invalidateQueries({ queryKey: ["project-progress"] });
        },
    });
}

export function useConfirmFuldaYear() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (year: number) =>
            api<{ confirmed: number }>(`/api/v1/import/fulda/years/${year}/confirm`, {
                method: "POST",
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["fulda-entries"] });
            queryClient.invalidateQueries({ queryKey: ["fulda-year-summaries"] });
            queryClient.invalidateQueries({ queryKey: ["project-progress"] });
        },
    });
}

export function useDeleteFuldaYear() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (year: number) =>
            api<void>(`/api/v1/import/fulda/years/${year}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["fulda-entries"] });
            queryClient.invalidateQueries({ queryKey: ["fulda-years"] });
            queryClient.invalidateQueries({ queryKey: ["fulda-year-summaries"] });
            queryClient.invalidateQueries({ queryKey: ["project-progress"] });
        },
    });
}

export function useVibAiAvailable() {
    return useQuery({
        queryKey: ["vib-ai-available"],
        queryFn: () => api<{ available: boolean; model: string | null }>("/api/v1/import/vib/ai-available"),
    });
}

export function useVibOcrAvailable() {
    return useQuery({
        queryKey: ["vib-ocr-available"],
        queryFn: () => api<{ available: boolean; model: string | null }>("/api/v1/import/vib/ocr-available"),
    });
}

export function useSaveVibDraft() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ taskId, data }: { taskId: string; data: VibParseTaskResult }) =>
            api<void>(`/api/v1/import/vib/draft/${taskId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            }),
        onSuccess: (_, { taskId, data }) => {
            queryClient.setQueryData(["vib-parse-result", taskId], data);
        },
    });
}

export function useRetryVibAiForEntry() {
    return useMutation({
        mutationFn: ({ taskId, entryIdx }: { taskId: string; entryIdx: number }) =>
            api<VibEntryProposed>(`/api/v1/import/vib/extract-ai/${taskId}/entry/${entryIdx}`, {
                method: "POST",
            }),
    });
}

export type VibDraftSchema = components["schemas"]["VibDraftSchema"];

export function useVibDrafts() {
    return useQuery({
        queryKey: ["vib-drafts"],
        queryFn: () => api<VibDraftSchema[]>("/api/v1/import/vib/drafts"),
    });
}

export function useDeleteVibDraft() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (taskId: string) =>
            api<void>(`/api/v1/import/vib/drafts/${taskId}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["vib-drafts"] });
        },
    });
}

// ---------------------------------------------------------------------------
// Admin: Offene Zuordnungen (unassigned FinVe / VIB entries)
// ---------------------------------------------------------------------------

export type UnassignedFinve = components["schemas"]["UnassignedFinveSchema"];

export type UnassignedVibEntry = components["schemas"]["UnassignedVibEntrySchema"];

export function useUnassignedFinves(enabled = true) {
    return useQuery({
        queryKey: ["admin-unassigned-finves"],
        queryFn: () => api<UnassignedFinve[]>("/api/v1/admin/unassigned-finves"),
        enabled,
    });
}

export function useUnassignedVibEntries(enabled = true) {
    return useQuery({
        queryKey: ["admin-unassigned-vib-entries"],
        queryFn: () => api<UnassignedVibEntry[]>("/api/v1/admin/unassigned-vib-entries"),
        enabled,
    });
}

export function useAssignFinve() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ finveId, projectIds }: { finveId: number; projectIds: number[] }) =>
            api<void>(`/api/v1/admin/unassigned-finves/${finveId}/assign`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ project_ids: projectIds }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["admin-unassigned-finves"] });
        },
    });
}

export function useAssignVibEntry() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ entryId, projectIds }: { entryId: number; projectIds: number[] }) =>
            api<void>(`/api/v1/admin/unassigned-vib-entries/${entryId}/assign`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ project_ids: projectIds }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["admin-unassigned-vib-entries"] });
        },
    });
}

// ---------------------------------------------------------------------------
// Routing / Geometry management
// ---------------------------------------------------------------------------

export type OperationalPointRef = components["schemas"]["OperationalPointRef"];

// The backend types the preview Feature loosely (dict); the concrete shape is
// stable (services/route_service.py) and narrowed here on top of the schema.
export type RoutePreviewFeature = Omit<
    components["schemas"]["RoutePreviewOut"],
    "geometry" | "properties"
> & {
    geometry: { type: "LineString"; coordinates: number[][] };
    properties: {
        distance_m: number;
        duration_ms: number;
        profile: string;
        graph_version: string;
        bbox: number[];
        details: Record<string, unknown>;
        cache_key: string;
    };
};

export function useOperationalPointSearch(q: string) {
    return useQuery({
        queryKey: ["operational-points", q],
        enabled: q.length >= 2,
        queryFn: () =>
            api<OperationalPointRef[]>(`/api/v1/operational-points/?q=${encodeURIComponent(q)}&limit=20`),
        staleTime: 30_000,
    });
}

export function useCalculateRoute() {
    return useMutation({
        mutationFn: (payload: {
            waypoints: Array<{ lat: number; lon: number }>;
            profile?: string;
        }) =>
            api<RoutePreviewFeature>("/api/v1/routes/calculate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ profile: "rail_default", options: {}, ...payload }),
            }),
    });
}

export function useConfirmRoute(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (feature: RoutePreviewFeature) =>
            api<ProjectRoute>(`/api/v1/projects/${projectId}/routes`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ feature }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: projectRoutesQueryKey(projectId) });
        },
    });
}

export function useUpdateProjectGeometry(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (geojson_representation: string | null) =>
            updateProject(projectId, { geojson_representation }),
        onSuccess: (updatedProject) => {
            queryClient.setQueryData(["project", projectId], updatedProject);
            queryClient.invalidateQueries({ queryKey: ["projects"] });
        },
    });
}

// ---------------------------------------------------------------------------
// To-dos (Aufgaben)
// ---------------------------------------------------------------------------

export type Todo = components["schemas"]["TodoSchema"];
export type TodoCreate = components["schemas"]["TodoCreate"];
export type TodoUpdate = components["schemas"]["TodoUpdate"];
export type TodoStatus = Todo["status"];
export type TodoPriority = Todo["priority"];
export type UserOption = components["schemas"]["UserOption"];

export type TodoFilters = {
    status?: TodoStatus;
    priority?: TodoPriority;
    assignee_id?: number;
    project_id?: number;
    created_by_id?: number;
    include_done?: boolean;
};

const todosKey = (filters?: TodoFilters) =>
    filters ? (["todos", filters] as const) : (["todos"] as const);

function buildTodoQuery(filters?: TodoFilters): string {
    if (!filters) return "";
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    if (filters.priority) params.set("priority", filters.priority);
    if (filters.assignee_id != null) params.set("assignee_id", String(filters.assignee_id));
    if (filters.project_id != null) params.set("project_id", String(filters.project_id));
    if (filters.created_by_id != null) params.set("created_by_id", String(filters.created_by_id));
    if (filters.include_done != null) params.set("include_done", String(filters.include_done));
    const qs = params.toString();
    return qs ? `?${qs}` : "";
}

/** List tasks (logged-in users only). Pass `enabled: false` when logged out. */
export function useTodos(filters?: TodoFilters, enabled = true) {
    return useQuery({
        queryKey: todosKey(filters),
        enabled,
        queryFn: () => api<Todo[]>(`/api/v1/todos/${buildTodoQuery(filters)}`),
    });
}

/** Minimal user list (id + username) for the assignee picker. */
export function useUserOptions(enabled = true) {
    return useQuery({
        queryKey: ["user-options"],
        enabled,
        queryFn: () => api<UserOption[]>(`/api/v1/users/options`),
    });
}

export function useCreateTodo() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: TodoCreate) =>
            api<Todo>(`/api/v1/todos/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["todos"] });
        },
    });
}

export function useUpdateTodo() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ id, payload }: { id: number; payload: TodoUpdate }) =>
            api<Todo>(`/api/v1/todos/${id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["todos"] });
        },
    });
}

export function useDeleteTodo() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: number) =>
            api<void>(`/api/v1/todos/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["todos"] });
        },
    });
}

// --- Guides ("Anleitungen") section overrides --------------------------------

export type GuideOverride = components["schemas"]["GuideOverrideSchema"];

export function useGuideOverrides(guideSlug: string) {
    return useQuery({
        queryKey: ["guide-overrides", guideSlug],
        queryFn: () => api<GuideOverride[]>(`/api/v1/guides/${guideSlug}/overrides`),
    });
}

export function useSaveGuideOverride() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({
            guideSlug,
            sectionKey,
            bodyMarkdown,
        }: {
            guideSlug: string;
            sectionKey: string;
            bodyMarkdown: string;
        }) =>
            api<GuideOverride>(`/api/v1/guides/${guideSlug}/overrides/${sectionKey}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ body_markdown: bodyMarkdown }),
            }),
        onSuccess: (_data, { guideSlug }) => {
            queryClient.invalidateQueries({ queryKey: ["guide-overrides", guideSlug] });
        },
    });
}

export function useDeleteGuideOverride() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ guideSlug, sectionKey }: { guideSlug: string; sectionKey: string }) =>
            api<void>(`/api/v1/guides/${guideSlug}/overrides/${sectionKey}`, {
                method: "DELETE",
            }),
        onSuccess: (_data, { guideSlug }) => {
            queryClient.invalidateQueries({ queryKey: ["guide-overrides", guideSlug] });
        },
    });
}
