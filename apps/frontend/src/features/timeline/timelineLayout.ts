// Pure layout helpers for the multi-project timeline ("Zeitstrahl").
// See docs/features/feature-project-timeline.md.

import type { ProjectTimeline, TimelineMilestone, TimelinePeriod } from "../../shared/api/queries";
import { asPrecision, formatQualifiedDate, qualifiedDateText } from "../../shared/datePrecision";
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
    // Pause between two construction stages of a superior ("zwischen
    // Bauetappen"): inside the BAU span, but no subproject is being built.
    gap?: boolean;
    // Date qualification (feature-project-progress.md → „Datumsqualifikation“),
    // set only when true:
    fuzzyStart?: boolean; // YEAR start: soft left edge
    fuzzyEnd?: boolean; // ends at a YEAR or lower-bound date: soft right edge
    assumed?: boolean; // an edge is ASSUMED: dashed outline
    open?: boolean; // NOT_BEFORE: open area from the bound to the right edge
    label?: string; // inline text („2028“, „nach 2031 – Termin offen“)
    title?: string; // tooltip (dates with precision, derivation)
};

const YEAR_MS = 365.25 * 24 * 3600 * 1000;

const precisionOf = (m: TimelineMilestone) => asPrecision(m.date_precision);

/** Display text of a milestone date with its precision and label. */
export function milestoneDateText(m: TimelineMilestone): string {
    return m.date_text ?? qualifiedDateText(m.date, m.date_precision, m.date_label) ?? formatMonth(m.date);
}

/** Where a phase bar starts: 1 Jan for a year-only date, else the date. */
function barTime(m: TimelineMilestone): number {
    return precisionOf(m) === "YEAR" ? Date.UTC(Number(m.date.slice(0, 4)), 0, 1) : toTime(m.date);
}

function phaseMilestones(milestones: TimelineMilestone[]): TimelineMilestone[] {
    return milestones
        .filter((m) => m.kind === "PHASE" && m.phase)
        .sort((a, b) => mainPhaseIndex(a.phase as MainPhase) - mainPhaseIndex(b.phase as MainPhase));
}

type SegmentExtras = Omit<Segment, "phase" | "start" | "end" | "planned">;

function pushSplitAtToday(
    segments: Segment[],
    phase: MainPhase,
    start: number,
    end: number,
    today: number,
    extras: SegmentExtras = {},
) {
    const { fuzzyStart, fuzzyEnd, label, ...shared } = extras;
    const first = { ...shared, ...(fuzzyStart && { fuzzyStart }), ...(label && { label }) };
    const last = { ...shared, ...(fuzzyEnd && { fuzzyEnd }) };
    if (end <= today) {
        segments.push({ phase, start, end, planned: false, ...first, ...last });
    } else if (start >= today) {
        segments.push({ phase, start, end, planned: true, ...first, ...last });
    } else {
        segments.push({ phase, start, end: today, planned: false, ...first });
        segments.push({ phase, start: today, end, planned: true, ...last });
    }
}

/** Tooltip of a phase bar: its dates with precision plus how assumed dates came about. */
function barTitle(m: TimelineMilestone, next: TimelineMilestone | undefined): string {
    const phase = MAIN_PHASE_LABEL[m.phase as MainPhase];
    const span = next ? `${milestoneDateText(m)} – ${milestoneDateText(next)}` : `ab ${milestoneDateText(m)}`;
    const derivations = [m.derivation, next?.derivation].filter(Boolean);
    return [`${phase}: ${span}`, ...derivations].join(" · ");
}

/**
 * BAU span of a superior whose subprojects build in separate stages: one bar
 * per construction period (clipped to the span), the pauses in between as
 * gap segments. Returns false when the periods don't split the span, so the
 * caller draws the plain bar.
 */
function pushConstructionStages(
    segments: Segment[],
    start: number,
    end: number,
    periods: TimelinePeriod[],
    today: number,
): boolean {
    const pieces = periods
        .map((p) => ({ start: Math.max(toTime(p.start), start), end: Math.min(toTime(p.end), end) }))
        .filter((p) => p.end > p.start)
        .sort((a, b) => a.start - b.start);
    if (pieces.length < 2) return false;
    pieces.forEach((piece, idx) => {
        const prev = pieces[idx - 1];
        if (prev && piece.start > prev.end) {
            segments.push({ phase: "BAU", start: prev.end, end: piece.start, planned: prev.end >= today, gap: true });
        }
        pushSplitAtToday(segments, "BAU", piece.start, piece.end, today);
    });
    return true;
}

/**
 * Phase bars of one row: each dated phase runs until the next dated phase
 * starts. The last phase before "In Betrieb" runs until today when it started
 * in the past (ongoing); "In Betrieb" itself is a marker, not a bar. Every bar
 * is split at today into a done and a planned part. Contradicting dates
 * (a later phase dated earlier) produce no bar. ``constructionPeriods`` (a
 * superior with separate construction stages) split the BAU bar into its
 * stages with gap segments in between.
 */
