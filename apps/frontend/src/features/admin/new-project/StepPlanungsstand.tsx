import { Stack, Text } from "@mantine/core";

import ProgressSection from "../../projects/components/progress/ProgressSection";

type Props = {
    projectId: number;
};

/**
 * Wizard step for the project's planning state. Reuses the same read-only
 * ProgressSection + edit drawer as the project detail view, so manual entry
 * (phase, confidence, observations, parallel tracks, documents) happens through
 * the familiar "Bearbeiten" drawer. Optional — the global wizard buttons handle
 * skipping / advancing.
 */
export default function StepPlanungsstand({ projectId }: Props) {
    return (
        <Stack gap="md">
            <Text c="dimmed" size="sm">
                Planungsstand für dieses Projekt erfassen (optional). Über „Bearbeiten" lassen sich
                Phase, Vertrauen, Beobachtungen sowie die Parallelspuren (Planfeststellung,
                parlamentarische Befassung) manuell eintragen. Der Stand ist später jederzeit in der
                Projektansicht änderbar.
            </Text>
            <ProgressSection projectId={projectId} />
        </Stack>
    );
}
