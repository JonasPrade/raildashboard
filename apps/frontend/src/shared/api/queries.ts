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

/**
 * Single source of truth for react-query cache keys. A typo'd string literal
 * silently breaks invalidation, so keys live only here: bare arrays are also
 * the prefix that matches every parameterised variant (e.g. queryKeys.progress
 * invalidates all per-project progress queries).
 */
export const queryKeys = {
    textTypes: ["textTypes"],
    projects: ["projects"],
    project: (id: number) => ["project", id] as const,
    projectTexts: (projectId: number) => ["projectTexts", projectId] as const,
    projectDrafts: ["projectDrafts"],
    projectGroups: ["projectGroups"],
    appSettings: ["appSettings"],
    projectRoutes: (projectId: number) => ["projectRoutes", projectId] as const,
    progress: ["project-progress"],
    progressFor: (projectId: number) => ["project-progress", projectId] as const,
    sammelFinveProgress: ["sammel-finve-progress"],
    projectFinves: (projectId: number) => ["project-finves", projectId] as const,
    projectBvwp: (projectId: number) => ["project-bvwp", projectId] as const,
    projectVib: ["project-vib"],
    projectVibFor: (projectId: number) => ["project-vib", projectId] as const,
    projectChangelog: (projectId: number) => ["project-changelog", projectId] as const,
    projectTextChangelog: (projectId: number) => ["project-text-changelog", projectId] as const,
    finves: ["finves"],
    users: ["users"],
    userOptions: ["user-options"],
    roles: ["roles"],
    permissions: ["permissions"],
    haushaltParseResults: ["haushalt-parse-results"],
    haushaltParseResult: (id: number) => ["haushalt-parse-result", id] as const,
    haushaltUnmatched: ["haushalt-unmatched"],
    haushaltUnmatchedFor: (resolved?: boolean) => ["haushalt-unmatched", resolved] as const,
    taskStatus: (taskId: string | null) => ["task-status", taskId] as const,
    vibParseResult: (taskId: string | null) => ["vib-parse-result", taskId] as const,
    vibReports: ["vib-reports"],
    vibDrafts: ["vib-drafts"],
    vibEntry: (entryId: number | null) => ["vib-entry", entryId] as const,
    vibEntriesConfirmed: ["vib-entries-confirmed"],
    vibAiAvailable: ["vib-ai-available"],
    vibOcrAvailable: ["vib-ocr-available"],
    adminUnassignedFinves: ["admin-unassigned-finves"],
    adminUnassignedVibEntries: ["admin-unassigned-vib-entries"],
    bauportalEntries: ["bauportal-entries"],
    bauportalEntriesFor: (onlyUnconfirmed: boolean) => ["bauportal-entries", onlyUnconfirmed] as const,
    mediaEntries: ["media-entries"],
    mediaEntriesFor: (onlyUnconfirmed: boolean) => ["media-entries", onlyUnconfirmed] as const,
    fuldaEntries: ["fulda-entries"],
    fuldaEntriesFor: (onlyUnconfirmed: boolean, year: number | null) =>
        ["fulda-entries", onlyUnconfirmed, year] as const,
    fuldaYears: ["fulda-years"],
    fuldaYearSummaries: ["fulda-year-summaries"],
    operationalPoints: (q: string) => ["operational-points", q] as const,
    todos: ["todos"],
    guideOverrides: (guideSlug: string) => ["guide-overrides", guideSlug] as const,
} as const;

type InvalidateKeys<TData, TVariables> =
    | ReadonlyArray<readonly unknown[]>
    | ((data: TData, variables: TVariables) => ReadonlyArray<readonly unknown[]>);

/**
 * The standard mutation shape: run ``mutationFn``, then invalidate a fixed
 * (or variables-derived) set of query keys. Covers every mutation without
 * extra cache writes; hooks with setQueryData/optimistic logic stay explicit.
 */
export function useInvalidatingMutation<TData, TVariables = void>(
    mutationFn: (variables: TVariables) => Promise<TData>,
    keys: InvalidateKeys<TData, TVariables>,
) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn,
        onSuccess: (data, variables) => {
            const resolved = typeof keys === "function" ? keys(data, variables) : keys;
            for (const key of resolved) {
                queryClient.invalidateQueries({ queryKey: key });
            }
        },
    });
}

