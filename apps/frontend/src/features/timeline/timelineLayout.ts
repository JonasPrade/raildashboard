// Pure layout helpers for the multi-project timeline ("Zeitstrahl").
// See docs/features/feature-project-timeline.md.

import type { ProjectTimeline, TimelineMilestone } from "../../shared/api/queries";
import { MAIN_PHASE_LABEL, mainPhaseIndex, type MainPhase } from "../projects/components/progress/phaseMeta";

export type TimelineSort = "betrieb" | "bau" | "name";

export const TIMELINE_SORT_OPTIONS: { value: TimelineSort; label: string }[] = [
    { value: "betrieb", label: "Inbetriebnahme" },
    { value: "bau", label: "Baubeginn" },
    { value: "name", label: "Name" },
];

export function parseTimelineSort(value: string | null): TimelineSort {
    return value === "bau" || value === "name" ? value : "betrieb";
}

/** ISO date (YYYY-MM-DD) → UTC milliseconds. */
export function toTime(iso: string): number {
    const [y, m, d] = iso.split("-").map(Number);
    return Date.UTC(y!, (m ?? 1) - 1, d ?? 1);
}

export type TimelineRange = { start: number; end: number };

export type Segment = {
    phase: MainPhase;
    start: number;
    end: number;
    // Part of the segment after today: drawn as "geplant".
    planned: boolean;
};

function phaseMilestones(milestones: TimelineMilestone[]): TimelineMilestone[] {
    return milestones
        .filter((m) => m.kind === "PHASE" && m.phase)
        .sort((a, b) => mainPhaseIndex(a.phase as MainPhase) - mainPhaseIndex(b.phase as MainPhase));
}

/**
 * Phase bars of one row: each dated phase runs until the next dated phase
 * starts. The last phase before "In Betrieb" runs until today when it started
 * in the past (ongoing); "In Betrieb" itself is a marker, not a bar. Every bar
 * is split at today into a done and a planned part. Contradicting dates
 * (a later phase dated earlier) produce no bar.
 */
export function buildSegments(milestones: TimelineMilestone[], today: number): Segment[] {
    const phases = phaseMilestones(milestones);
    const segments: Segment[] = [];
    phases.forEach((m, idx) => {
        const phase = m.phase as MainPhase;
        if (phase === "IN_BETRIEB") return;
        const start = toTime(m.date);
        const next = phases[idx + 1];
        const end = next ? toTime(next.date) : start < today ? today : null;
        if (end === null || end <= start) return;
        if (end <= today) {
            segments.push({ phase, start, end, planned: false });
        } else if (start >= today) {
            segments.push({ phase, start, end, planned: true });
        } else {
            segments.push({ phase, start, end: today, planned: false });
            segments.push({ phase, start: today, end, planned: true });
        }
    });
    return segments;
}

/** Whole-year range covering every milestone and today. */
export function computeRange(rows: ProjectTimeline[], today: number): TimelineRange {
    let min = today;
    let max = today;
    for (const row of rows) {
        for (const m of row.milestones) {
            const t = toTime(m.date);
            if (t < min) min = t;
            if (t > max) max = t;
        }
    }
    const startYear = new Date(min).getUTCFullYear();
    const endYear = new Date(max).getUTCFullYear() + 1;
    return { start: Date.UTC(startYear, 0, 1), end: Date.UTC(endYear, 0, 1) };
}

/** Year ticks with a step of 1/2/5/10 years so at most ``maxTicks`` fit. */
export function yearTicks(range: TimelineRange, maxTicks: number): number[] {
    const first = new Date(range.start).getUTCFullYear();
    const last = new Date(range.end).getUTCFullYear();
    const span = last - first;
    const step = [1, 2, 5, 10].find((s) => span / s <= maxTicks) ?? 10;
    const ticks: number[] = [];
    for (let y = Math.ceil(first / step) * step; y <= last; y += step) ticks.push(y);
    return ticks;
}

/** Position of ``time`` in the range, as a percentage (clamped to 0..100). */
export function percent(time: number, range: TimelineRange): number {
    const span = range.end - range.start;
    if (span <= 0) return 0;
    return Math.min(100, Math.max(0, ((time - range.start) / span) * 100));
}

function phaseDate(row: ProjectTimeline, phase: MainPhase): number | null {
    const m = row.milestones.find((x) => x.kind === "PHASE" && x.phase === phase);
    return m ? toTime(m.date) : null;
}

/** Sort rows by opening / construction start (undated last) or by name. */
export function sortRows(rows: ProjectTimeline[], sort: TimelineSort): ProjectTimeline[] {
    const byName = (a: ProjectTimeline, b: ProjectTimeline) => a.name.localeCompare(b.name, "de");
    if (sort === "name") return [...rows].sort(byName);
    const phase: MainPhase = sort === "bau" ? "BAU" : "IN_BETRIEB";
    return [...rows].sort((a, b) => {
        const da = phaseDate(a, phase);
        const db = phaseDate(b, phase);
        if (da === null && db === null) return byName(a, b);
        if (da === null) return 1;
        if (db === null) return -1;
        return da - db || byName(a, b);
    });
}

/** "05/2026" — the backend normalises coarse dates (quarter, year) to a
 * representative day, so a day would be false precision. */
export function formatMonth(iso: string): string {
    const [y, m] = iso.split("-");
    return `${m}/${y}`;
}

const PHASE_EVENT_LABEL: Record<MainPhase, string> = {
    NICHT_GESTARTET: "Projektstart",
    VORPLANUNG: "Beginn Vorplanung",
    GENEHMIGUNGSPLANUNG: "Beginn Genehmigungsplanung",
    BAU: "Baubeginn",
    IN_BETRIEB: "Inbetriebnahme",
};

/** Human-readable description of one milestone (tooltip / aria label). */
export function milestoneLabel(m: TimelineMilestone): string {
    const when = formatMonth(m.date);
    if (m.kind === "PFB") return `Planfeststellung ${when} · ${m.source}`;
    if (m.kind === "PARL") return `Parlamentarische Befassung ${when} · ${m.source}`;
    const phase = m.phase as MainPhase;
    if (m.certainty === "EVIDENCE") {
        return `${MAIN_PHASE_LABEL[phase]} spätestens seit ${when} · ${m.source}`;
    }
    return `${PHASE_EVENT_LABEL[phase]} ${when} · ${m.source}`;
}
