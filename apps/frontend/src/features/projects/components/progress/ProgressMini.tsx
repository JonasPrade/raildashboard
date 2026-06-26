import { Box, Group, Stack, Text, Tooltip } from "@mantine/core";

import { useProjectProgress } from "../../../../shared/api/queries";
import {
    LIFECYCLE_LABEL,
    MAIN_PHASES,
    MAIN_PHASE_LABEL,
    UNKNOWN_LABEL,
    mainPhaseIndex,
    type LifecycleStatus,
    type MainPhase,
} from "./phaseMeta";

const ACTIVE = "var(--info)";
const DONE = "var(--ledOk, #2f9e44)";
const IDLE = "var(--rule)";

/**
 * Kompakte Leistungsphasen-Darstellung für die Kurzansicht eines Projekts
 * (Karten-Popup, Unter-/Übergeordnet-Abschnitte). Zeigt eine schlanke
 * Segment-Leiste über die fünf Hauptphasen plus eine Beschriftung des
 * aktuellen Stands. Spiegelt die Logik des großen ``PhaseStepper`` wider,
 * ohne Meilensteine/Parallelspuren.
 */
export default function ProgressMini({ projectId }: { projectId: number }) {
    const { data: progress } = useProjectProgress(projectId);
    if (!progress) return null;

    const lifecycle = progress.lifecycle_status as LifecycleStatus;
    const dimmed = lifecycle !== "AKTIV";
    const effectivePhase = progress.effective_phase as MainPhase;
    const isUnknownLeaf = !progress.is_superior && !progress.is_known;
    const isSpan = Boolean(progress.is_superior && progress.span_min_phase && progress.span_max_phase);
    const spanMin = isSpan ? (progress.span_min_phase as MainPhase) : null;
    const spanMax = isSpan ? (progress.span_max_phase as MainPhase) : null;
    // Superior with unknown children → cannot claim earlier phases are completed.
    const noCompleted = progress.is_superior && progress.children.some((c) => c.is_known === false);

    const currentIdx = mainPhaseIndex(effectivePhase);
    let minIdx = currentIdx;
    let maxIdx = currentIdx;
    if (isUnknownLeaf) {
        minIdx = -1;
        maxIdx = -1;
    } else if (isSpan) {
        minIdx = mainPhaseIndex(spanMin as MainPhase);
        maxIdx = mainPhaseIndex(spanMax as MainPhase);
    }

    let caption: string;
    if (progress.is_superior) {
        if (isSpan) {
            caption = `Unterprojekte: ${MAIN_PHASE_LABEL[spanMin as MainPhase]} – ${MAIN_PHASE_LABEL[spanMax as MainPhase]}`;
        } else if (progress.is_overridden) {
            caption = MAIN_PHASE_LABEL[effectivePhase];
        } else {
            caption = UNKNOWN_LABEL;
        }
    } else if (isUnknownLeaf) {
        caption = UNKNOWN_LABEL;
    } else {
        caption = MAIN_PHASE_LABEL[effectivePhase];
    }

    return (
        <Stack gap={4}>
            <Group gap={3} wrap="nowrap" style={{ opacity: dimmed ? 0.45 : 1 }}>
                {MAIN_PHASES.map((phase, idx) => {
                    const inSpan = !isUnknownLeaf && idx >= minIdx && idx <= maxIdx;
                    const isDone = !isUnknownLeaf && !noCompleted && idx < minIdx;
                    // "In Betrieb" is the terminal phase — reaching it means the
                    // project is effectively complete, so colour it green (DONE)
                    // rather than the in-progress blue.
                    let color = IDLE;
                    if (inSpan) color = phase === "IN_BETRIEB" ? DONE : ACTIVE;
                    else if (isDone) color = DONE;
                    return (
                        <Tooltip
                            key={phase}
                            label={MAIN_PHASE_LABEL[phase]}
                            withArrow
                            events={{ hover: true, focus: true, touch: true }}
                        >
                            <Box
                                style={{
                                    flex: 1,
                                    height: 6,
                                    minWidth: 12,
                                    borderRadius: 3,
                                    backgroundColor: color,
                                    cursor: "default",
                                }}
                            />
                        </Tooltip>
                    );
                })}
            </Group>
            <Group gap={6} wrap="nowrap" align="baseline">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: 0.4, flexShrink: 0 }}>
                    Planungsstand
                </Text>
                <Text size="xs" c={dimmed ? "dimmed" : undefined} style={{ lineHeight: 1.2 }}>
                    {caption}
                    {dimmed ? ` · ${LIFECYCLE_LABEL[lifecycle]}` : ""}
                </Text>
            </Group>
        </Stack>
    );
}
