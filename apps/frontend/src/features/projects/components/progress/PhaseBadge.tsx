import type { ReactNode } from "react";
import { Badge, Group } from "@mantine/core";

import { SwatchTag } from "../../../../shared/ui/SwatchTag";
import {
    LIFECYCLE_LABEL,
    MAIN_PHASE_COLOR,
    MAIN_PHASE_LABEL,
    MAIN_PHASES,
    UNKNOWN_LABEL,
    UNKNOWN_PHASE_COLOR,
    type LifecycleStatus,
    type MainPhase,
} from "./phaseMeta";

type Props = {
    /** Headline phase; null/unknown values render the "Unbekannt" badge. */
    phase: string | null | undefined;
    lifecycle?: string | null;
};

const isMainPhase = (value: string | null | undefined): value is MainPhase =>
    typeof value === "string" && (MAIN_PHASES as string[]).includes(value);

/**
 * Phase tag (Stufe 3): outline badge with a square in the phase colour and the
 * phase name. Unknown values get the "Unbekannt" colour; `children` replaces the
 * label (e.g. "3× Bau" in a distribution).
 */
export function PhaseTag({
    phase,
    children,
    size = "sm",
    dimmed = false,
}: {
    phase: string | null | undefined;
    children?: ReactNode;
    size?: "xs" | "sm" | "md";
    dimmed?: boolean;
}) {
    const known = isMainPhase(phase);
    const label = known ? MAIN_PHASE_LABEL[phase] : phase || UNKNOWN_LABEL;
    return (
        <SwatchTag
            size={size}
            color={known ? MAIN_PHASE_COLOR[phase] : UNKNOWN_PHASE_COLOR}
            muted={dimmed}
        >
            {children ?? label}
        </SwatchTag>
    );
}

/**
 * Compact planning-phase badge for overview cards. Same tag as the
 * SubprojectsTable; a paused/aborted project gets a second grey lifecycle badge
 * (the lifecycle never changes the phase itself).
 */
export default function PhaseBadge({ phase, lifecycle }: Props) {
    const paused = lifecycle === "PAUSIERT" || lifecycle === "ABGEBROCHEN";
    return (
        <Group gap={4} wrap="wrap">
            {isMainPhase(phase) ? (
                <PhaseTag phase={phase} dimmed={paused} />
            ) : (
                <PhaseTag phase={null}>{UNKNOWN_LABEL}</PhaseTag>
            )}
            {paused && (
                <Badge size="sm" variant="outline" color="gray">
                    {LIFECYCLE_LABEL[lifecycle as LifecycleStatus]}
                </Badge>
            )}
        </Group>
    );
}
