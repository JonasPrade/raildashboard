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

/**
 * Milestone marker: commissioning is a 10px square in --idt-success, other
 * phase starts are 9px points in the phase colour with an ink rim; evidence
 * ("spätestens seit") is hollow in ink. PFB/Parl. are ink diamonds.
 */
export function markerStyle(
    kind: "PHASE" | "PFB" | "PARL" | string,
    phase: MainPhase | null | undefined,
    evidence: boolean,
): CSSProperties {
    const ink = TIMELINE_COLOR.marker;
    const hollow = "var(--surface)";
    if (kind === "PHASE") {
        if (phase === "IN_BETRIEB") {
            return {
                width: 10,
                height: 10,
                border: `2px solid ${evidence ? ink : TIMELINE_COLOR.commissioning}`,
                background: evidence ? hollow : TIMELINE_COLOR.commissioning,
            };
        }
        return {
            width: 9,
            height: 9,
            borderRadius: "50%",
            border: `2px solid ${ink}`,
            background: evidence || !phase ? hollow : phaseColor(phase),
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
