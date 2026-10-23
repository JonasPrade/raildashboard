import { Link } from "react-router-dom";
import { Alert, Badge, Button, Container, Group, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";

import RequirePermission from "../../components/RequirePermission";
import {
    type ProgressConflictRow,
    queryKeys,
    useProgressConflicts,
    useStartProgressRecomputeAll,
} from "../../shared/api/queries";
import { TaskProgressIndicator, useImportTask } from "../import-review/shared";
import {
    SOURCE_LABEL,
    formatAge,
    type MainPhase,
    type SourceType,
} from "../projects/components/progress/phaseMeta";
import { PhaseTag } from "../projects/components/progress/PhaseBadge";
import { LoadingState } from "../../shared/ui/LoadingState";

function sourceLabel(source: string): string {
    return SOURCE_LABEL[source as SourceType] ?? source;
}

function percent(value: number): string {
    return `${(value * 100).toFixed(0)} %`;
}

function Row({ row }: { row: ProgressConflictRow }) {
    const { conflict } = row;
    return (
        <Table.Tr>
            <Table.Td>
                <Stack gap={0}>
                    <Text
                        component={Link}
                        to={`/projects/${row.project_id}`}
                        size="sm"
                        fw={500}
                        style={{ color: "inherit" }}
                    >
                        {row.project_name}
                    </Text>
                    {row.project_number && (
                        <Text size="xs" c="dimmed">
                            {row.project_number}
                        </Text>
                    )}
                </Stack>
            </Table.Td>
            <Table.Td>
                <Stack gap={4}>
                    <PhaseTag phase={conflict.asserted_phase as MainPhase} />
                    <Text size="xs" c="dimmed">
                        {sourceLabel(conflict.source_type)} · {conflict.date_text ?? "ohne Datum"} ·{" "}
                        {percent(conflict.trust)}
                    </Text>
                </Stack>
            </Table.Td>
            <Table.Td>
                <Stack gap={4}>
                    <PhaseTag phase={conflict.contradicted_phase as MainPhase} />
                    {row.contradicted.map((c) => (
                        <Text key={c.observation_id ?? c.source_type} size="xs" c="dimmed">
                            {sourceLabel(c.source_type)} · {c.date_text ?? "ohne Datum"} (
                            {formatAge(c.observed_date)}) · {percent(c.trust ?? 0)}
                            {c.is_lower_bound ? " · Untergrenze" : ""}
                        </Text>
                    ))}
                </Stack>
            </Table.Td>
            <Table.Td>
                <PhaseTag phase={row.computed_phase as MainPhase} />
            </Table.Td>
            <Table.Td>
                {conflict.applied ? (
                    <Badge variant="light" color="gray">
                        übernommen
                    </Badge>
                ) : (
                    <Badge variant="light" color="orange">
                        zurückgehalten
                    </Badge>
                )}
            </Table.Td>
        </Table.Tr>
    );
}

type RecomputeStats = {
    projects: number;
    known_before: number;
    known_after: number;
    phase_changed: number;
};

/**
 * „Alle Projekte neu berechnen“ — the full resync after a deploy that changes
 * the derivation. Single projects resync lazily when read, so list views,
 * filters and data gaps otherwise lag behind for days.
 */
function RecomputeAllCard() {
    const queryClient = useQueryClient();
    const start = useStartProgressRecomputeAll();
    const task = useImportTask({
        onSuccess: (result) => {
            task.reset();
            queryClient.invalidateQueries({ queryKey: queryKeys.projects });
            queryClient.invalidateQueries({ queryKey: ["project-progress"] });
            const stats = result as RecomputeStats | null;
            notifications.show({
                color: "green",
                title: "Planungsstand neu berechnet",
                message: stats
                    ? `${stats.projects} Projekte · bekannt ${stats.known_before} → ${stats.known_after} · ` +
                      `${stats.phase_changed} Phasen geändert`
                    : "Der neue Stand ist sichtbar.",
            });
        },
        onFailure: (error) =>
            notifications.show({
                color: "red",
                title: "Neuberechnung fehlgeschlagen",
                message: error ?? "Unbekannter Fehler — Details im Worker-Log.",
                autoClose: false,
            }),
    });
    const busy = start.isPending || task.taskId !== null;

    const launch = () =>
        start.mutate(undefined, {
            onSuccess: (response) => task.start(response.task_id),
            onError: (error) =>
                notifications.show({
                    color: "red",
                    title: "Neuberechnung konnte nicht gestartet werden",
                    message: error instanceof Error ? error.message : "Unbekannter Fehler.",
                }),
        });

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="sm">
                <Text fw={500}>Alle Projekte neu berechnen</Text>
                <Text size="sm" c="dimmed">
                    Leitet den Planungsstand aller Projekte neu aus den Quellen ab (VIB, FinVe, Infraplan,
                    GVFG, …) und aktualisiert Phase, Baubeginn und Inbetriebnahme in Listen und Filtern. Nötig
                    nach einem Update mit geänderten Berechnungsregeln — sonst rechnet ein Projekt erst neu,
                    wenn es geöffnet wird. Dauert einige Minuten.
                </Text>
                <Group>
                    <Button variant="light" leftSection={<RefreshCw size={16} />} loading={busy} onClick={launch}>
                        Alle Projekte neu berechnen
                    </Button>
                </Group>
                {task.isRunning && (
                    <TaskProgressIndicator
                        progress={task.progress}
                        label={task.progress?.step_label ?? "Wartet auf den Worker …"}
                        warning={task.warning}
                    />
                )}
            </Stack>
        </Paper>
    );
}