/**
 * PATCH one entry of a cached list optimistically: cancel in-flight fetches,
 * snapshot every matching list, merge the patch into the entry (defined keys
 * only), roll back on error and refetch on settle. Shared by the Bauportal and
 * Fulda review tables.
 */
function useOptimisticEntryPatch<TEntry extends { id: number }, TData, TPatch extends object>(config: {
    listKey: readonly unknown[];
    settledKeys: ReadonlyArray<readonly unknown[]>;
    mutationFn: (variables: { entryId: number; data: TPatch }) => Promise<TData>;
}) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: config.mutationFn,
        onMutate: async ({ entryId, data }) => {
            await queryClient.cancelQueries({ queryKey: config.listKey });
            const snapshots = queryClient.getQueriesData<TEntry[]>({ queryKey: config.listKey });
            queryClient.setQueriesData<TEntry[]>({ queryKey: config.listKey }, (old) =>
                old ? old.map((e) => (e.id === entryId ? mergeDefined(e, data) : e)) : old,
            );
            return { snapshots };
        },
        onError: (_err, _vars, context) => {
            context?.snapshots?.forEach(([key, value]) => queryClient.setQueryData(key, value));
        },
        onSettled: () => {
            for (const key of config.settledKeys) {
                queryClient.invalidateQueries({ queryKey: key });
            }
        },
    });
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
        queryKey: queryKeys.textTypes,
        queryFn: () => api<ProjectTextType[]>("/api/v1/text_types"),
    });
}

export function useCreateTextType() {
    return useInvalidatingMutation(
        (name: string) =>
            api<ProjectTextType>("/api/v1/text_types", {
                method: "POST",
                json: { name },
            }),
        [queryKeys.textTypes],
    );
}

export function useProjectTexts(projectId: number) {
    return useQuery({
        queryKey: queryKeys.projectTexts(projectId),
        enabled: Number.isFinite(projectId),
        queryFn: () =>
            api<ProjectText[]>(`/api/v1/projects/${projectId}/texts`),
    });
}

export function useCreateProjectText(projectId: number) {
    return useInvalidatingMutation(
        (payload: ProjectTextCreate) =>
            api<ProjectText>(`/api/v1/projects/${projectId}/texts`, {
                method: "POST",
                json: payload,
            }),
        [queryKeys.projectTexts(projectId)],
    );
}

export function useUpdateProjectText(projectId: number) {
    return useInvalidatingMutation(
        ({ textId, payload }: { textId: number; payload: ProjectTextUpdate }) =>
            api<ProjectText>(`/api/v1/projects/texts/${textId}`, {
                method: "PATCH",
                json: payload,
            }),
        [queryKeys.projectTexts(projectId)],
    );
}

export function useDeleteProjectText(projectId: number) {
    return useInvalidatingMutation(
        (textId: number) =>
            api<void>(`/api/v1/projects/texts/${textId}`, { method: "DELETE" }),
        [queryKeys.projectTexts(projectId)],
    );
}

export function useUploadTextAttachment(projectId: number) {
    return useInvalidatingMutation(
        ({ textId, file }: { textId: number; file: File }) => {
            const formData = new FormData();
            formData.append("file", file);
            // No Content-Type header — browser sets multipart/form-data with boundary
            return api<TextAttachment>(`/api/v1/projects/texts/${textId}/attachments`, {
                method: "POST",
                body: formData,
            });
        },
        [queryKeys.projectTexts(projectId)],
    );
}

export function useDeleteTextAttachment(projectId: number) {
    return useInvalidatingMutation(
        ({ textId, attachmentId }: { textId: number; attachmentId: number }) =>
            api<void>(`/api/v1/projects/texts/${textId}/attachments/${attachmentId}`, {
                method: "DELETE",
            }),
        [queryKeys.projectTexts(projectId)],
    );
}

