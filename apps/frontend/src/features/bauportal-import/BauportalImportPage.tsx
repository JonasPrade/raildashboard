import { useMemo } from "react";
import {
    Alert,
    Anchor,
    Badge,
    Button,
    Container,
    Group,
    Loader,
    Select,
    Stack,
    Switch,
    Table,
    Text,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { IconExternalLink, IconRefresh } from "@tabler/icons-react";

import {
    useBauportalEntries,
    useConfirmBauportalMatch,
    useFetchBauportal,
    useProjects,
    type BauportalEntry,
} from "../../shared/api/queries";

const PHASE_LABEL: Record<string, string> = {
    NICHT_GESTARTET: "Nicht gestartet",
    VORPLANUNG: "Vorplanung",
    GENEHMIGUNGSPLANUNG: "Genehmigungsplanung",
    BAU: "Bau",
    IN_BETRIEB: "In Betrieb",
};

const PHASE_COLOR: Record<string, string> = {
    VORPLANUNG: "gray",
    GENEHMIGUNGSPLANUNG: "blue",
    BAU: "orange",
    IN_BETRIEB: "green",
};

function MatchRow({
    entry,
    projectOptions,
}: {
    entry: BauportalEntry;
    projectOptions: { value: string; label: string }[];
}) {
    const confirm = useConfirmBauportalMatch();

    const handleChange = (value: string | null) => {
        confirm.mutate(
            { entryId: entry.id, projectId: value ? Number(value) : null },
            {
                onSuccess: () =>
                    notifications.show({
                        color: "green",
                        title: value ? "Zuordnung gespeichert" : "Zuordnung entfernt",
                        message: entry.shorttitle,
                    }),
                onError: () =>
                    notifications.show({
                        color: "red",
                        title: "Fehler",
                        message: "Die Zuordnung konnte nicht gespeichert werden.",
                    }),
            },
        );
    };

    return (
        <Table.Tr>
            <Table.Td>
                <Stack gap={2}>
                    <Text size="sm" fw={500}>
                        {entry.shorttitle}
                    </Text>
                    {entry.url && (
                        <Anchor href={entry.url} target="_blank" rel="noreferrer" size="xs">
                            <Group gap={4} wrap="nowrap" component="span">
                                <IconExternalLink size={12} />
                                Bauportal
                            </Group>
                        </Anchor>
                    )}
                </Stack>
            </Table.Td>
            <Table.Td>
                {entry.mapped_phase ? (
                    <Badge color={PHASE_COLOR[entry.mapped_phase] ?? "gray"} variant="light">
                        {PHASE_LABEL[entry.mapped_phase] ?? entry.mapped_phase}
                    </Badge>
                ) : (
                    <Text size="xs" c="dimmed" title={entry.status_raw ?? undefined}>
                        kein Beitrag
                    </Text>
                )}
            </Table.Td>
            <Table.Td>
                <Text size="xs" c="dimmed">
                    {entry.projecttime_raw ?? "–"}
                </Text>
            </Table.Td>
            <Table.Td>
                {entry.suggested_project_name ? (
                    <Text size="xs" c="dimmed">
                        ✦ {entry.suggested_project_name}
                    </Text>
                ) : (
                    <Text size="xs" c="dimmed">
                        –
                    </Text>
                )}
            </Table.Td>
            <Table.Td style={{ minWidth: 280 }}>
                <Select
                    placeholder="Projekt zuordnen …"
                    data={projectOptions}
                    value={entry.project_id ? String(entry.project_id) : null}
                    onChange={handleChange}
                    searchable
                    clearable
                    nothingFoundMessage="Kein Projekt gefunden"
                    disabled={confirm.isPending}
                />
            </Table.Td>
        </Table.Tr>
    );
}

export default function BauportalImportPage() {
    const [onlyUnconfirmed, setOnlyUnconfirmed] = useState(false);
    const { data: entries, isLoading } = useBauportalEntries(onlyUnconfirmed);
    const { data: projects } = useProjects();
    const fetchBauportal = useFetchBauportal();

    const projectOptions = useMemo(
        () =>
            (projects ?? [])
                .filter((p) => p.id != null && p.name)
                .map((p) => ({ value: String(p.id), label: p.name as string })),
        [projects],
    );

    const handleFetch = () => {
        fetchBauportal.mutate(undefined, {
            onSuccess: (summary) =>
                notifications.show({
                    color: "green",
                    title: "Bauportal abgerufen",
                    message: `${summary.fetched} Einträge · ${summary.created} neu · ${summary.updated} aktualisiert`,
                }),
            onError: () =>
                notifications.show({
                    color: "red",
                    title: "Abruf fehlgeschlagen",
                    message: "Die Bauportal-API ist nicht erreichbar.",
                }),
        });
    };

    const confirmedCount = (entries ?? []).filter((e) => e.project_id != null).length;

    return (
        <Container size="xl" py="xl">
            <Stack gap="lg">
                <Group justify="space-between" align="flex-start">
                    <Stack gap={4}>
                        <Title order={2}>DB-Bauportal</Title>
                        <Text c="dimmed" size="sm">
                            Aktuellen Bau-/Planungsstand aus der offenen Bauportal-API abrufen und
                            den Projekten zuordnen. Bestätigte Zuordnungen erzeugen automatisch eine
                            abgeleitete Beobachtung (Quelle „Bauportal").
                        </Text>
                    </Stack>
                    <Button
                        leftSection={<IconRefresh size={16} />}
                        onClick={handleFetch}
                        loading={fetchBauportal.isPending}
                    >
                        Bauportal abrufen
                    </Button>
                </Group>

                <Group justify="space-between">
                    <Switch
                        label="Nur offene (ohne Zuordnung)"
                        checked={onlyUnconfirmed}
                        onChange={(e) => setOnlyUnconfirmed(e.currentTarget.checked)}
                    />
                    {entries && (
                        <Text size="sm" c="dimmed">
                            {entries.length} Einträge · {confirmedCount} zugeordnet
                        </Text>
                    )}
                </Group>

                {isLoading ? (
                    <Group justify="center" py="xl">
                        <Loader />
                    </Group>
                ) : !entries || entries.length === 0 ? (
                    <Alert variant="light" title="Keine Daten">
                        Noch keine Bauportal-Einträge. Klicke auf „Bauportal abrufen", um die Liste
                        zu laden.
                    </Alert>
                ) : (
                    <Table.ScrollContainer minWidth={900}>
                        <Table striped highlightOnHover>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Bauportal-Projekt</Table.Th>
                                    <Table.Th>Phase</Table.Th>
                                    <Table.Th>Bauzeitraum</Table.Th>
                                    <Table.Th>Vorschlag</Table.Th>
                                    <Table.Th>Zuordnung</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {entries.map((entry) => (
                                    <MatchRow
                                        key={entry.id}
                                        entry={entry}
                                        projectOptions={projectOptions}
                                    />
                                ))}
                            </Table.Tbody>
                        </Table>
                    </Table.ScrollContainer>
                )}
            </Stack>
        </Container>
    );
}
