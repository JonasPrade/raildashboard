/**
 * Helpers for the scheduled routine jobs (docs/features/feature-routine-abrufe.md):
 * the block „Zeitgesteuerte Abrufe“ in /admin/system, the badge in the admin
 * overview and the „Zeitplan“ marker on the run lines of /admin/abgeordnete.
 */

import type { RoutineJobRun } from "../../shared/api/queries";

type Trigger = {
    triggered_by_user_id?: number | null;
    triggered_by_username?: string | null;
};

/** Who started a run: „Zeitplan“ for the scheduler, else the user. */
export function triggerLabel(run: Trigger): string {
    if (run.triggered_by_user_id == null) return "Zeitplan";
    return run.triggered_by_username ? `von ${run.triggered_by_username}` : "von Hand";
}

export function formatBerlin(value: string | null | undefined): string {
    if (!value) return "—";
    return new Date(value).toLocaleString("de-DE", {
        timeZone: "Europe/Berlin",
        dateStyle: "medium",
        timeStyle: "short",
    });
}

/** „12 s“, „3 min 5 s“, „1 h 2 min“. */
export function formatDuration(seconds: number | null | undefined): string {
    if (seconds == null) return "—";
    const total = Math.max(0, Math.round(seconds));
    if (total < 60) return `${total} s`;
    const minutes = Math.floor(total / 60);
    if (minutes < 60) return `${minutes} min ${total % 60} s`;
    return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

export const RUN_STATUS_LABEL: Record<string, string> = {
    success: "erfolgreich",
    error: "Fehler",
    running: "läuft",
    skipped: "übersprungen",
};

export const RUN_STATUS_TONE: Record<string, "done" | "danger" | "active" | "neutral"> = {
    success: "done",
    error: "danger",
    running: "active",
    skipped: "neutral",
};

export function runStatusLabel(run: Pick<RoutineJobRun, "status">): string {
    return RUN_STATUS_LABEL[run.status] ?? run.status;
}
