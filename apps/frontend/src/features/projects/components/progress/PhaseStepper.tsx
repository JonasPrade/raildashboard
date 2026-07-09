import { Box, Group, Stack, Text, Tooltip } from "@mantine/core";
import { IconChevronRight } from "@tabler/icons-react";

import {
    MAIN_PHASES,
    MAIN_PHASE_LABEL,
    MAIN_PHASE_SHORT,
    PARALLEL_STATE_LABEL,
    UNKNOWN_LABEL,
    type MainPhase,
    type ParallelState,
    mainPhaseIndex,
} from "./phaseMeta";
import { formatDateShort } from "../../../../shared/format";

export type StepperChild = { project_id: number; name: string };

type Props = {
    /** Effective (override-aware) current phase. */
    current: MainPhase;
    /** Superior span (min..max over children); highlights a range instead of one. */
    spanMin?: MainPhase | null;
    spanMax?: MainPhase | null;
    /** Dimmed when the lifecycle overlay (PAUSIERT/ABGEBROCHEN) is active. */
    dimmed?: boolean;
    /** Leaf project with no phase information → nothing active, "Unbekannt". */
    unknown?: boolean;
    /** Suppress the green "completed" marking for phases before the span — used
     * for superiors with unknown children, where we cannot claim every child
     * has passed the earlier phases. */
    noCompleted?: boolean;
    /** For superior projects: subprojects grouped by phase, shown on hover. */
    childrenByPhase?: Partial<Record<MainPhase, StepperChild[]>>;
    /** Whether the Planfeststellung gate (PFB) is relevant for this project.
     * When true, a milestone marker is drawn on the Genehmigungsplanung→Bau
     * connector — that boundary is exactly where the Planfeststellungsbeschluss
     * legally gates the start of construction. Only shown when explicitly set. */
    pfRelevant?: boolean;
    /** Resolved Planfeststellung track state, drives the marker colour. */
    pfState?: ParallelState | null;
    /** PFB date (ISO), shown under the marker when present. */
    pfDate?: string | null;
    /** Whether the parl. Befassung gate is relevant; drawn as a milestone on the
     * Vorplanung→Genehmigungsplanung connector. Only shown when explicitly set. */
    parlRelevant?: boolean;
    /** Resolved parl. Befassung track state, drives the marker colour. */
    parlState?: ParallelState | null;
    /** parl. Befassung date (ISO), shown under the marker when present. */
    parlDate?: string | null;
};

const ACTIVE = "var(--info)";
const DONE = "var(--ledOk, #2f9e44)";
const IDLE = "var(--rule)";

/**
 * Gate milestone marker rendered on a second tier *below* a timeline connector
 * (linked by a short connector), so the main flow stays intact. Green/filled when
 * abgeschlossen, blue/filled while it läuft, outline when still offen. Used for the
 * Planfeststellungsbeschluss and the parliamentary involvement.
 */
function Milestone({
    label,
    tooltipPrefix,
    state,
    date,
}: {
    label: string;
    tooltipPrefix: string;
    state: ParallelState | null;
    date: string | null;
}) {
    const done = state === "ABGESCHLOSSEN";
    const running = state === "LAEUFT";
    const color = done ? DONE : running ? ACTIVE : IDLE;
    const filled = done || running;
    const formattedDate = date ? formatDateShort(date) : null;
    const stateLabel = PARALLEL_STATE_LABEL[state ?? "OFFEN"];
    return (
        <Tooltip
            label={`${tooltipPrefix}: ${stateLabel}${formattedDate ? ` · ${formattedDate}` : ""}`}
            withArrow
            position="bottom"
            events={{ hover: true, focus: true, touch: true }}
        >
            <Stack gap={3} align="center" style={{ minWidth: 52, cursor: "default" }}>
                {/* short connector linking the marker up to the timeline boundary */}
                <Box style={{ width: 2, height: 6, backgroundColor: color }} />
                <Box
                    style={{
                        width: 14,
                        height: 14,
                        transform: "rotate(45deg)",
                        border: `2px solid ${color}`,
                        backgroundColor: filled ? color : "transparent",
                    }}
                />
                <Text size="xs" ta="center" fw={done ? 700 : 400} c={filled ? undefined : "dimmed"} style={{ lineHeight: 1.1, whiteSpace: "nowrap" }}>
                    {label}{done ? " ✓" : ""}
                </Text>
                {formattedDate && (
                    <Text ta="center" c="dimmed" style={{ fontSize: 10, lineHeight: 1.1, whiteSpace: "nowrap" }}>
                        {formattedDate}
                    </Text>
                )}
            </Stack>
        </Tooltip>
    );
}