export function useProjects() {
    return useQuery({
        queryKey: queryKeys.projects,
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

export function useProjectProgress(projectId: number) {
    return useQuery({
        queryKey: queryKeys.progressFor(projectId),
        enabled: Number.isFinite(projectId),
        queryFn: () => api<ProjectProgress>(`/api/v1/projects/${projectId}/progress`),
    });
}

export function useUpdateProjectProgress(projectId: number) {
    return useInvalidatingMutation(
        (payload: ProjectProgressUpdate) =>
            api<ProjectProgress>(`/api/v1/projects/${projectId}/progress`, {
                method: "PATCH",
                json: payload,
            }),
        [queryKeys.progressFor(projectId)],
    );
}

export function useAddProgressObservation(projectId: number) {
    return useInvalidatingMutation(
        (payload: ProgressObservationCreate) =>
            api<ProjectProgress>(`/api/v1/projects/${projectId}/progress/observations`, {
                method: "POST",
                json: payload,
            }),
        [queryKeys.progressFor(projectId)],
    );
}

export function useDeleteProgressObservation(projectId: number) {
    return useInvalidatingMutation(
        (observationId: number) =>
            api<ProjectProgress>(
                `/api/v1/projects/${projectId}/progress/observations/${observationId}`,
                { method: "DELETE" },
            ),
        [queryKeys.progressFor(projectId)],
    );
}

export type SammelFinveProgress = components["schemas"]["SammelFinveProgressSchema"];

export function useSammelFinveProgress() {
    return useQuery({
        queryKey: queryKeys.sammelFinveProgress,
        queryFn: () => api<SammelFinveProgress[]>("/api/v1/finves/sammel-progress"),
    });
}

export function useSetFinveProgressPhase() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ finveId, phase }: { finveId: number; phase: string | null }) =>
            api<SammelFinveProgress[]>(`/api/v1/finves/${finveId}/progress-phase`, {
                method: "PATCH",
                json: { progress_phase: phase },
            }),
        onSuccess: (data) => {
            queryClient.setQueryData(queryKeys.sammelFinveProgress, data);
            // A changed mapping affects derived progress on linked projects.
            queryClient.invalidateQueries({ queryKey: queryKeys.progress });
        },
    });
}

export function useRecomputeProgress(projectId: number) {
    return useInvalidatingMutation(
        () =>
            api<ProjectProgress>(`/api/v1/projects/${projectId}/progress/recompute`, {
                method: "POST",
            }),
        [queryKeys.progressFor(projectId)],
    );
}

export function useProject(id: number) {
    return useQuery({
        queryKey: queryKeys.project(id),
        enabled: Number.isFinite(id),
        queryFn: () =>
            api<Project>("/api/v1/projects/:project_id", {
                params: { path: { project_id: id } },
            }),
    });
}

export function useProjectGroups() {
    return useQuery({
        queryKey: queryKeys.projectGroups,
        queryFn: () => api<ProjectGroup[]>("/api/v1/project_groups/"),
    });
}

export type ProjectGroupCreatePayload = components["schemas"]["ProjectGroupCreate"];

export type ProjectGroupUpdatePayload = components["schemas"]["ProjectGroupUpdate"];

export function useCreateProjectGroup() {
    return useInvalidatingMutation(
        (payload: ProjectGroupCreatePayload) =>
            api<ProjectGroup>("/api/v1/project_groups/", {
                method: "POST",
                json: payload,
            }),
        [queryKeys.projectGroups],
    );
}

export function useUpdateProjectGroup() {
    return useInvalidatingMutation(
        ({ groupId, ...payload }: { groupId: number } & ProjectGroupUpdatePayload) =>
            api<ProjectGroup>(`/api/v1/project_groups/${groupId}`, {
                method: "PATCH",
                json: payload,
            }),
        [queryKeys.projectGroups],
    );
}

export function useDeleteProjectGroup() {
    return useInvalidatingMutation(
        (groupId: number) =>
            api<void>(`/api/v1/project_groups/${groupId}`, { method: "DELETE" }),
        [queryKeys.projectGroups],
    );
}

export type MapGroupMode = AppSettings["map_group_mode"];
export type AppSettings = components["schemas"]["AppSettingsSchema"];

export function useAppSettings() {
    return useQuery({
        queryKey: queryKeys.appSettings,
        queryFn: () => api<AppSettings>("/api/v1/settings/"),
    });
}

