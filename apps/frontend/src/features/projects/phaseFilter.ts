/**
 * Pure helpers behind the "Phase" filter on the map/list page (`/`), kept out
 * of the components so parsing and matching can be unit-tested.
 *
 * The selection lives in the URL as `?phase=BAU,VORPLANUNG` (MainPhase values,
 * plus `UNBEKANNT` for projects without a known headline phase). An empty or
 * missing param means "no phase filter".
 *
 * Paused / aborted projects (lifecycle ≠ AKTIV) are filtered by their headline
 * phase like any other project — the lifecycle is an overlay and does not
 * change the phase value (same rule as the backend derivation).
 */

import { MAIN_PHASES, MAIN_PHASE_LABEL, UNKNOWN_LABEL, type MainPhase } from "./components/progress/phaseMeta";

/** URL value of the "no known phase" option. */
export const PHASE_UNKNOWN = "UNBEKANNT";

export type PhaseFilterValue = MainPhase | typeof PHASE_UNKNOWN;

/** URL search param holding the selection. */
export const PHASE_PARAM = "phase";

/** Canonical option order: the phases in planning order, "Unbekannt" last. */
export const PHASE_FILTER_VALUES: readonly PhaseFilterValue[] = [...MAIN_PHASES, PHASE_UNKNOWN];

const VALID_VALUES = new Set<string>(PHASE_FILTER_VALUES);

export function isPhaseFilterValue(value: string): value is PhaseFilterValue {
    return VALID_VALUES.has(value);
}

/** Select options ({ value, label }) in canonical order, labels from phaseMeta. */
export function phaseFilterOptions(): { value: PhaseFilterValue; label: string }[] {
    return PHASE_FILTER_VALUES.map((value) => ({
        value,
        label: value === PHASE_UNKNOWN ? UNKNOWN_LABEL : MAIN_PHASE_LABEL[value],
    }));
}

/**
 * Parse `?phase=…` into a deduplicated selection in canonical order.
 * Unknown tokens are dropped, so a stale or hand-edited link never breaks the page.
 */
export function parsePhaseParam(raw: string | null | undefined): PhaseFilterValue[] {
    if (!raw) return [];
    const tokens = new Set(
        raw
            .split(",")
            .map((token) => token.trim().toUpperCase())
            .filter(Boolean),
    );
    return PHASE_FILTER_VALUES.filter((value) => tokens.has(value));
}

/** Serialise a selection for the URL; `null` means "remove the param". */
export function serializePhaseParam(values: readonly string[]): string | null {
    const normalized = parsePhaseParam(values.join(","));
    return normalized.length > 0 ? normalized.join(",") : null;
}

export type PhaseFilterable = { headline_phase?: string | null };

/** The filter bucket a project falls into: its headline phase, or `UNBEKANNT`. */
export function phaseFilterKey(project: PhaseFilterable): PhaseFilterValue {
    const phase = project.headline_phase;
    return phase && isPhaseFilterValue(phase) && phase !== PHASE_UNKNOWN ? phase : PHASE_UNKNOWN;
}

/**
 * Projects whose phase bucket is in `selected`. An empty selection returns the
 * input unchanged (same array), so memoised consumers do not re-render.
 */
export function filterProjectsByPhase<T extends PhaseFilterable>(
    projects: T[],
    selected: readonly PhaseFilterValue[],
): T[] {
    if (selected.length === 0) return projects;
    const wanted = new Set<PhaseFilterValue>(selected);
    return projects.filter((project) => wanted.has(phaseFilterKey(project)));
}