function ProgressConflictsAdminPageContent() {
    const { data, isLoading } = useProgressConflicts();
    const rows = data ?? [];
    const heldBack = rows.filter((r) => !r.conflict.applied).length;

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Stack gap={4}>
                    <Title order={1}>Planungsstand · Konflikte</Title>
                    <Text size="sm" c="dimmed">
                        Projekte, bei denen ein neuerer Bericht eine niedrigere Phase meldet als ältere Angaben
                        (z. B. FinVe „Bau“, neuer VIB „Vorplanung“). Ist der neuere Bericht mindestens so
                        vertrauenswürdig wie die älteren Angaben, wird er übernommen, sonst bleibt die höhere Phase
                        stehen. Aufgelöst wird ein Konflikt im Projekt per Phasen-Override oder manueller
                        Beobachtung.
                    </Text>
                </Stack>

                <RecomputeAllCard />

                {heldBack > 0 && (
                    <Alert color="orange" variant="light">
                        {heldBack} neuere Meldung(en) wurden zurückgehalten, weil ältere Angaben vertrauenswürdiger
                        sind – bitte prüfen.
                    </Alert>
                )}

                <Paper withBorder p="var(--card-pad)">
                    {isLoading ? (
                        <LoadingState rows={6} />
                    ) : rows.length === 0 ? (
                        <Text size="sm" c="dimmed">
                            Keine Konflikte.
                        </Text>
                    ) : (
                        <ResponsiveTable minWidth={760} striped highlightOnHover>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Projekt</Table.Th>
                                    <Table.Th>Neuere Meldung</Table.Th>
                                    <Table.Th>Ältere Angaben</Table.Th>
                                    <Table.Th>Planungsstand</Table.Th>
                                    <Table.Th>Status</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {rows.map((row) => (
                                    <Row key={row.project_id} row={row} />
                                ))}
                            </Table.Tbody>
                        </ResponsiveTable>
                    )}
                </Paper>
            </Stack>
        </Container>
    );
}

export default function ProgressConflictsAdminPage() {
    return (
        <RequirePermission
            perm="progress.edit"
            message={'Sie benötigen die Berechtigung „Planungsstand bearbeiten".'}
        >
            <ProgressConflictsAdminPageContent />
        </RequirePermission>
    );
}
