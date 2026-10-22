// When past phases ended per the sources, shown in the planning-state stepper's
// tooltips ("abgeschlossen 2009"). Display only — the derivation lives in the
// backend (services/progress_materialization.py); these helpers read the same
// fields the same way.

import type { GvfgProjectEntry, VibEntryForProject } from "../../../../shared/api/queries";
import { editionLabel } from "../../../gvfg/gvfgFormat";
import { type MainPhase, visiblePhases } from "./phaseMeta";

/** `label` is the date as the source prints it ("2009", "12/2024"). */
export type PhaseCompletion = { label: string; source: string };
export type PhaseCompletions = Partial<Record<MainPhase, PhaseCompletion[]>>;

/** The last planning phase the stepper shows — a Baubeginn or PFB closes it. */
function lastPlanningPhase(hiddenPhases: readonly string[] | null | undefined): MainPhase | undefined {
    const phases = visiblePhases(hiddenPhases);
    return phases[phases.indexOf("BAU") - 1];
}

function add(out: PhaseCompletions, phase: MainPhase, completion: PhaseCompletion) {
    out[phase] = [...(out[phase] ?? []), completion];
}

// ---------------------------------------------------------------------------
// GVFG-Bundesprogramm (gvfg_entry_to_specs): a Baubeginn up to this year ends
// the planning, an "Inbetriebnahme tats." before this year ends Bau (later
// years in that column are expectations, not facts).
// ---------------------------------------------------------------------------

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

export function gvfgPhaseCompletions(
    entries: GvfgProjectEntry[] | undefined,
    projectId: number,
    hiddenPhases: readonly string[] | null | undefined,
    currentYear: number = new Date().getFullYear(),
): PhaseCompletions {
    const out: PhaseCompletions = {};
    if (!entries) return out;
    const beforeBau = lastPlanningPhase(hiddenPhases);
    // With several Vorhaben a phase ends with the last one.
    let planning: GvfgProjectEntry | null = null;
    let bau: GvfgProjectEntry | null = null;
    for (const e of newestOwnEntries(entries, projectId)) {
        const start = e.construction_start;
        if (start != null && start <= currentYear && start > (planning?.construction_start ?? -Infinity)) {
            planning = e;
        }
        const ibn = e.commissioning_actual;
        if (ibn != null && ibn < currentYear && ibn > (bau?.commissioning_actual ?? -Infinity)) bau = e;
    }
    if (beforeBau && planning) {
        add(out, beforeBau, {
            label: String(planning.construction_start),
            source: `GVFG ${editionLabel(planning.program)}, Baubeginn`,
        });
    }
    if (bau) {
        add(out, "BAU", {
            label: String(bau.commissioning_actual),
            source: `GVFG ${editionLabel(bau.program)}, Inbetriebnahme tats.`,
        });
    }
    return out;
}

// ---------------------------------------------------------------------------
// VIB: the PFA table of the newest report. A phase counts as ended only when
// every section has a past date — the PFB (else the Baubeginn) ends the
// planning, the Inbetriebnahme ends Bau; the latest section's date is shown.
// ---------------------------------------------------------------------------

type Pfa = VibEntryForProject["pfa_entries"][number];

// Forecast wording ("voraussichtlich Ende 2027") is no completion.
const FORECAST = /vorauss|vsl\.|geplant|prognos/i;

const MONTHS: Record<string, number> = {
    jan: 1, feb: 2, mär: 3, mae: 3, mrz: 3, apr: 4, mai: 5, jun: 6,
    jul: 7, aug: 8, sep: 9, okt: 10, nov: 11, dez: 12,
};
const KEYWORD_MONTH: Record<string, number> = {
    anfang: 3, frühjahr: 5, fruehjahr: 5, mitte: 8, sommer: 9, herbst: 11, ende: 12, winter: 12,
};

