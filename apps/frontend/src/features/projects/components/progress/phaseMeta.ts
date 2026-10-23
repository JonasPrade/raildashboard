// German UI labels and ordering for the planning-state enums.
// Mirrors backend models.projects.progress_enums.

import { PHASE_COLOR } from "../../../../shared/theme/semanticColors";

export type MainPhase =
    | "NICHT_GESTARTET"
    | "VORPLANUNG"
    | "GENEHMIGUNGSPLANUNG"
    | "BAU"
    | "IN_BETRIEB";

export type ParallelState = "OFFEN" | "LAEUFT" | "ABGESCHLOSSEN";
export type LifecycleStatus = "AKTIV" | "PAUSIERT" | "ABGEBROCHEN" | "ERSETZT";
export type ObservationTrack = "MAIN" | "PF" | "PARL";
export type SourceType =
    | "VIB"
    | "FINVE"
    | "FULDA_RUNDE"
    | "BAUPORTAL"
    | "MEDIEN"
    | "INFRAPLAN"
    | "GVFG"
    | "MANUELL";

export const MAIN_PHASES: MainPhase[] = [
    "NICHT_GESTARTET",
    "VORPLANUNG",
    "GENEHMIGUNGSPLANUNG",
    "BAU",
    "IN_BETRIEB",
];

// Planning phases a project group may skip (#164), e.g. corridor renewals
// without Planfeststellung. Mirrors SkippablePhaseLiteral in the backend.
export const SKIPPABLE_PHASES: MainPhase[] = ["VORPLANUNG", "GENEHMIGUNGSPLANUNG"];

/** Main phases minus the ones the progress view hides for this project. */
export function visiblePhases(hidden?: readonly string[] | null): MainPhase[] {
    if (!hidden || hidden.length === 0) return MAIN_PHASES;
    return MAIN_PHASES.filter((p) => !hidden.includes(p));
}

// Shown when a project carries no phase information at all (is_known === false).
export const UNKNOWN_LABEL = "Unbekannt";

export const MAIN_PHASE_LABEL: Record<MainPhase, string> = {
    NICHT_GESTARTET: "Nicht gestartet",
    VORPLANUNG: "Vorplanung",
    GENEHMIGUNGSPLANUNG: "Genehmigungsplanung",
    BAU: "Bau",
    IN_BETRIEB: "In Betrieb",
};

// Phase colours live in shared/theme/semanticColors.ts (Q11/W6): the teal ramp
// for the planning phases, --idt-success for "In Betrieb". CSS values, not
// Mantine colour names — use them as `background`/`color`, not as `color=` props.
export const MAIN_PHASE_COLOR: Record<MainPhase, string> = PHASE_COLOR;

/** Colour for "Unbekannt" (no phase information). */
export const UNKNOWN_PHASE_COLOR = PHASE_COLOR.UNBEKANNT;

/** Select options for the main phases: { value, label } pairs. */
export const mainPhaseOptions = () =>
    MAIN_PHASES.map((p) => ({ value: p, label: MAIN_PHASE_LABEL[p] }));

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
    ERSETZT: "Ersetzt",
};

export const LIFECYCLE_STATUSES: LifecycleStatus[] = ["AKTIV", "PAUSIERT", "ABGEBROCHEN", "ERSETZT"];

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
    INFRAPLAN: "Infraplan",
    GVFG: "GVFG",
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

/** Age of an observation date as short German text, e.g. "2,8 J." or "4 Mon.". */
export function formatAge(isoDate: string | null | undefined, today: Date = new Date()): string {
    if (!isoDate) return "–";
    const d = new Date(isoDate);
    if (Number.isNaN(d.getTime())) return "–";
    const days = (today.getTime() - d.getTime()) / 86_400_000;
    if (days < 0) return "künftig";
    if (days < 365) return `${Math.floor(days / 30.44)} Mon.`;
    return `${(days / 365.25).toLocaleString("de-DE", { maximumFractionDigits: 1 })} J.`;
}

/** Format an ISO datetime as a short German date + time, e.g. "21.06.2026 14:08". */
export function formatTimestamp(iso: string | null | undefined): string {
    if (!iso) return "–";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "–";
    return d.toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Berlin" });
}

/** Bucket subprojects by their effective phase; ``is_known === false`` →
 * separate "unknown" bucket (not counted as NICHT_GESTARTET). Replaced
 * subprojects (ERSETZT) count nowhere — their successor carries the scheme
 * (feature-project-replacement.md, W3). */
export function groupChildrenByPhase<
    T extends { effective_phase: string; is_known?: boolean; lifecycle_status?: string },
>(children: T[]): { byPhase: Partial<Record<MainPhase, T[]>>; unknown: T[] } {
    const byPhase: Partial<Record<MainPhase, T[]>> = {};
    const unknown: T[] = [];
    for (const c of children) {
        if (c.lifecycle_status === "ERSETZT") continue;
        if (c.is_known === false) {
            unknown.push(c);
            continue;
        }
        const phase = c.effective_phase as MainPhase;
        (byPhase[phase] ??= []).push(c);
    }
    return { byPhase, unknown };
}
