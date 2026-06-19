import {
    Badge,
    Button,
    Group,
    Loader,
    Select,
    Stack,
    Switch,
    Text,
    TextInput,
} from "@mantine/core";
import { IconRefresh } from "@tabler/icons-react";

import { ChronicleCard, ChronicleHeadline } from "../../../../components/chronicle";
import { useAuth } from "../../../../lib/auth";
import {
    type ProjectProgressUpdate,
    useProjectProgress,
    useRecomputeProgress,
    useUpdateProjectProgress,
} from "../../../../shared/api/queries";
import ForecastPanel from "./ForecastPanel";
import LifecycleOverlay from "./LifecycleOverlay";
import ParallelLanes from "./ParallelLanes";
import PhaseStepper, { type StepperChild } from "./PhaseStepper";
import SourceBreakdown from "./SourceBreakdown";
import SubprojectsTable from "./SubprojectsTable";
import {
    LIFECYCLE_LABEL,
    MAIN_PHASES,
    MAIN_PHASE_LABEL,
    UNKNOWN_LABEL,
    groupChildrenByPhase,
    type LifecycleStatus,
    type MainPhase,
    type ParallelState,
} from "./phaseMeta";

const PARL_STANDARD = "__standard__";
const PHASE_NONE = "__none__";

export default function ProgressSection({ projectId }: { projectId: number }) {
    const { can } = useAuth();
    const canEdit = can("progress.edit");
    const { data: progress, isLoading, isError } = useProjectProgress(projectId);
    const update = useUpdateProjectProgress(projectId);
    const recompute = useRecomputeProgress(projectId);

    const patch = (payload: ProjectProgressUpdate) => update.mutate(payload);

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
                                    Aktuelle Phase: {MAIN_PHASE_LABEL[effectivePhase]} ·{" "}
                                    {(progress.computed_confidence * 100).toFixed(0)} % Vertrauen
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
                            variant="subtle"
                            size="xs"
                            leftSection={<IconRefresh size={14} />}
                            onClick={() => recompute.mutate()}
                            loading={recompute.isPending}
                        >
                            Neu berechnen
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
                />

                {progress.is_superior && progress.children.length > 0 && (
                    <SubprojectsTable children={progress.children} />
                )}

                <ParallelLanes
                    projectId={projectId}
                    hasPf={progress.has_planfeststellung}
                    pfState={progress.pf_state as ParallelState | null}
                    parlRelevant={progress.parl_befassung_relevant}
                    parlState={progress.parl_state as ParallelState | null}
                    pfDocuments={progress.pf_documents}
                    parlDocuments={progress.parl_documents}
                    canEdit={canEdit}
                />

                {!isDimmed && (
                    <Stack gap="xs">
                        <Text size="sm" fw={700} c="dimmed" tt="uppercase" style={{ letterSpacing: 0.5 }}>
                            Prognose
                        </Text>
                        <ForecastPanel forecast={progress.forecast} />
                    </Stack>
                )}

                {canEdit && (
                    <Stack gap="sm">
                        <Group gap="lg" align="flex-end" wrap="wrap">
                            <Switch
                                label="Hat Planfeststellung"
                                checked={progress.has_planfeststellung}
                                onChange={(e) =>
                                    patch({ has_planfeststellung: e.currentTarget.checked })
                                }
                            />
                            <Select
                                size="xs"
                                label="Parl. Befassung"
                                w={180}
                                value={
                                    progress.parl_befassung_relevant_override === null ||
                                    progress.parl_befassung_relevant_override === undefined
                                        ? PARL_STANDARD
                                        : progress.parl_befassung_relevant_override
                                          ? "true"
                                          : "false"
                                }
                                data={[
                                    { value: PARL_STANDARD, label: "Gruppen-Standard" },
                                    { value: "true", label: "Relevant" },
                                    { value: "false", label: "Nicht relevant" },
                                ]}
                                onChange={(v) => {
                                    if (v === PARL_STANDARD) patch({ clear_parl_relevant: true });
                                    else patch({ parl_befassung_relevant: v === "true" });
                                }}
                            />
                            <Select
                                size="xs"
                                label="Lebenszyklus"
                                w={150}
                                value={lifecycle}
                                data={(["AKTIV", "PAUSIERT", "ABGEBROCHEN"] as LifecycleStatus[]).map(
                                    (s) => ({ value: s, label: LIFECYCLE_LABEL[s] }),
                                )}
                                onChange={(v) =>
                                    v && patch({ lifecycle_status: v as LifecycleStatus })
                                }
                            />
                        </Group>

                        <Group gap="lg" align="flex-end" wrap="wrap">
                            <Select
                                size="xs"
                                label="Phasen-Override"
                                w={200}
                                value={progress.is_overridden ? progress.effective_phase : PHASE_NONE}
                                data={[
                                    { value: PHASE_NONE, label: "— berechnet —" },
                                    ...MAIN_PHASES.map((p) => ({ value: p, label: MAIN_PHASE_LABEL[p] })),
                                ]}
                                onChange={(v) => {
                                    if (!v || v === PHASE_NONE) patch({ clear_phase_override: true });
                                    else patch({ manual_phase_override: v as MainPhase });
                                }}
                            />
                            <TextInput
                                size="xs"
                                label="Override-Notiz"
                                w={280}
                                defaultValue={progress.manual_override_note ?? ""}
                                onBlur={(e) =>
                                    patch({ manual_override_note: e.currentTarget.value || null })
                                }
                            />
                        </Group>
                    </Stack>
                )}

                <SourceBreakdown
                    projectId={projectId}
                    contributions={progress.contributions}
                    observations={progress.observations}
                    canEdit={canEdit}
                />
            </Stack>
        </ChronicleCard>
    );
}
