import { Badge, Group } from "@mantine/core";

import {
    LIFECYCLE_LABEL,
    MAIN_PHASE_COLOR,
    MAIN_PHASE_LABEL,
    MAIN_PHASES,
    UNKNOWN_LABEL,
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
 * Compact planning-phase badge for overview cards. Same palette and
 * "Unbekannt" style as the SubprojectsTable; a paused/aborted project gets a
 * second grey lifecycle badge (the lifecycle never changes the phase itself).
 */
export default function PhaseBadge({ phase, lifecycle }: Props) {
    const paused = lifecycle === "PAUSIERT" || lifecycle === "ABGEBROCHEN";
    return (
        <Group gap={4} wrap="wrap">
            {isMainPhase(phase) ? (
                <Badge size="sm" variant="light" color={MAIN_PHASE_COLOR[phase]} style={paused ? { opacity: 0.6 } : undefined}>
                    {MAIN_PHASE_LABEL[phase]}
                </Badge>
            ) : (
                <Badge size="sm" variant="outline" color="gray">
                    {UNKNOWN_LABEL}
                </Badge>
            )}
            {paused && (
                <Badge size="sm" variant="outline" color="gray">
                    {LIFECYCLE_LABEL[lifecycle as LifecycleStatus]}
                </Badge>
            )}
        </Group>
    );
}