export function useUpdateAppSettings() {
    return useInvalidatingMutation(
        (map_group_mode: MapGroupMode) =>
            api<AppSettings>("/api/v1/settings/", {
                method: "PATCH",
                json: { map_group_mode },
            }),
        [queryKeys.appSettings],
    );
}

export function updateProject(id: number, payload: ProjectUpdatePayload) {
    return api<Project>("/api/v1/projects/:project_id", {
        method: "PATCH",
        json: payload,
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
                json: payload,
            }),
        onSuccess: (created) => {
            queryClient.invalidateQueries({ queryKey: queryKeys.projects });
            queryClient.invalidateQueries({ queryKey: queryKeys.projectDrafts });
            if (created.id != null) {
                queryClient.setQueryData(queryKeys.project(created.id), created);
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
        queryKey: queryKeys.projectDrafts,
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
            queryClient.invalidateQueries({ queryKey: queryKeys.projects });
            queryClient.invalidateQueries({ queryKey: queryKeys.projectDrafts });
            if (project.id != null) {
                queryClient.setQueryData(queryKeys.project(project.id), project);
            }
        },
    });
}

/** Delete a project (used to discard drafts). */
export function useDeleteProject() {
    return useInvalidatingMutation(
        (projectId: number) =>
            api<void>(`/api/v1/projects/${projectId}`, { method: "DELETE" }),
        [
            queryKeys.projects,
            queryKeys.projectDrafts,
        ],
    );
}

export function useLinkFinvesToProject(projectId: number) {
    return useInvalidatingMutation(
        (finveIds: number[]) =>
            api<void>(`/api/v1/projects/${projectId}/finves`, {
                method: "POST",
                json: { finve_ids: finveIds },
            }),
        [
            queryKeys.projectFinves(projectId),
            queryKeys.finves,
            queryKeys.adminUnassignedFinves,
        ],
    );
}

export type ConfirmedVibEntry = components["schemas"]["VibEntryListItemSchema"];

export function useConfirmedVibEntries(enabled: boolean = true) {
    return useQuery({
        queryKey: queryKeys.vibEntriesConfirmed,
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
        queryKey: queryKeys.projectChangelog(projectId),
        enabled: Number.isFinite(projectId),
        queryFn: () => api<ChangeLog[]>(`/api/v1/projects/${projectId}/changelog`),
    });
}

export function useProjectTextChangelog(projectId: number) {
    return useQuery({
        queryKey: queryKeys.projectTextChangelog(projectId),
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
                json: { changelog_entry_id: changelogEntryId },
            }),
        onSuccess: (updatedProject) => {
            queryClient.setQueryData(queryKeys.project(projectId), updatedProject);
            queryClient.invalidateQueries({ queryKey: queryKeys.projects });
            queryClient.invalidateQueries({ queryKey: queryKeys.projectChangelog(projectId) });
        },
    });
}

// ---------------------------------------------------------------------------
// User management hooks (admin only)
// ---------------------------------------------------------------------------

export function useUsers() {
    return useQuery({
        queryKey: queryKeys.users,
        queryFn: () => api<User[]>("/api/v1/users/"),
    });
}

export function useCreateUser() {
    return useInvalidatingMutation(
        (payload: { username: string; password: string; role: string }) =>
            api<User>("/api/v1/users/", {
                method: "POST",
                json: payload,
            }),
        [queryKeys.users],
    );
}

export function useUpdateUserRole() {
    return useInvalidatingMutation(
        ({ userId, role }: { userId: number; role: string }) =>
            api<User>(`/api/v1/users/${userId}`, {
                method: "PATCH",
                json: { role },
            }),
        [queryKeys.users],
    );
}

export function useUpdateUser() {
    return useInvalidatingMutation(
        ({ userId, username, role }: { userId: number; username?: string; role?: string }) =>
            api<User>(`/api/v1/users/${userId}`, {
                method: "PATCH",
                json: {
                    ...(username !== undefined ? { username } : {}),
                    ...(role !== undefined ? { role } : {}),
                },
            }),
        [queryKeys.users],
    );
}

export function useDeleteUser() {
    return useInvalidatingMutation(
        (userId: number) =>
            api<void>(`/api/v1/users/${userId}`, { method: "DELETE" }),
        [queryKeys.users],
    );
}