export default function PhaseStepper({
    current,
    spanMin,
    spanMax,
    dimmed,
    unknown,
    noCompleted,
    childrenByPhase,
    pfRelevant,
    pfState,
    pfDate,
    parlRelevant,
    parlState,
    parlDate,
}: Props) {
    const isSpan = spanMin != null && spanMax != null;
    const currentIdx = mainPhaseIndex(current);
    const minIdx = unknown ? -1 : isSpan ? mainPhaseIndex(spanMin as MainPhase) : currentIdx;
    const maxIdx = unknown ? -1 : isSpan ? mainPhaseIndex(spanMax as MainPhase) : currentIdx;
    // Gate milestones sit on connectors leaving a phase: the parliamentary
    // involvement after Vorplanung (→ Genehmigungsplanung), the PFB after
    // Genehmigungsplanung (→ Bau).
    const parlBoundaryIdx = mainPhaseIndex("VORPLANUNG");
    const pfBoundaryIdx = mainPhaseIndex("GENEHMIGUNGSPLANUNG");

    return (
        <Group
            gap={4}
            wrap="nowrap"
            align="flex-start"
            style={{ opacity: dimmed ? 0.45 : 1, overflowX: "auto" }}
        >
            {MAIN_PHASES.map((phase, idx) => {
                const inSpan = !unknown && idx >= minIdx && idx <= maxIdx;
                const isCurrent = !unknown && (isSpan ? idx === minIdx || idx === maxIdx : idx === currentIdx);
                const isDone = !unknown && !noCompleted && idx < minIdx;

                let circleColor = IDLE;
                if (inSpan || isCurrent) circleColor = ACTIVE;
                else if (isDone) circleColor = DONE;

                const phaseChildren = childrenByPhase?.[phase] ?? [];
                const tooltipLabel =
                    phaseChildren.length > 0 ? (
                        <Stack gap={2}>
                            <Text size="xs" fw={700}>
                                {MAIN_PHASE_LABEL[phase]} ({phaseChildren.length})
                            </Text>
                            {phaseChildren.slice(0, 12).map((c) => (
                                <Text key={c.project_id} size="xs">
                                    {c.name}
                                </Text>
                            ))}
                            {phaseChildren.length > 12 && (
                                <Text size="xs" c="dimmed">
                                    + {phaseChildren.length - 12} weitere
                                </Text>
                            )}
                        </Stack>
                    ) : (
                        MAIN_PHASE_LABEL[phase]
                    );

                return (
                    <Group gap={4} wrap="nowrap" key={phase} align="flex-start">
                        <Tooltip label={tooltipLabel} multiline withArrow position="top" events={{ hover: true, focus: true, touch: true }}>
                            <Stack gap={4} align="center" style={{ minWidth: 78, cursor: "default" }}>
                                <Box
                                    style={{
                                        position: "relative",
                                        width: 28,
                                        height: 28,
                                        borderRadius: "50%",
                                        border: `2px solid ${circleColor}`,
                                        backgroundColor: inSpan || isCurrent || isDone ? circleColor : "transparent",
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        color: inSpan || isCurrent || isDone ? "#fff" : "var(--ink, #333)",
                                        fontSize: 12,
                                        fontWeight: 700,
                                    }}
                                >
                                    {idx + 1}
                                    {phaseChildren.length > 0 && (
                                        <Box
                                            style={{
                                                position: "absolute",
                                                top: -6,
                                                right: -6,
                                                minWidth: 16,
                                                height: 16,
                                                padding: "0 4px",
                                                borderRadius: 8,
                                                backgroundColor: "var(--board, #1f2933)",
                                                color: "#fff",
                                                fontSize: 10,
                                                lineHeight: "16px",
                                                textAlign: "center",
                                            }}
                                        >
                                            {phaseChildren.length}
                                        </Box>
                                    )}
                                </Box>
                                <Text
                                    size="xs"
                                    ta="center"
                                    fw={isCurrent ? 700 : 400}
                                    c={inSpan || isCurrent ? undefined : "dimmed"}
                                    style={{ lineHeight: 1.1 }}
                                >
                                    {MAIN_PHASE_SHORT[phase]}
                                </Text>
                            </Stack>
                        </Tooltip>
                        {idx < MAIN_PHASES.length - 1 && (
                            <Stack gap={4} align="center" style={{ flexShrink: 0 }}>
                                {/* Arrow stays on the main timeline row, vertically centred
                                    with the phase circles (28px band). */}
                                <Box style={{ height: 28, display: "flex", alignItems: "center" }}>
                                    <IconChevronRight
                                        size={18}
                                        style={{ color: !unknown && idx < maxIdx ? ACTIVE : IDLE }}
                                    />
                                </Box>
                                {idx === parlBoundaryIdx && parlRelevant && (
                                    <Milestone
                                        label="Parl."
                                        tooltipPrefix="Parlamentarische Befassung"
                                        state={parlState ?? null}
                                        date={parlDate ?? null}
                                    />
                                )}
                                {idx === pfBoundaryIdx && pfRelevant && (
                                    <Milestone
                                        label="PFB"
                                        tooltipPrefix="Planfeststellung"
                                        state={pfState ?? null}
                                        date={pfDate ?? null}
                                    />
                                )}
                            </Stack>
                        )}
                    </Group>
                );
            })}
            {unknown && (
                <Text size="sm" c="dimmed" fs="italic" style={{ alignSelf: "center", paddingLeft: 8 }}>
                    {UNKNOWN_LABEL}
                </Text>
            )}
        </Group>
    );
}
