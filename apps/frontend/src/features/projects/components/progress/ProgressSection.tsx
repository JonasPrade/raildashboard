import { useState } from "react";
import { Alert, Badge, Button, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { Pencil } from "lucide-react";

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
    SOURCE_LABEL,
    UNKNOWN_LABEL,
    groupChildrenByPhase,
    type LifecycleStatus,
    type MainPhase,
    type ParallelState,
    type SourceType,
} from "./phaseMeta";
import { LoadingState } from "../../../../shared/ui/LoadingState";

export default function ProgressSection({ projectId }: { projectId: number }) {
    const { can, user } = useAuth();
    const canEdit = can("progress.edit");
    const { data: progress, isLoading, isError } = useProjectProgress(projectId);
    const [editing, setEditing] = useState(false);

    if (isLoading) {
        return (
            <Paper withBorder p="var(--card-pad)">
                <LoadingState rows={4} label="Planungsstand wird geladen …" />
            </Paper>
        );
    }
    if (isError || !progress) {
        return (
            <Paper withBorder p="var(--card-pad)">
                <Text size="sm" c="dimmed">
                    Planungsstand konnte nicht geladen werden.
                </Text>
            </Paper>
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
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="lg">
                <Stack gap="xs">
                    <Group className="idt-section-head" justify="space-between" align="center" wrap="nowrap">
                        <Title order={2} className="idt-title-plain">
                            Planungsstand
                        </Title>
                        {canEdit && (
                            <Button
                                variant="light"
                                size="xs"
                                leftSection={<Pencil size={16} />}
                                onClick={() => setEditing(true)}
                            >
                                Bearbeiten
                            </Button>
                        )}
                    </Group>
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
                            <Badge color="violet" variant="light" title={progress.manual_override_note ?? undefined}>
                                übersteuert
                            </Badge>
                        )}
                        {isDimmed && (
                            <Badge variant="outline" color="gray">
                                {LIFECYCLE_LABEL[lifecycle]}
                            </Badge>
                        )}
                    </Group>
                </Stack>

                {canEdit && progress.conflict && (
                    <Alert color="orange" variant="light" title="Konflikt im Planungsstand">
                        {SOURCE_LABEL[progress.conflict.source_type as SourceType] ??
                            progress.conflict.source_type}{" "}
                        ({progress.conflict.observed_date ?? "ohne Datum"}) meldet{" "}
                        {MAIN_PHASE_LABEL[progress.conflict.asserted_phase as MainPhase]}, ältere Quellen
                        sehen das Projekt schon in{" "}
                        {MAIN_PHASE_LABEL[progress.conflict.contradicted_phase as MainPhase]}.{" "}
                        {progress.conflict.applied
                            ? "Die neuere Meldung ist vertrauenswürdiger und wurde übernommen."
                            : "Die neuere Meldung ist weniger vertrauenswürdig und wurde nicht übernommen."}{" "}
                        Auflösen per Phasen-Override oder manueller Beobachtung.
                    </Alert>
                )}

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
                    hiddenPhases={progress.hidden_phases}
                    forecastSteps={!isDimmed && progress.forecast?.has_data ? progress.forecast.next_steps : null}
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

                {!isDimmed && <ForecastPanel forecast={progress.forecast} />}

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
        </Paper>
    );
}