export function useSetUserPassword() {
    return useMutation({
        mutationFn: ({ userId, password }: { userId: number; password: string }) =>
            api<void>(`/api/v1/users/${userId}/password`, {
                method: "PATCH",
                json: { password },
            }),
    });
}

// ---------------------------------------------------------------------------
// Roles & permissions (admin)
// ---------------------------------------------------------------------------

export function useRoles() {
    return useQuery({
        queryKey: queryKeys.roles,
        queryFn: () => api<Role[]>("/api/v1/roles/"),
    });
}

export function usePermissions() {
    return useQuery({
        queryKey: queryKeys.permissions,
        queryFn: () => api<Permission[]>("/api/v1/permissions/"),
    });
}

export function useCreateRole() {
    return useInvalidatingMutation(
        (payload: { name: string; description?: string | null; permissions: string[] }) =>
            api<Role>("/api/v1/roles/", {
                method: "POST",
                json: payload,
            }),
        [queryKeys.roles],
    );
}

export function useUpdateRole() {
    return useInvalidatingMutation(
        ({
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
                json: payload,
            }),
        [queryKeys.roles],
    );
}

export function useDeleteRole() {
    return useInvalidatingMutation(
        (roleId: number) =>
            api<void>(`/api/v1/roles/${roleId}`, { method: "DELETE" }),
        [queryKeys.roles],
    );
}

// ---------------------------------------------------------------------------
// FinVe + Budget (Projektdetail)
// ---------------------------------------------------------------------------

export type TitelEntry = components["schemas"]["TitelEntrySchema"];

export type BudgetSummary = components["schemas"]["BudgetSummarySchema"];

export type FinveWithBudgets = components["schemas"]["FinveWithBudgetsSchema"];

export function useProjectFinves(projectId: number) {
    return useQuery({
        queryKey: queryKeys.projectFinves(projectId),
        queryFn: () => api<FinveWithBudgets[]>(`/api/v1/projects/${projectId}/finves`),
        enabled: !Number.isNaN(projectId),
    });
}

export type BvwpProjectData = components["schemas"]["BvwpProjectDataSchema"];

export function useProjectBvwp(projectId: number) {
    return useQuery({
        queryKey: queryKeys.projectBvwp(projectId),
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
        queryKey: queryKeys.finves,
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
        queryKey: queryKeys.haushaltParseResults,
        queryFn: () => api<ParseResultPublic[]>("/api/v1/import/haushalt/parse-result"),
    });
}

export function useParseResult(id: number) {
    return useQuery({
        queryKey: queryKeys.haushaltParseResult(id),
        enabled: Number.isFinite(id),
        queryFn: () => api<ParseResultPublic>(`/api/v1/import/haushalt/parse-result/${id}`),
    });
}

export function useTaskStatus(taskId: string | null) {
    return useQuery({
        queryKey: queryKeys.taskStatus(taskId),
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
    return useInvalidatingMutation(
        (id: number) =>
            api<void>(`/api/v1/import/haushalt/parse-result/${id}`, { method: "DELETE" }),
        [queryKeys.haushaltParseResults],
    );
}

export function useConfirmHaushaltsImport() {
    return useInvalidatingMutation(
        (payload: HaushaltsConfirmRequest) =>
            api<HaushaltsConfirmResponse>("/api/v1/import/haushalt/confirm", {
                method: "POST",
                json: payload,
            }),
        [
            queryKeys.haushaltParseResults,
            queryKeys.haushaltUnmatched,
        ],
    );
}

export function useUnmatchedRows(resolved?: boolean) {
    return useQuery({
        queryKey: queryKeys.haushaltUnmatchedFor(resolved),
        queryFn: () => {
            const qs = resolved !== undefined ? `?resolved=${resolved}` : "";
            return api<UnmatchedBudgetRow[]>(`/api/v1/import/haushalt/unmatched${qs}`);
        },
    });
}

export function useResolveUnmatchedRow() {
    return useInvalidatingMutation(
        ({ rowId, finveId }: { rowId: number; finveId: number }) =>
            api<UnmatchedBudgetRow>(`/api/v1/import/haushalt/unmatched/${rowId}`, {
                method: "PATCH",
                json: { finve_id: finveId },
            }),
        [queryKeys.haushaltUnmatched],
    );
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
        queryKey: queryKeys.vibParseResult(taskId),
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
        queryKey: queryKeys.vibReports,
        queryFn: () => api<VibReportSchema[]>("/api/v1/import/vib/reports"),
    });
}