/** Last day of the period a free-text VIB date names ("12/2024" → 31.12.2024),
 * so a period counts as past only once it is over. A reduced reading of the
 * backend's parse_flexible_date; null when nothing date-like is present. */
export function vibDateEnd(text: string | null | undefined): Date | null {
    if (!text) return null;
    const t = text.toLowerCase();
    const endOfMonth = (y: number, m: number) => (m >= 1 && m <= 12 ? new Date(y, m, 0) : null);
    let m = t.match(/\b(\d{4})-(\d{1,2})-(\d{1,2})\b/);
    if (m) return new Date(+m[1], +m[2] - 1, +m[3]);
    m = t.match(/\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b/);
    if (m) return new Date(+m[3], +m[2] - 1, +m[1]);
    m = t.match(/\b([1-4])\s*\.?\s*quartal\b.*?(\d{4})/) ?? t.match(/\bq\s*([1-4])\b.*?(\d{4})/);
    if (m) return endOfMonth(+m[2], +m[1] * 3);
    m = t.match(/\b(\d{1,2})[/.](\d{4})\b/);
    if (m) return endOfMonth(+m[2], +m[1]);
    const year = t.match(/\b(19|20)\d{2}\b/);
    if (!year) return null;
    const y = +year[0];
    for (const [name, month] of Object.entries(MONTHS)) {
        if (new RegExp(`\\b${name}`).test(t)) return endOfMonth(y, month);
    }
    for (const [word, month] of Object.entries(KEYWORD_MONTH)) {
        if (t.includes(word)) return endOfMonth(y, month);
    }
    return new Date(y, 11, 31);
}

/** The latest past date over all sections, or null when one section lacks it. */
function latestPast(
    pfas: Pfa[],
    pick: (p: Pfa) => string | null | undefined,
    today: Date,
): string | null {
    let latest: { text: string; end: Date } | null = null;
    for (const pfa of pfas) {
        const text = pick(pfa)?.trim();
        const end = text && !FORECAST.test(text) ? vibDateEnd(text) : null;
        if (!text || !end || end >= today) return null;
        if (!latest || end > latest.end) latest = { text, end };
    }
    return latest?.text ?? null;
}

export function vibPhaseCompletions(
    entries: VibEntryForProject[] | undefined,
    projectId: number,
    isSuperior: boolean,
    hiddenPhases: readonly string[] | null | undefined,
    today: Date = new Date(),
): PhaseCompletions {
    const out: PhaseCompletions = {};
    if (!entries) return out;
    // A parent spans all sections; a leaf only its own and the unassigned ones.
    const sections = (e: VibEntryForProject) =>
        e.pfa_entries.filter((p) => isSuperior || p.project_id == null || p.project_id === projectId);
    const withSections = entries.filter((e) => sections(e).length > 0);
    if (withSections.length === 0) return out;
    const year = Math.max(...withSections.map((e) => e.year));
    const pfas = withSections.filter((e) => e.year === year).flatMap(sections);
    const suffix = pfas.length > 1 ? `, ${pfas.length} Abschnitte` : "";

    const beforeBau = lastPlanningPhase(hiddenPhases);
    const planning = latestPast(pfas, (p) => p.datum_pfb || p.baubeginn, today);
    if (beforeBau && planning) {
        add(out, beforeBau, { label: planning, source: `VIB ${year}, PFB bzw. Baubeginn${suffix}` });
    }
    const bau = latestPast(pfas, (p) => p.inbetriebnahme, today);
    if (bau) add(out, "BAU", { label: bau, source: `VIB ${year}, Inbetriebnahme${suffix}` });
    return out;
}

export function mergeCompletions(...parts: PhaseCompletions[]): PhaseCompletions {
    const out: PhaseCompletions = {};
    for (const part of parts) {
        for (const [phase, list] of Object.entries(part) as [MainPhase, PhaseCompletion[]][]) {
            for (const c of list) add(out, phase, c);
        }
    }
    return out;
}
