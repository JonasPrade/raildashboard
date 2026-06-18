import { Box, Group, Stack, Text } from "@mantine/core";
import { IconChevronRight } from "@tabler/icons-react";

import {
    MAIN_PHASES,
    MAIN_PHASE_LABEL,
    MAIN_PHASE_SHORT,
    type MainPhase,
    mainPhaseIndex,
} from "./phaseMeta";

type Props = {
    /** Effective (override-aware) current phase. */
    current: MainPhase;
    /** Superior span (min..max over children); highlights a range instead of one. */
    spanMin?: MainPhase | null;
    spanMax?: MainPhase | null;
    /** Dimmed when the lifecycle overlay (PAUSIERT/ABGEBROCHEN) is active. */
    dimmed?: boolean;
};

const ACTIVE = "var(--info)";
const DONE = "var(--ledOk, #2f9e44)";
const IDLE = "var(--rule)";

export default function PhaseStepper({ current, spanMin, spanMax, dimmed }: Props) {
    const isSpan = spanMin != null && spanMax != null;
    const currentIdx = mainPhaseIndex(current);
    const minIdx = isSpan ? mainPhaseIndex(spanMin as MainPhase) : currentIdx;
    const maxIdx = isSpan ? mainPhaseIndex(spanMax as MainPhase) : currentIdx;

    return (
        <Group
            gap={4}
            wrap="nowrap"
            align="flex-start"
            style={{ opacity: dimmed ? 0.45 : 1, overflowX: "auto" }}
        >
            {MAIN_PHASES.map((phase, idx) => {
                const inSpan = idx >= minIdx && idx <= maxIdx;
                const isCurrent = isSpan ? idx === minIdx || idx === maxIdx : idx === currentIdx;
                const isDone = idx < minIdx;

                let circleColor = IDLE;
                if (inSpan || isCurrent) circleColor = ACTIVE;
                else if (isDone) circleColor = DONE;

                return (
                    <Group gap={4} wrap="nowrap" key={phase} align="center">
                        <Stack gap={4} align="center" style={{ minWidth: 78 }}>
                            <Box
                                style={{
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
                                title={MAIN_PHASE_LABEL[phase]}
                            >
                                {idx + 1}
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
                        {idx < MAIN_PHASES.length - 1 && (
                            <IconChevronRight
                                size={18}
                                style={{ color: idx < maxIdx ? ACTIVE : IDLE, flexShrink: 0 }}
                            />
                        )}
                    </Group>
                );
            })}
        </Group>
    );
}