export function useDeleteVibReport() {
    return useInvalidatingMutation(
        (id: number) =>
            api<void>(`/api/v1/import/vib/reports/${id}`, { method: "DELETE" }),
        [queryKeys.vibReports],
    );
}

export function useConfirmVibImport() {
    return useInvalidatingMutation(
        (payload: VibConfirmRequest) =>
            api<VibConfirmResponse>("/api/v1/import/vib/confirm", {
                method: "POST",
                json: payload,
            }),
        [
            queryKeys.vibReports,
            queryKeys.vibDrafts,
        ],
    );
}

export function useProjectVibEntries(projectId: number) {
    return useQuery({
        queryKey: queryKeys.projectVibFor(projectId),
        queryFn: () => api<VibEntryForProject[]>(`/api/v1/projects/${projectId}/vib`),
    });
}

export function useUpdateVibEntry() {
    return useInvalidatingMutation(
        ({ entryId, data }: { entryId: number; data: Partial<VibEntryProposed> }) =>
            api<VibEntrySchema>(`/api/v1/import/vib/entries/${entryId}`, {
                method: "PATCH",
                json: data,
            }),
        [
            queryKeys.projectVib,
            queryKeys.adminUnassignedVibEntries,
            queryKeys.vibEntriesConfirmed,
        ],
    );
}

export function useVibEntry(entryId: number | null) {
    return useQuery({
        queryKey: queryKeys.vibEntry(entryId),
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
        queryKey: queryKeys.bauportalEntriesFor(onlyUnconfirmed),
        queryFn: () =>
            api<BauportalEntry[]>(
                `/api/v1/import/bauportal/entries?only_unconfirmed=${onlyUnconfirmed}`,
            ),
    });
}

export function useFetchBauportal() {
    return useInvalidatingMutation(
        () =>
            api<BauportalImportSummary>("/api/v1/import/bauportal/fetch", { method: "POST" }),
        [queryKeys.bauportalEntries],
    );
}

export function useUpdateBauportalEntry() {
    // Optimistic write-through so an assignment/confirm never appears to
    // "jump back" before the refetch; rolls back if the PATCH fails.
    return useOptimisticEntryPatch<BauportalEntry, BauportalEntry, BauportalUpdatePayload>({
        listKey: queryKeys.bauportalEntries,
        settledKeys: [queryKeys.bauportalEntries, queryKeys.progress],
        mutationFn: ({ entryId, data }) =>
            api<BauportalEntry>(`/api/v1/import/bauportal/entries/${entryId}`, {
                method: "PATCH",
                json: data,
            }),
    });
}

export function useConfirmAllBauportal() {
    return useInvalidatingMutation(
        () =>
            api<{ confirmed: number }>("/api/v1/import/bauportal/confirm-all", {
                method: "POST",
            }),
        [
            queryKeys.bauportalEntries,
            queryKeys.progress,
        ],
    );
}

// ---------------------------------------------------------------------------
// Medien/Presse importer (#48)
// ---------------------------------------------------------------------------

export type MediaEntry = components["schemas"]["MediaEntrySchema"];

export type MediaUpdatePayload = components["schemas"]["MediaUpdateInput"];

export function useMediaEntries(onlyUnconfirmed = false) {
    return useQuery({
        queryKey: queryKeys.mediaEntriesFor(onlyUnconfirmed),
        queryFn: () =>
            api<MediaEntry[]>(`/api/v1/import/media/entries?only_unconfirmed=${onlyUnconfirmed}`),
    });
}

export function useExtractMedia() {
    return useInvalidatingMutation(
        ({ url, text }: { url?: string; text?: string }) =>
            api<MediaEntry>("/api/v1/import/media/extract", {
                method: "POST",
                json: { url: url || null, text: text || null },
            }),
        [queryKeys.mediaEntries],
    );
}

