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
    MAIN: "Hauptspur",
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
