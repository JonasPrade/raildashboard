import { Link } from "react-router-dom";
import { Alert, Badge, Container, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";

import RequirePermission from "../../components/RequirePermission";
import { type ProgressConflictRow, useProgressConflicts } from "../../shared/api/queries";
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