export function useUpdateMediaEntry() {
    return useInvalidatingMutation(
        ({ entryId, data }: { entryId: number; data: MediaUpdatePayload }) =>
            api<MediaEntry>(`/api/v1/import/media/entries/${entryId}`, {
                method: "PATCH",
                json: data,
            }),
        [
            queryKeys.mediaEntries,
            queryKeys.progress,
        ],
    );
}

export function useDeleteMediaEntry() {
    return useInvalidatingMutation(
        (entryId: number) =>
            api<void>(`/api/v1/import/media/entries/${entryId}`, { method: "DELETE" }),
        [
            queryKeys.mediaEntries,
            queryKeys.progress,
        ],
    );
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
        queryKey: queryKeys.fuldaEntriesFor(onlyUnconfirmed, year),
        queryFn: () => {
            const params = new URLSearchParams({ only_unconfirmed: String(onlyUnconfirmed) });
            if (year != null) params.set("year", String(year));
            return api<FuldaEntry[]>(`/api/v1/import/fulda/entries?${params.toString()}`);
        },
    });
}

export function useFuldaYearSummaries() {
    return useQuery({
        queryKey: queryKeys.fuldaYearSummaries,
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
    // Optimistic write-through so an edit never appears to "jump back" before
    // the refetch; rolls back if the PATCH fails.
    return useOptimisticEntryPatch<FuldaEntry, FuldaEntry, FuldaUpdatePayload>({
        listKey: queryKeys.fuldaEntries,
        settledKeys: [queryKeys.fuldaEntries, queryKeys.fuldaYearSummaries, queryKeys.progress],
        mutationFn: ({ entryId, data }) =>
            api<FuldaEntry>(`/api/v1/import/fulda/entries/${entryId}`, {
                method: "PATCH",
                json: data,
            }),
    });
}

export function useDeleteFuldaEntry() {
    return useInvalidatingMutation(
        (entryId: number) =>
            api<void>(`/api/v1/import/fulda/entries/${entryId}`, { method: "DELETE" }),
        [
            queryKeys.fuldaEntries,
            queryKeys.fuldaYearSummaries,
            queryKeys.progress,
        ],
    );
}

export function useConfirmFuldaYear() {
    return useInvalidatingMutation(
        (year: number) =>
            api<{ confirmed: number }>(`/api/v1/import/fulda/years/${year}/confirm`, {
                method: "POST",
            }),
        [
            queryKeys.fuldaEntries,
            queryKeys.fuldaYearSummaries,
            queryKeys.progress,
        ],
    );
}

export function useDeleteFuldaYear() {
    return useInvalidatingMutation(
        (year: number) =>
            api<void>(`/api/v1/import/fulda/years/${year}`, { method: "DELETE" }),
        [
            queryKeys.fuldaEntries,
            queryKeys.fuldaYears,
            queryKeys.fuldaYearSummaries,
            queryKeys.progress,
        ],
    );
}

export function useVibAiAvailable() {
    return useQuery({
        queryKey: queryKeys.vibAiAvailable,
        queryFn: () => api<{ available: boolean; model: string | null }>("/api/v1/import/vib/ai-available"),
    });
}

export function useVibOcrAvailable() {
    return useQuery({
        queryKey: queryKeys.vibOcrAvailable,
        queryFn: () => api<{ available: boolean; model: string | null }>("/api/v1/import/vib/ocr-available"),
    });
}

export function useSaveVibDraft() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ taskId, data }: { taskId: string; data: VibParseTaskResult }) =>
            api<void>(`/api/v1/import/vib/draft/${taskId}`, {
                method: "PATCH",
                json: data,
            }),
        onSuccess: (_, { taskId, data }) => {
            queryClient.setQueryData(queryKeys.vibParseResult(taskId), data);
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
        queryKey: queryKeys.vibDrafts,
        queryFn: () => api<VibDraftSchema[]>("/api/v1/import/vib/drafts"),
    });
}

export function useDeleteVibDraft() {
    return useInvalidatingMutation(
        (taskId: string) =>
            api<void>(`/api/v1/import/vib/drafts/${taskId}`, { method: "DELETE" }),
        [queryKeys.vibDrafts],
    );
}

