import { Box, Group, Stack, Text, Tooltip } from "@mantine/core";
import { IconChevronRight } from "@tabler/icons-react";

import {
    MAIN_PHASES,
    MAIN_PHASE_LABEL,
    MAIN_PHASE_SHORT,
    UNKNOWN_LABEL,
    type MainPhase,
    mainPhaseIndex,
} from "./phaseMeta";

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
    /** For superior projects: subprojects grouped by phase, shown on hover. */
    childrenByPhase?: Partial<Record<MainPhase, StepperChild[]>>;
};

const ACTIVE = "var(--info)";
const DONE = "var(--ledOk, #2f9e44)";
const IDLE = "var(--rule)";

export default function PhaseStepper({
    current,
    spanMin,
    spanMax,
    dimmed,
    unknown,
    childrenByPhase,
}: Props) {
    const isSpan = spanMin != null && spanMax != null;
    const currentIdx = mainPhaseIndex(current);
    const minIdx = unknown ? -1 : isSpan ? mainPhaseIndex(spanMin as MainPhase) : currentIdx;
    const maxIdx = unknown ? -1 : isSpan ? mainPhaseIndex(spanMax as MainPhase) : currentIdx;

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
                const isDone = !unknown && idx < minIdx;

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
                    <Group gap={4} wrap="nowrap" key={phase} align="center">
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
                            <IconChevronRight
                                size={18}
                                style={{ color: !unknown && idx < maxIdx ? ACTIVE : IDLE, flexShrink: 0 }}
                            />
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
