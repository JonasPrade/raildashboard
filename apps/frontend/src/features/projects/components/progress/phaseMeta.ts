// German UI labels and ordering for the planning-state enums.
// Mirrors backend models.projects.progress_enums.

export type MainPhase =
    | "NICHT_GESTARTET"
    | "VORPLANUNG"
    | "GENEHMIGUNGSPLANUNG"
    | "BAU"
    | "IN_BETRIEB";

export type ParallelState = "OFFEN" | "LAEUFT" | "ABGESCHLOSSEN";
export type LifecycleStatus = "AKTIV" | "PAUSIERT" | "ABGEBROCHEN";
export type ObservationTrack = "MAIN" | "PF" | "PARL";
export type SourceType =
    | "VIB"
    | "FINVE"
    | "FULDA_RUNDE"
    | "BAUPORTAL"
    | "MEDIEN"
    | "MANUELL";

export const MAIN_PHASES: MainPhase[] = [
    "NICHT_GESTARTET",
    "VORPLANUNG",
    "GENEHMIGUNGSPLANUNG",
    "BAU",
    "IN_BETRIEB",
];

// Shown when a project carries no phase information at all (is_known === false).
export const UNKNOWN_LABEL = "Unbekannt";

export const MAIN_PHASE_LABEL: Record<MainPhase, string> = {
    NICHT_GESTARTET: "Nicht gestartet",
    VORPLANUNG: "Vorplanung",
    GENEHMIGUNGSPLANUNG: "Genehmigungsplanung",
    BAU: "Bau",
    IN_BETRIEB: "In Betrieb",
};

export const MAIN_PHASE_SHORT: Record<MainPhase, string> = {
    NICHT_GESTARTET: "Start",
    VORPLANUNG: "LP 1–2",
    GENEHMIGUNGSPLANUNG: "LP 3–4",
    BAU: "Bau",
    IN_BETRIEB: "Betrieb",
};

export const PARALLEL_STATES: ParallelState[] = ["OFFEN", "LAEUFT", "ABGESCHLOSSEN"];

export const PARALLEL_STATE_LABEL: Record<ParallelState, string> = {
    OFFEN: "offen",
    LAEUFT: "läuft",
    ABGESCHLOSSEN: "abgeschlossen",
};

export const LIFECYCLE_LABEL: Record<LifecycleStatus, string> = {
    AKTIV: "Aktiv",
    PAUSIERT: "Pausiert",
    ABGEBROCHEN: "Abgebrochen",
};

export const TRACK_LABEL: Record<ObservationTrack, string> = {
    MAIN: "Planungsphasen",
    PF: "Planfeststellung",
    PARL: "Parlamentarische Befassung",
};

export const SOURCE_LABEL: Record<SourceType, string> = {
    VIB: "VIB",
    FINVE: "FinVe",
    FULDA_RUNDE: "Fulda-Runde",
    BAUPORTAL: "Bauportal",
    MEDIEN: "Medien",
    MANUELL: "Manuell",
};

// Milestone-style labels for the forecast (the *event* that starts the phase).
export const MILESTONE_LABEL: Record<MainPhase, string> = {
    NICHT_GESTARTET: "Projektstart",
    VORPLANUNG: "Vorplanung",
    GENEHMIGUNGSPLANUNG: "Genehmigung / PFB",
    BAU: "Baubeginn",
    IN_BETRIEB: "Inbetriebnahme",
};

export function mainPhaseIndex(phase: MainPhase): number {
    return MAIN_PHASES.indexOf(phase);
}

/** Human-readable label for an asserted_state, depending on its track. */
export function stateLabel(track: ObservationTrack, state: string): string {
    if (track === "MAIN") return MAIN_PHASE_LABEL[state as MainPhase] ?? state;
    return PARALLEL_STATE_LABEL[state as ParallelState] ?? state;
}

/** Format an ISO datetime as a short German date + time, e.g. "21.06.2026 14:08". */
export function formatTimestamp(iso: string | null | undefined): string {
    if (!iso) return "–";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "–";
    return d.toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" });
}

/** Bucket subprojects by their effective phase; ``is_known === false`` →
 * separate "unknown" bucket (not counted as NICHT_GESTARTET). */
export function groupChildrenByPhase<T extends { effective_phase: string; is_known?: boolean }>(
    children: T[],
): { byPhase: Partial<Record<MainPhase, T[]>>; unknown: T[] } {
    const byPhase: Partial<Record<MainPhase, T[]>> = {};
    const unknown: T[] = [];
    for (const c of children) {
        if (c.is_known === false) {
            unknown.push(c);
            continue;
        }
        const phase = c.effective_phase as MainPhase;
        (byPhase[phase] ??= []).push(c);
    }
    return { byPhase, unknown };
}