export function buildSegments(
    milestones: TimelineMilestone[],
    today: number,
    constructionPeriods: TimelinePeriod[] = [],
    rangeEnd?: number,
): Segment[] {
    const phases = phaseMilestones(milestones);
    const segments: Segment[] = [];
    for (const [idx, m] of phases.entries()) {
        const phase = m.phase as MainPhase;
        if (phase === "IN_BETRIEB") break;
        const precision = precisionOf(m);
        const next = phases[idx + 1];
        const start = barTime(m);
        const openEnd = rangeEnd ?? start + 2 * YEAR_MS;

        // „nach 2031“: no closed bar, an open area to the right edge; every
        // later phase is unknown as well.
        if (precision === "NOT_BEFORE") {
            if (openEnd > start) {
                segments.push({
                    phase,
                    start,
                    end: openEnd,
                    planned: true,
                    open: true,
                    label: `${milestoneDateText(m)}${m.date_label ? "" : " – Termin offen"}`,
                    title: barTitle(m, undefined),
                });
            }
            break;
        }

        const extras: SegmentExtras = {
            ...(precision === "YEAR" && { fuzzyStart: true, label: milestoneDateText(m) }),
            ...((precision === "ASSUMED" || (next && precisionOf(next) === "ASSUMED")) && { assumed: true }),
            title: barTitle(m, next),
        };
        let end: number | null;
        if (next) {
            end = barTime(next);
            const nextPrecision = precisionOf(next);
            if (nextPrecision === "YEAR" || nextPrecision === "NOT_BEFORE") extras.fuzzyEnd = true;
        } else if (start < today) {
            end = today;
        } else {
            // A lone year-only start spans its whole year.
            end = precision === "YEAR" ? start + YEAR_MS : null;
        }
        if (end === null || end <= start) continue;
        if (
            phase === "BAU" &&
            precision !== "YEAR" &&
            pushConstructionStages(segments, start, end, constructionPeriods, today)
        ) {
            continue;
        }
        pushSplitAtToday(segments, phase, start, end, today, extras);

        // The phase runs at least until a lower-bound opening, its end is open.
        if (next && next.phase === "IN_BETRIEB" && precisionOf(next) === "NOT_BEFORE" && openEnd > end) {
            segments.push({
                phase,
                start: end,
                end: openEnd,
                planned: true,
                open: true,
                label: `Inbetriebnahme ${milestoneDateText(next)}${next.date_label ? "" : " – Termin offen"}`,
                title: barTitle(next, undefined),
            });
        }
    }
    return segments;
}

/** Whole-year range covering every milestone and today. */
export function computeRange(rows: ProjectTimeline[], today: number): TimelineRange {
    let min = today;
    let max = today;
    for (const row of rows) {
        for (const m of row.milestones) {
            // A lower bound counts with its bound only — the open area runs to
            // the end of that year, the axis is not stretched for it.
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

/** "05/2026" — month and year of an ISO date. */
export function formatMonth(iso: string): string {
    const [y, m] = iso.split("-");
    return `${m}/${y}`;
}

/** Short date for the row header („IB 2028“, „IB nach 2031“, „IB ca. 07/2028“). */
export function shortMilestoneDate(m: TimelineMilestone): string {
    const precision = precisionOf(m);
    if (precision === "YEAR") return m.date.slice(0, 4);
    if (precision === "NOT_BEFORE") return formatQualifiedDate(m.date, precision) ?? formatMonth(m.date);
    if (precision === "ASSUMED") return `ca. ${formatMonth(m.date)}`;
    return formatMonth(m.date);
}

/** Where a marker sits: mid-year for a year-only date, else the date itself. */
export function markerTime(m: TimelineMilestone): number {
    return precisionOf(m) === "YEAR" ? Date.UTC(Number(m.date.slice(0, 4)), 6, 1) : toTime(m.date);
}

/** Markers drawn: a lower bound has no point in time — its open area shows it. */
export function drawnMarkers(milestones: TimelineMilestone[]): TimelineMilestone[] {
    return milestones.filter((m) => precisionOf(m) !== "NOT_BEFORE");
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
    const when = milestoneDateText(m);
    const derivation = m.derivation ? ` · ${m.derivation}` : "";
    if (m.kind === "PFB") return `Planfeststellung ${when} · ${m.source}`;
    if (m.kind === "PARL") return `Parlamentarische Befassung ${when} · ${m.source}`;
    const phase = m.phase as MainPhase;
    if (m.certainty === "EVIDENCE") {
        return `${MAIN_PHASE_LABEL[phase]} spätestens seit ${when} · ${m.source}`;
    }
    return `${PHASE_EVENT_LABEL[phase]} ${when} · ${m.source}${derivation}`;
}
