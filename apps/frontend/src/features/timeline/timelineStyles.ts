import type { CSSProperties } from "react";

import { TIMELINE_COLOR, TIMELINE_PHASE_COLOR } from "../../shared/theme/semanticColors";
import type { MainPhase } from "../projects/components/progress/phaseMeta";

// Fill rules of the Zeitstrahl (feature-idt-design.md → Diagramme, W4).

/** Segment colour of a phase (teal, cyan, ink, "In Betrieb" green). */
export const phaseColor = (phase: MainPhase): string => TIMELINE_PHASE_COLOR[phase];

/** Planned part (after today): hatched in the phase colour, not lighter. */
export function plannedFill(color: string): string {
    return `repeating-linear-gradient(135deg, ${color} 0 4px, transparent 4px 8px)`;
}

/** Pause between construction stages: a thin dashed line in seq-4. */
export function gapFill(color: string = TIMELINE_COLOR.stagePause): string {
    return `repeating-linear-gradient(90deg, ${color} 0 4px, transparent 4px 8px)`;
}

/** Background of a phase segment: solid when past, hatched when planned. */
export function segmentFill(phase: MainPhase, planned: boolean): string {
    const color = phaseColor(phase);
    return planned ? plannedFill(color) : color;
}

/** Open area of a lower bound („nach 2031“): a pale hatch in the phase colour. */
export function openFill(color: string): string {
    const pale = `color-mix(in srgb, ${color} 45%, transparent)`;
    return `repeating-linear-gradient(135deg, ${pale} 0 3px, transparent 3px 9px)`;
}

/**
 * Soft edges of a year-only date: the segment fades in (and/or out) over
 * ``fadePct`` percent of its width — no hard edge where the day is unknown.
 */
export function fuzzyMask(fuzzyStart: boolean, fuzzyEnd: boolean, fadePct = 35): string | undefined {
    if (!fuzzyStart && !fuzzyEnd) return undefined;
    const from = fuzzyStart ? `transparent 0, #000 ${fadePct}%` : "#000 0";
    const to = fuzzyEnd ? `#000 ${100 - fadePct}%, transparent 100%` : "#000 100%";
    return `linear-gradient(90deg, ${from}, ${to})`;
}

/** Dashed outline of a segment with an assumed (not published) edge. */
export const ASSUMED_OUTLINE = `1.5px dashed ${TIMELINE_COLOR.marker}`;

/**
 * Milestone marker: commissioning is a 10px square in --idt-success, other
 * phase starts are 9px points in the phase colour with an ink rim; evidence
 * ("spätestens seit") is hollow in ink. PFB/Parl. are ink diamonds.
 */
export function markerStyle(
    kind: "PHASE" | "PFB" | "PARL" | "PART_IBN" | string,
    phase: MainPhase | null | undefined,
    evidence: boolean,
    precision?: string | null,
): CSSProperties {
    const ink = TIMELINE_COLOR.marker;
    const hollow = "var(--surface)";
    // A year-only or assumed date is no fixed point: hollow with a dashed rim.
    const uncertain = precision === "YEAR" || precision === "ASSUMED";
    if (kind === "PART_IBN") {
        // Partial commissioning: the commissioning marker, hollow (#344).
        return {
            width: 10,
            height: 10,
            border: `2px ${uncertain ? "dashed" : "solid"} ${TIMELINE_COLOR.commissioning}`,
            background: hollow,
        };
    }
    if (kind === "PHASE") {
        if (phase === "IN_BETRIEB") {
            const rim = evidence ? ink : TIMELINE_COLOR.commissioning;
            return {
                width: 10,
                height: 10,
                border: `2px ${uncertain ? "dashed" : "solid"} ${rim}`,
                background: evidence || uncertain ? hollow : TIMELINE_COLOR.commissioning,
            };
        }
        return {
            width: 9,
            height: 9,
            borderRadius: "50%",
            border: `2px ${uncertain ? "dashed" : "solid"} ${ink}`,
            background: evidence || uncertain || !phase ? hollow : phaseColor(phase),
        };
    }
    return {
        width: 9,
        height: 9,
        transform: "rotate(45deg)",
        border: `2px solid ${ink}`,
        background: kind === "PFB" ? ink : hollow,
    };
}
