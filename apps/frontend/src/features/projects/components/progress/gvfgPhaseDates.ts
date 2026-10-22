// Completion years of past phases as the GVFG-Bundesprogramm states them, shown
// in the planning-state stepper's tooltips ("abgeschlossen 2009").
// Same reading as the backend's gvfg_entry_to_specs: a Baubeginn up to this
// year ends the planning, an "Inbetriebnahme tats." before this year ends Bau
// (later years in that column are expectations, not facts).

import type { GvfgProjectEntry } from "../../../../shared/api/queries";
import { editionLabel } from "../../../gvfg/gvfgFormat";
import { type MainPhase, visiblePhases } from "./phaseMeta";

export type PhaseCompletion = { year: number; source: string };

/** Newest edition of each Vorhaben assigned to the project itself. */
function newestOwnEntries(entries: GvfgProjectEntry[], projectId: number): GvfgProjectEntry[] {
    const byKey = new Map<string, GvfgProjectEntry>();
    for (const e of entries) {
        if (!e.projects.some((p) => p.id === projectId)) continue;
        const prev = byKey.get(e.key);
        if (!prev || e.program.year_from > prev.program.year_from) byKey.set(e.key, e);
    }
    return [...byKey.values()];
}

/** Keeps the latest year: with several Vorhaben a phase ends with the last one. */
function keepLatest(
    out: Partial<Record<MainPhase, PhaseCompletion>>,
    phase: MainPhase,
    completion: PhaseCompletion,
) {
    const prev = out[phase];
    if (!prev || completion.year > prev.year) out[phase] = completion;
}

export function gvfgPhaseCompletions(
    entries: GvfgProjectEntry[] | undefined,
    projectId: number,
    hiddenPhases: readonly string[] | null | undefined,
    currentYear: number = new Date().getFullYear(),
): Partial<Record<MainPhase, PhaseCompletion>> {
    const out: Partial<Record<MainPhase, PhaseCompletion>> = {};
    if (!entries) return out;
    // The Baubeginn closes the last planning phase the stepper shows.
    const phases = visiblePhases(hiddenPhases);
    const beforeBau = phases[phases.indexOf("BAU") - 1];
    for (const e of newestOwnEntries(entries, projectId)) {
        const label = `GVFG ${editionLabel(e.program)}`;
        if (beforeBau && e.construction_start != null && e.construction_start <= currentYear) {
            keepLatest(out, beforeBau, { year: e.construction_start, source: `${label}, Baubeginn` });
        }
        if (e.commissioning_actual != null && e.commissioning_actual < currentYear) {
            keepLatest(out, "BAU", {
                year: e.commissioning_actual,
                source: `${label}, Inbetriebnahme tats.`,
            });
        }
    }
    return out;
}
