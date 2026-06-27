import { useMemo, useState } from "react";
import {
    ActionIcon,
    Alert,
    Badge,
    Button,
    Container,
    FileInput,
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
import { IconTrash, IconUpload } from "@tabler/icons-react";

import {
    useDeleteFuldaEntry,
    useFuldaEntries,
    useParseFulda,
    useProjects,
    useUpdateFuldaEntry,
    type FuldaEntry,
} from "../../shared/api/queries";
import { MAIN_PHASES, MAIN_PHASE_LABEL } from "../projects/components/progress/phaseMeta";

const PHASE_OPTIONS = MAIN_PHASES.map((p) => ({ value: p, label: MAIN_PHASE_LABEL[p] }));

const CATEGORY_LABEL: Record<string, string> = {
    IN_LPH_1_2: "in Lph 1–2",
    IN_LPH_3_4: "in Lph 3–4",
    COMPLETED_LPH_1_2: "Lph 1–2 abgeschlossen",
    COMPLETED_LPH_3_4: "Lph 3–4 abgeschlossen",
};

function FuldaRow({
    entry,
    projectOptions,
}: {
    entry: FuldaEntry;
    projectOptions: { value: string; label: string }[];
}) {
    const update = useUpdateFuldaEntry();
    const remove = useDeleteFuldaEntry();

    const patch = (data: Parameters<typeof update.mutate>[0]["data"]) =>
        update.mutate(
            { entryId: entry.id, data },
            {
                onError: () =>
                    notifications.show({
                        color: "red",
                        title: "Fehler",
                        message: "Änderung konnte nicht gespeichert werden.",
                    }),
            },
        );

    const canConfirm = entry.project_id != null && entry.announced_phase != null;

    return (
        <Table.Tr>
            <Table.Td>
                <Text size="sm" fw={500}>
                    {entry.raw_name}
                </Text>
                {entry.category && (
                    <Text size="xs" c="dimmed">
                        {CATEGORY_LABEL[entry.category] ?? entry.category}
                    </Text>
                )}
            </Table.Td>
            <Table.Td style={{ minWidth: 190 }}>
                <Select
                    data={PHASE_OPTIONS}
                    value={entry.announced_phase}
                    onChange={(v) => patch({ announced_phase: v })}
                    placeholder="Phase"
                    clearable
                />
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
            <Table.Td style={{ minWidth: 260 }}>
                <Select
                    placeholder="Projekt zuordnen …"
                    data={projectOptions}
                    value={entry.project_id ? String(entry.project_id) : null}
                    onChange={(v) => patch({ project_id: v ? Number(v) : null })}
                    searchable
                    clearable
                    nothingFoundMessage="Kein Projekt gefunden"
                />
            </Table.Td>
            <Table.Td>
                <Group gap="xs" wrap="nowrap">
                    <Switch
                        checked={entry.confirmed}
                        disabled={!canConfirm && !entry.confirmed}
                        onChange={(e) => patch({ confirmed: e.currentTarget.checked })}
                        title={canConfirm ? "Übernehmen" : "Phase & Projekt wählen"}
                    />
                    {entry.confirmed && (
                        <Badge color="green" variant="light">
                            aktiv
                        </Badge>
                    )}
                    <ActionIcon
                        variant="subtle"
                        color="red"
                        onClick={() => remove.mutate(entry.id)}
                        title="Eintrag löschen"
                    >
                        <IconTrash size={16} />
                    </ActionIcon>
                </Group>
            </Table.Td>
        </Table.Tr>
    );
}

export default function FuldaImportPage() {
    const [file, setFile] = useState<File | null>(null);
    const [onlyUnconfirmed, setOnlyUnconfirmed] = useState(false);

    const { data: entries, isLoading } = useFuldaEntries(onlyUnconfirmed);
    const { data: projects } = useProjects();
    const parse = useParseFulda();

    const projectOptions = useMemo(
        () =>
            (projects ?? [])
                .filter((p) => p.id != null && p.name)
                .map((p) => ({ value: String(p.id), label: p.name as string })),
        [projects],
    );

    const handleParse = () => {
        if (!file) return;
        parse.mutate(file, {
            onSuccess: (summary) => {
                setFile(null);
                notifications.show({
                    color: "green",
                    title: "Kleine Anfrage ausgewertet",
                    message: `${summary.created} Einträge erkannt (OCR: ${summary.ocr_status})`,
                });
            },
            onError: () =>
                notifications.show({
                    color: "red",
                    title: "Auswertung fehlgeschlagen",
                    message: "Das PDF konnte nicht verarbeitet werden.",
                }),
        });
    };

    return (
        <Container size="xl" py="xl">
            <Stack gap="lg">
                <Stack gap={4}>
                    <Title order={2}>Fulda-Runde</Title>
                    <Text c="dimmed" size="sm">
                        Kleine Anfrage (PDF) hochladen. OCR + KI erkennen die nach Leistungsphase
                        gruppierten Projekte; nach Prüfung & Zuordnung erzeugt das Bestätigen eine
                        Beobachtung (Quelle „Fulda-Runde"), die auch in die Prognose einfließt.
                    </Text>
                </Stack>

                <Group align="flex-end">
                    <FileInput
                        label="Kleine Anfrage (PDF)"
                        placeholder="PDF auswählen"
                        accept="application/pdf"
                        value={file}
                        onChange={setFile}
                        leftSection={<IconUpload size={16} />}
                        style={{ flex: 1, maxWidth: 420 }}
                    />
                    <Button onClick={handleParse} loading={parse.isPending} disabled={!file}>
                        Auswerten
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
                            {entries.length} Einträge
                        </Text>
                    )}
                </Group>

                {isLoading ? (
                    <Group justify="center" py="xl">
                        <Loader />
                    </Group>
                ) : !entries || entries.length === 0 ? (
                    <Alert variant="light" title="Keine Einträge">
                        Noch keine Fulda-Einträge. Lade oben eine Kleine Anfrage hoch.
                    </Alert>
                ) : (
                    <Table.ScrollContainer minWidth={900}>
                        <Table striped highlightOnHover>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Projekt (Roh) · Kategorie</Table.Th>
                                    <Table.Th>Phase</Table.Th>
                                    <Table.Th>Vorschlag</Table.Th>
                                    <Table.Th>Zuordnung</Table.Th>
                                    <Table.Th>Übernehmen</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {entries.map((entry) => (
                                    <FuldaRow
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
