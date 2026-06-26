import { useState } from "react";
import { Badge, Button, Group, Loader, Stack, Text } from "@mantine/core";
import { IconPencil } from "@tabler/icons-react";

import { ChronicleCard, ChronicleHeadline } from "../../../../components/chronicle";
import { useAuth } from "../../../../lib/auth";
import { useProjectProgress } from "../../../../shared/api/queries";
import ForecastPanel from "./ForecastPanel";
import LifecycleOverlay from "./LifecycleOverlay";
import ParallelLanes from "./ParallelLanes";
import PhaseStepper, { type StepperChild } from "./PhaseStepper";
import ProgressEditDrawer from "./ProgressEditDrawer";
import SourceBreakdown from "./SourceBreakdown";
import SubprojectsTable from "./SubprojectsTable";
import {
    LIFECYCLE_LABEL,
    MAIN_PHASE_LABEL,
    UNKNOWN_LABEL,
    groupChildrenByPhase,
    type LifecycleStatus,
    type MainPhase,
    type ParallelState,
} from "./phaseMeta";

export default function ProgressSection({ projectId }: { projectId: number }) {
    const { can, user } = useAuth();
    const canEdit = can("progress.edit");
    const { data: progress, isLoading, isError } = useProjectProgress(projectId);
    const [editing, setEditing] = useState(false);

    if (isLoading) {
        return (
            <ChronicleCard>
                <Group gap="sm">
                    <Loader size="sm" />
                    <Text size="sm" c="dimmed">
                        Planungsstand wird geladen …
                    </Text>
                </Group>
            </ChronicleCard>
        );
    }
    if (isError || !progress) {
        return (
            <ChronicleCard>
                <Text size="sm" c="dimmed">
                    Planungsstand konnte nicht geladen werden.
                </Text>
            </ChronicleCard>
        );
    }

    const lifecycle = progress.lifecycle_status as LifecycleStatus;
    const isDimmed = lifecycle !== "AKTIV";
    const effectivePhase = progress.effective_phase as MainPhase;

    const hasSpan = Boolean(progress.span_min_phase && progress.span_max_phase);
    // Leaf project with no phase information → render as "Unbekannt".
    const isUnknownLeaf = !progress.is_superior && !progress.is_known;

    // Subprojects grouped by phase, for the stepper hover tooltips.
    const { byPhase: childrenByPhase, unknown: unknownChildren } = groupChildrenByPhase(
        progress.children,
    );
    const hasUnknownChildren = unknownChildren.length > 0;
    const stepperChildren: Partial<Record<MainPhase, StepperChild[]>> = {};
    (Object.keys(childrenByPhase) as MainPhase[]).forEach((phase) => {
        stepperChildren[phase] = (childrenByPhase[phase] ?? []).map((c) => ({
            project_id: c.project_id,
            name: c.name,
        }));
    });

    return (
        <ChronicleCard>
            <Stack gap="lg">
                <Group justify="space-between" align="flex-start">
                    <Stack gap={2}>
                        <ChronicleHeadline as="h2" style={{ fontSize: "1.15rem" }}>
                            Planungsstand
                        </ChronicleHeadline>
                        <Group gap="sm">
                            {progress.is_superior ? (
                                hasSpan ? (
                                    <Text size="sm" c="dimmed">
                                        Spanne der Unterprojekte:{" "}
                                        {MAIN_PHASE_LABEL[progress.span_min_phase as MainPhase]} –{" "}
                                        {MAIN_PHASE_LABEL[progress.span_max_phase as MainPhase]}
                                    </Text>
                                ) : progress.is_overridden ? (
                                    // Editorial override pins the whole project to one phase.
                                    <Text size="sm" c="dimmed">
                                        Gesamter Abschnitt: {MAIN_PHASE_LABEL[effectivePhase]}
                                    </Text>
                                ) : (
                                    <Text size="sm" c="dimmed">
                                        Status der Unterprojekte unbekannt
                                    </Text>
                                )
                            ) : isUnknownLeaf ? (
                                <Text size="sm" c="dimmed">
                                    Aktuelle Phase: {UNKNOWN_LABEL} (keine Datengrundlage)
                                </Text>
                            ) : (
                                <Text size="sm" c="dimmed">
                                    Aktuelle Phase: {MAIN_PHASE_LABEL[effectivePhase]}
                                    {user?.role === "admin" &&
                                        ` · ${(progress.computed_confidence * 100).toFixed(0)} % Vertrauen`}
                                </Text>
                            )}
                            {progress.is_overridden && (
                                <Badge color="grape" variant="light" title={progress.manual_override_note ?? undefined}>
                                    übersteuert
                                </Badge>
                            )}
                            {isDimmed && (
                                <Badge color={lifecycle === "ABGEBROCHEN" ? "red" : "orange"}>
                                    {LIFECYCLE_LABEL[lifecycle]}
                                </Badge>
                            )}
                        </Group>
                    </Stack>
                    {canEdit && (
                        <Button
                            variant="light"
                            size="xs"
                            leftSection={<IconPencil size={14} />}
                            onClick={() => setEditing(true)}
                        >
                            Bearbeiten
                        </Button>
                    )}
                </Group>

                <LifecycleOverlay status={lifecycle} />

                <PhaseStepper
                    current={effectivePhase}
                    spanMin={progress.is_superior ? (progress.span_min_phase as MainPhase | null) : null}
                    spanMax={progress.is_superior ? (progress.span_max_phase as MainPhase | null) : null}
                    dimmed={isDimmed}
                    unknown={isUnknownLeaf}
                    noCompleted={progress.is_superior && hasUnknownChildren}
                    childrenByPhase={progress.is_superior ? stepperChildren : undefined}
                    pfRelevant={!progress.is_superior && progress.has_planfeststellung}
                    pfState={progress.pf_state as ParallelState | null}
                    pfDate={progress.pf_date}
                    parlRelevant={!progress.is_superior && progress.parl_befassung_relevant}
                    parlState={progress.parl_state as ParallelState | null}
                    parlDate={progress.parl_befassung_date}
                />

                {progress.is_superior && progress.children.length > 0 && (
                    <SubprojectsTable children={progress.children} />
                )}

                <ParallelLanes
                    hasPf={progress.has_planfeststellung}
                    pfState={progress.pf_state as ParallelState | null}
                    parlRelevant={progress.parl_befassung_relevant}
                    parlState={progress.parl_state as ParallelState | null}
                    parlText={progress.parl_befassung_text}
                    parlDrucksacheUrl={progress.parl_drucksache_url}
                    parlDate={progress.parl_befassung_date}
                    pfText={progress.pf_text}
                    pfLinks={progress.pf_links}
                    pfDate={progress.pf_date}
                    pfStateInGraphic={!progress.is_superior && progress.has_planfeststellung}
                    parlStateInGraphic={!progress.is_superior && progress.parl_befassung_relevant}
                />

                {!isDimmed && (
                    <Stack gap="xs">
                        <Text size="sm" fw={700} c="dimmed" tt="uppercase" style={{ letterSpacing: 0.5 }}>
                            Prognose
                        </Text>
                        <ForecastPanel forecast={progress.forecast} />
                    </Stack>
                )}

                <SourceBreakdown
                    contributions={progress.contributions}
                    observations={progress.observations}
                />
            </Stack>

            {canEdit && (
                <ProgressEditDrawer
                    projectId={projectId}
                    progress={progress}
                    opened={editing}
                    onClose={() => setEditing(false)}
                />
            )}
        </ChronicleCard>
    );
}
