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
    project_group_ids?: number[];
};

// ---------------------------------------------------------------------------
// Project texts
// ---------------------------------------------------------------------------

export type ProjectTextType = { id: number; name: string };

export type TextAttachment = {
    id: number;
    text_id: number;
    filename: string;
    mime_type: string;
    file_size: number;
    uploaded_at: string;
    uploaded_by_user_id: number | null;
};

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
    attachments: TextAttachment[];
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

export function useUpdateProjectGroup() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ groupId, isVisible, isDefaultSelected }: { groupId: number; isVisible?: boolean; isDefaultSelected?: boolean }) =>
            api<ProjectGroup>(`/api/v1/project_groups/${groupId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ...(isVisible !== undefined && { is_visible: isVisible }),
                    ...(isDefaultSelected !== undefined && { is_default_selected: isDefaultSelected }),
                }),
            }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["projectGroups"] }),
    });
}

export type MapGroupMode = "preconfigured" | "all";
export type AppSettings = { map_group_mode: MapGroupMode };

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

// ---------------------------------------------------------------------------
// FinVe + Budget (Projektdetail)
// ---------------------------------------------------------------------------

export type TitelEntry = {
    titel_key: string;
    kapitel: string;
    titel_nr: string;
    label: string;
    is_nachrichtlich: boolean;
    cost_estimate_last_year: number | null;
    cost_estimate_aktuell: number | null;
    verausgabt_bis: number | null;
    bewilligt: number | null;
    ausgabereste_transferred: number | null;
    veranschlagt: number | null;
    vorhalten_future: number | null;
};

export type BudgetSummary = {
    budget_year: number;
    lfd_nr: string | null;
    bedarfsplan_number: string | null;
    cost_estimate_original: number | null;
    cost_estimate_last_year: number | null;
    cost_estimate_actual: number | null;
    delta_previous_year: number | null;
    delta_previous_year_relativ: number | null;
    spent_two_years_previous: number | null;
    allowed_previous_year: number | null;
    spending_residues: number | null;
    year_planned: number | null;
    next_years: number | null;
    titel_entries: TitelEntry[];
};

export type FinveWithBudgets = {
    id: number;
    name: string | null;
    starting_year: number | null;
    cost_estimate_original: number | null;
    is_sammel_finve: boolean;
    budgets: BudgetSummary[];
};

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

export type ProjectRef = { id: number; name: string };

export type FinveListItem = {
    id: number;
    name: string | null;
    starting_year: number | null;
    cost_estimate_original: number | null;
    is_sammel_finve: boolean;
    temporary_finve_number: boolean;
    project_count: number;
    project_names: string[];
    projects: ProjectRef[];
    budgets: BudgetSummary[];
};

export function useFinves() {
    return useQuery({
        queryKey: ["finves"],
        queryFn: () => api<FinveListItem[]>("/api/v1/finves/"),
    });
}

// ---------------------------------------------------------------------------
// Haushalt-Import
// ---------------------------------------------------------------------------

export type TitelEntryProposed = {
    titel_key: string;
    kapitel: string;
    titel_nr: string;
    label: string;
    is_nachrichtlich: boolean;
    cost_estimate_last_year: number | null;
    cost_estimate_aktuell: number | null;
    verausgabt_bis: number | null;
    bewilligt: number | null;
    ausgabereste_transferred: number | null;
    veranschlagt: number | null;
    vorhalten_future: number | null;
};

export type ProposedFinve = {
    id: number;
    name: string;
    starting_year: number | null;
    cost_estimate_original: number | null;
    is_sammel_finve: boolean;
};

export type ProposedBudget = {
    budget_year: number;
    lfd_nr: string | null;
    fin_ve: number;
    bedarfsplan_number: string | null;
    cost_estimate_original: number | null;
    cost_estimate_last_year: number | null;
    cost_estimate_actual: number | null;
    delta_previous_year: number | null;
    delta_previous_year_relativ: number | null;
    delta_previous_year_reasons: string | null;
    spent_two_years_previous: number | null;
    allowed_previous_year: number | null;
    spending_residues: number | null;
    year_planned: number | null;
    next_years: number | null;
    sammel_finve: boolean;
};

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

export type ParseResultPublic = {
    id: number;
    haushalt_year: number;
    pdf_filename: string;
    parsed_at: string;
    username_snapshot: string | null;
    status: "PENDING" | "SUCCESS" | "FAILURE";
    error_message: string | null;
    confirmed_at: string | null;
    confirmed_by_snapshot: string | null;
    result_json: HaushaltsParseTaskResult | null;
};

export type UnmatchedBudgetRow = {
    id: number;
    haushalt_year: number;
    raw_finve_number: string;
    raw_name: string;
    raw_data: Record<string, unknown> | null;
    resolved: boolean;
    resolved_finve_id: number | null;
    resolved_at: string | null;
    resolved_by_snapshot: string | null;
};

export type HaushaltsConfirmRowInput = Omit<HaushaltsParseRow, "status"> & {
    status: string;
};

export type HaushaltsConfirmRequest = {
    parse_result_id: number;
    rows: HaushaltsConfirmRowInput[];
    unmatched_action: "save" | "discard";
};

export type HaushaltsConfirmResponse = {
    finves_created: number;
    finves_updated: number;
    budgets_created: number;
    budgets_updated: number;
    unmatched_saved: number;
};

export type TaskLaunchResponse = { task_id: string };
export type TaskProgressMeta = {
    // VIB parse steps
    step?: string;
    step_label?: string;
    // legacy page-based progress (haushalt import)
    current_page?: number;
    total_pages?: number;
    rows_found?: number;
};

export type TaskStatusResponse = {
    task_id: string;
    status: "PENDING" | "STARTED" | "PROGRESS" | "SUCCESS" | "FAILURE";
    result: unknown;
    error: string | null;
};

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

export type VibPfaEntryProposed = {
    abschnitt_label: string | null;
    nr_pfa: string | null;
    oertlichkeit: string | null;
    entwurfsplanung: string | null;
    abschluss_finve: string | null;
    datum_pfb: string | null;
    baubeginn: string | null;
    inbetriebnahme: string | null;
};

export type VibEntryProposed = {
    vib_section: string | null;
    vib_lfd_nr: string | null;
    vib_name_raw: string;
    category: "laufend" | "neu" | "potentiell" | "abgeschlossen";
    verkehrliche_zielsetzung: string | null;
    durchgefuehrte_massnahmen: string | null;
    noch_umzusetzende_massnahmen: string | null;
    bauaktivitaeten: string | null;
    teilinbetriebnahmen: string | null;
    raw_text: string | null;
    strecklaenge_km: number | null;
    gesamtkosten_mio_eur: number | null;
    entwurfsgeschwindigkeit: string | null;
    planungsstand: string | null;
    pfa_entries: VibPfaEntryProposed[];
    pfa_raw_markdown: string | null;
    sonstiges: string | null;
    project_ids: number[];
    suggested_project_ids: number[];
    status_planung: boolean;
    status_bau: boolean;
    status_abgeschlossen: boolean;
    ai_extracted: boolean;
    ai_extraction_failed: boolean;
    ai_extraction_error: string | null;
};

export type VibParseTaskResult = {
    year: number;
    drucksache_nr: string | null;
    report_date: string | null;
    entries: VibEntryProposed[];
};

export type VibConfirmEntryInput = Omit<VibEntryProposed, "suggested_project_ids">;

export type VibConfirmRequest = {
    task_id: string;
    year: number;
    drucksache_nr: string | null;
    report_date: string | null;
    entries: VibConfirmEntryInput[];
};

export type VibConfirmResponse = {
    report_id: number;
    entries_created: number;
    pfa_entries_created: number;
};

export type VibReportSchema = {
    id: number;
    year: number;
    drucksache_nr: string | null;
    report_date: string | null;
    imported_at: string;
    entry_count: number;
};

export type VibPfaEntrySchema = {
    id: number;
    abschnitt_label: string | null;
    nr_pfa: string | null;
    oertlichkeit: string | null;
    entwurfsplanung: string | null;
    abschluss_finve: string | null;
    datum_pfb: string | null;
    baubeginn: string | null;
    inbetriebnahme: string | null;
};

export type VibEntryForProject = {
    id: number;
    year: number;
    drucksache_nr: string | null;
    vib_section: string | null;
    vib_name_raw: string;
    category: "laufend" | "neu" | "potentiell" | "abgeschlossen";
    bauaktivitaeten: string | null;
    teilinbetriebnahmen: string | null;
    verkehrliche_zielsetzung: string | null;
    durchgefuehrte_massnahmen: string | null;
    noch_umzusetzende_massnahmen: string | null;
    raw_text: string | null;
    strecklaenge_km: number | null;
    gesamtkosten_mio_eur: number | null;
    entwurfsgeschwindigkeit: string | null;
    planungsstand: string | null;
    status_planung: boolean;
    status_bau: boolean;
    status_abgeschlossen: boolean;
    ai_extracted: boolean;
    pfa_entries: VibPfaEntrySchema[];
};

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

export function useStartVibAiExtraction() {
    return useMutation({
        mutationFn: (parseTaskId: string) =>
            api<TaskLaunchResponse>(`/api/v1/import/vib/extract-ai/${parseTaskId}`, {
                method: "POST",
            }),
    });
}

export function useSaveVibDraft() {
    return useMutation({
        mutationFn: ({ taskId, data }: { taskId: string; data: VibParseTaskResult }) =>
            api<void>(`/api/v1/import/vib/draft/${taskId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            }),
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

export type VibDraftSchema = {
    task_id: string;
    year: number;
    created_at: string;
};

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

export type UnassignedFinve = {
    id: number;
    name: string | null;
    is_sammel_finve: boolean;
    starting_year: number | null;
};

export type UnassignedVibEntry = {
    id: number;
    vib_name_raw: string;
    vib_section: string | null;
    category: string;
    report_year: number;
};

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