// ---------------------------------------------------------------------------
// Admin: Offene Zuordnungen (unassigned FinVe / VIB entries)
// ---------------------------------------------------------------------------

export type UnassignedFinve = components["schemas"]["UnassignedFinveSchema"];

export type UnassignedVibEntry = components["schemas"]["UnassignedVibEntrySchema"];

export function useUnassignedFinves(enabled = true) {
    return useQuery({
        queryKey: queryKeys.adminUnassignedFinves,
        queryFn: () => api<UnassignedFinve[]>("/api/v1/admin/unassigned-finves"),
        enabled,
    });
}

export function useUnassignedVibEntries(enabled = true) {
    return useQuery({
        queryKey: queryKeys.adminUnassignedVibEntries,
        queryFn: () => api<UnassignedVibEntry[]>("/api/v1/admin/unassigned-vib-entries"),
        enabled,
    });
}

export function useAssignFinve() {
    return useInvalidatingMutation(
        ({ finveId, projectIds }: { finveId: number; projectIds: number[] }) =>
            api<void>(`/api/v1/admin/unassigned-finves/${finveId}/assign`, {
                method: "PATCH",
                json: { project_ids: projectIds },
            }),
        [queryKeys.adminUnassignedFinves],
    );
}

export function useAssignVibEntry() {
    return useInvalidatingMutation(
        ({ entryId, projectIds }: { entryId: number; projectIds: number[] }) =>
            api<void>(`/api/v1/admin/unassigned-vib-entries/${entryId}/assign`, {
                method: "PATCH",
                json: { project_ids: projectIds },
            }),
        [queryKeys.adminUnassignedVibEntries],
    );
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
        queryKey: queryKeys.operationalPoints(q),
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
                json: { profile: "rail_default", options: {}, ...payload },
            }),
    });
}

export function useConfirmRoute(projectId: number) {
    return useInvalidatingMutation(
        (feature: RoutePreviewFeature) =>
            api<ProjectRoute>(`/api/v1/projects/${projectId}/routes`, {
                method: "POST",
                json: { feature },
            }),
        [queryKeys.projectRoutes(projectId)],
    );
}

export function useUpdateProjectGeometry(projectId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (geojson_representation: string | null) =>
            updateProject(projectId, { geojson_representation }),
        onSuccess: (updatedProject) => {
            queryClient.setQueryData(queryKeys.project(projectId), updatedProject);
            queryClient.invalidateQueries({ queryKey: queryKeys.projects });
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
    filters ? ([...queryKeys.todos, filters] as const) : queryKeys.todos;

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
        queryKey: queryKeys.userOptions,
        enabled,
        queryFn: () => api<UserOption[]>(`/api/v1/users/options`),
    });
}

export function useCreateTodo() {
    return useInvalidatingMutation(
        (payload: TodoCreate) =>
            api<Todo>(`/api/v1/todos/`, {
                method: "POST",
                json: payload,
            }),
        [queryKeys.todos],
    );
}

export function useUpdateTodo() {
    return useInvalidatingMutation(
        ({ id, payload }: { id: number; payload: TodoUpdate }) =>
            api<Todo>(`/api/v1/todos/${id}`, {
                method: "PATCH",
                json: payload,
            }),
        [queryKeys.todos],
    );
}

export function useDeleteTodo() {
    return useInvalidatingMutation(
        (id: number) =>
            api<void>(`/api/v1/todos/${id}`, { method: "DELETE" }),
        [queryKeys.todos],
    );
}

// --- Guides ("Anleitungen") section overrides --------------------------------

export type GuideOverride = components["schemas"]["GuideOverrideSchema"];

export function useGuideOverrides(guideSlug: string) {
    return useQuery({
        queryKey: queryKeys.guideOverrides(guideSlug),
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
                json: { body_markdown: bodyMarkdown },
            }),
        onSuccess: (_data, { guideSlug }) => {
            queryClient.invalidateQueries({ queryKey: queryKeys.guideOverrides(guideSlug) });
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
            queryClient.invalidateQueries({ queryKey: queryKeys.guideOverrides(guideSlug) });
        },
    });
}
