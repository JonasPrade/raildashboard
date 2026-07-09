import { useMemo, useState } from "react";
import {
    ActionIcon,
    Alert,
    Anchor,
    Badge,
    Button,
    Card,
    Container,
    Group,
    Loader,
    Select,
    Stack,
    Switch,
    Text,
    Textarea,
    TextInput,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconExternalLink, IconTrash } from "@tabler/icons-react";

import {
    useDeleteMediaEntry,
    useExtractMedia,
    useMediaEntries,
    useProjects,
    useUpdateMediaEntry,
    type MediaEntry,
} from "../../shared/api/queries";
import { mainPhaseOptions } from "../projects/components/progress/phaseMeta";
import { formatDate } from "../../shared/format";

const PHASE_OPTIONS = mainPhaseOptions();

function MediaCard({
    entry,
    projectOptions,
}: {
    entry: MediaEntry;
    projectOptions: { value: string; label: string }[];
}) {
    const update = useUpdateMediaEntry();
    const remove = useDeleteMediaEntry();

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

    const canConfirm = entry.project_id != null && entry.asserted_phase != null;

    return (
        <Card withBorder padding="md">
            <Stack gap="sm">
                <Group justify="space-between" align="flex-start">
                    <Stack gap={2}>
                        <Group gap="xs">
                            <Text fw={600}>{entry.publication || "Unbekannte Quelle"}</Text>
                            {entry.published_date && (
                                <Text size="xs" c="dimmed">
                                    {formatDate(entry.published_date)}
                                </Text>
                            )}
                            {entry.confirmed && (
                                <Badge color="green" variant="light">
                                    bestätigt
                                </Badge>
                            )}
                        </Group>
                        {entry.url && (
                            <Anchor href={entry.url} target="_blank" rel="noreferrer" size="xs">
                                <Group gap={4} wrap="nowrap" component="span">
                                    <IconExternalLink size={12} />
                                    Artikel öffnen
                                </Group>
                            </Anchor>
                        )}
                    </Stack>
                    <ActionIcon
                        variant="subtle"
                        color="red"
                        onClick={() => remove.mutate(entry.id)}
                        title="Bericht löschen"
                    >
                        <IconTrash size={16} />
                    </ActionIcon>
                </Group>

                {entry.quote && (
                    <Text size="sm" fs="italic" c="dimmed">
                        „{entry.quote}"
                    </Text>
                )}

                <Group grow align="flex-end">
                    <Select
                        label="Phase"
                        placeholder="Phase wählen"
                        data={PHASE_OPTIONS}
                        value={entry.asserted_phase}
                        onChange={(v) => patch({ asserted_phase: v })}
                        clearable
                    />
                    <Select
                        label="Projekt"
                        placeholder="Projekt zuordnen …"
                        data={projectOptions}
                        value={entry.project_id ? String(entry.project_id) : null}
                        onChange={(v) => patch({ project_id: v ? Number(v) : null })}
                        searchable
                        clearable
                        nothingFoundMessage="Kein Projekt gefunden"
                    />
                </Group>

                {entry.suggested_project_name && entry.project_id == null && (
                    <Text size="xs" c="dimmed">
                        ✦ Vorschlag: {entry.suggested_project_name}
                    </Text>
                )}

                <Switch
                    label="Als Beobachtung übernehmen (bestätigt)"
                    checked={entry.confirmed}
                    disabled={!canConfirm && !entry.confirmed}
                    onChange={(e) => patch({ confirmed: e.currentTarget.checked })}
                />
                {!canConfirm && !entry.confirmed && (
                    <Text size="xs" c="dimmed">
                        Phase und Projekt wählen, um den Bericht zu bestätigen.
                    </Text>
                )}
            </Stack>
        </Card>
    );
}

export default function MediaImportPage() {
    const [url, setUrl] = useState("");
    const [text, setText] = useState("");
    const [onlyUnconfirmed, setOnlyUnconfirmed] = useState(false);

    const { data: entries, isLoading } = useMediaEntries(onlyUnconfirmed);
    const { data: projects } = useProjects();
    const extract = useExtractMedia();

    const projectOptions = useMemo(
        () =>
            (projects ?? [])
                .filter((p) => p.id != null && p.name)
                .map((p) => ({ value: String(p.id), label: p.name as string })),
        [projects],
    );

    const handleExtract = () => {
        extract.mutate(
            { url: url.trim() || undefined, text: text.trim() || undefined },
            {
                onSuccess: () => {
                    setUrl("");
                    setText("");
                    notifications.show({
                        color: "green",
                        title: "Entwurf angelegt",
                        message: "Bitte Phase & Projekt prüfen und bestätigen.",
                    });
                },
                onError: () =>
                    notifications.show({
                        color: "red",
                        title: "Extraktion fehlgeschlagen",
                        message: "URL/Text konnte nicht verarbeitet werden.",
                    }),
            },
        );
    };

    return (
        <Container size="md" py="xl">
            <Stack gap="lg">
                <Stack gap={4}>
                    <Title order={2}>Medien / Presse</Title>
                    <Text c="dimmed" size="sm">
                        Artikel-URL oder -Text einfügen. Die KI-Extraktion schlägt Projekt, Phase und
                        ein Zitat vor; nach Prüfung bestätigen erzeugt eine Beobachtung (Quelle
                        „Medien", niedriges Vertrauen).
                    </Text>
                </Stack>

                <Card withBorder padding="md">
                    <Stack gap="sm">
                        <TextInput
                            label="Artikel-URL"
                            placeholder="https://…"
                            value={url}
                            onChange={(e) => setUrl(e.currentTarget.value)}
                        />
                        <Textarea
                            label="… oder Text einfügen"
                            placeholder="Artikeltext hier einfügen"
                            minRows={4}
                            autosize
                            value={text}
                            onChange={(e) => setText(e.currentTarget.value)}
                        />
                        <Group justify="flex-end">
                            <Button
                                onClick={handleExtract}
                                loading={extract.isPending}
                                disabled={!url.trim() && !text.trim()}
                            >
                                Extrahieren & Entwurf anlegen
                            </Button>
                        </Group>
                    </Stack>
                </Card>

                <Group justify="space-between">
                    <Switch
                        label="Nur offene (unbestätigt)"
                        checked={onlyUnconfirmed}
                        onChange={(e) => setOnlyUnconfirmed(e.currentTarget.checked)}
                    />
                    {entries && (
                        <Text size="sm" c="dimmed">
                            {entries.length} Berichte
                        </Text>
                    )}
                </Group>

                {isLoading ? (
                    <Group justify="center" py="xl">
                        <Loader />
                    </Group>
                ) : !entries || entries.length === 0 ? (
                    <Alert variant="light" title="Keine Berichte">
                        Noch keine Medienberichte. Füge oben eine URL oder Text ein.
                    </Alert>
                ) : (
                    <Stack gap="md">
                        {entries.map((entry) => (
                            <MediaCard key={entry.id} entry={entry} projectOptions={projectOptions} />
                        ))}
                    </Stack>
                )}
            </Stack>
        </Container>
    );
}
