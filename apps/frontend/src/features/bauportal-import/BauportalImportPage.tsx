import { useMemo, useState } from "react";
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
    Table,
    Text,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconChecks, IconExternalLink, IconRefresh } from "@tabler/icons-react";

import {
    useBauportalEntries,
    useConfirmAllBauportal,
    useFetchBauportal,
    useProjects,
    useUpdateBauportalEntry,
    type BauportalEntry,
    type Project,
} from "../../shared/api/queries";
import { filterProjectOption } from "../../lib/filterProjectOption";
import CreateDraftProjectModal from "../projects/CreateDraftProjectModal";
import {
    ConfirmBadge,
    MissingProjectAnchor,
    SavingIndicator,
    UnconfirmedFilter,
    usePatchWithToast,
} from "../import-review/shared";
import {
    MAIN_PHASE_COLOR,
    MAIN_PHASE_LABEL,
    type MainPhase,
} from "../projects/components/progress/phaseMeta";

type ProjectOption = { value: string; label: string };

function MatchRow({
    entry,
    projectOptions,
    onCreateDraft,
}: {
    entry: BauportalEntry;
    projectOptions: ProjectOption[];
    onCreateDraft: (entry: BauportalEntry) => void;
}) {
    const update = useUpdateBauportalEntry();
    const patch = usePatchWithToast(update, entry.id);

    const isSuggestion =
        entry.project_id != null &&
        entry.project_id === entry.suggested_project_id &&
        !entry.confirmed;
    const canConfirm = entry.project_id != null;

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
                    <Badge color={MAIN_PHASE_COLOR[entry.mapped_phase as MainPhase] ?? "gray"} variant="light">
                        {MAIN_PHASE_LABEL[entry.mapped_phase as MainPhase] ?? entry.mapped_phase}
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
            <Table.Td style={{ width: "34%" }}>
                <Stack gap={4}>
                    <Select
                        placeholder="Projekt zuordnen …"
                        data={projectOptions}
                        value={entry.project_id ? String(entry.project_id) : null}
                        onChange={(v) => patch({ project_id: v ? Number(v) : null })}
                        searchable
                        clearable
                        filter={filterProjectOption}
                        nothingFoundMessage="Kein Projekt gefunden"
                    />
                    <Group gap="xs" justify="space-between" wrap="nowrap">
                        {isSuggestion ? (
                            <Text size="xs" c="dimmed">
                                ✦ Vorschlag – bitte prüfen
                            </Text>
                        ) : (
                            <span />
                        )}
                        <MissingProjectAnchor onClick={() => onCreateDraft(entry)} />
                    </Group>
                </Stack>
            </Table.Td>
            <Table.Td>
                <Group gap="xs" wrap="nowrap">
                    <ConfirmBadge
                        confirmed={entry.confirmed}
                        canConfirm={canConfirm}
                        onToggle={() => patch({ confirmed: !entry.confirmed })}
                        confirmTitle="Übernehmen / zurücknehmen"
                        blockedTitle="Erst ein Projekt zuordnen"
                    />
                    {update.isPending && <SavingIndicator />}
                </Group>
            </Table.Td>
        </Table.Tr>
    );
}

export default function BauportalImportPage() {
    const [onlyUnconfirmed, setOnlyUnconfirmed] = useState(false);
    const { data: entries, isLoading } = useBauportalEntries(onlyUnconfirmed);
    const { data: projects } = useProjects();
    const fetchBauportal = useFetchBauportal();
    const confirmAll = useConfirmAllBauportal();
    const update = useUpdateBauportalEntry();

    const [draftFor, setDraftFor] = useState<BauportalEntry | null>(null);

    const projectOptions = useMemo<ProjectOption[]>(
        () =>
            (projects ?? [])
                .filter((p) => p.id != null && p.name)
                .map((p) => ({
                    value: String(p.id),
                    label: p.superior_project_id ? `   ↳ ${p.name}` : (p.name as string),
                })),
        [projects],
    );

    const readyCount = useMemo(
        () => (entries ?? []).filter((e) => !e.confirmed && e.project_id != null).length,
        [entries],
    );
    const confirmedCount = (entries ?? []).filter((e) => e.confirmed).length;

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

    const handleConfirmAll = () => {
        confirmAll.mutate(undefined, {
            onSuccess: (res) =>
                notifications.show({
                    color: "green",
                    title: "Übernommen",
                    message: `${res.confirmed} Einträge bestätigt — du kannst Zuordnungen weiterhin anpassen.`,
                }),
            onError: () =>
                notifications.show({
                    color: "red",
                    title: "Fehler",
                    message: "Die Einträge konnten nicht übernommen werden.",
                }),
        });
    };

    // A newly created draft is assigned (unconfirmed) so the editor still reviews it.
    const handleDraftCreated = (entry: BauportalEntry) => (project: Project) => {
        if (project.id == null) return;
        update.mutate({ entryId: entry.id, data: { project_id: project.id } });
    };

    return (
        <Container size="xl" py="xl">
            <Stack gap="lg">
                <Group justify="space-between" align="flex-start">
                    <Stack gap={4}>
                        <Title order={2}>DB-Bauportal</Title>
                        <Text c="dimmed" size="sm">
                            Aktuellen Bau-/Planungsstand aus der offenen Bauportal-API abrufen und
                            den Projekten zuordnen. Der Vorschlag ist bereits vorbelegt — prüfen,
                            ggf. anpassen und übernehmen. Bestätigte Zuordnungen erzeugen eine
                            abgeleitete Beobachtung (Quelle „Bauportal").
                        </Text>
                    </Stack>
                    <Group gap="sm">
                        <Button
                            color="green"
                            leftSection={<IconChecks size={16} />}
                            onClick={handleConfirmAll}
                            loading={confirmAll.isPending}
                            disabled={readyCount === 0}
                            title={
                                readyCount === 0
                                    ? "Keine zugeordneten, offenen Einträge"
                                    : "Alle zugeordneten Einträge übernehmen"
                            }
                        >
                            Alle übernehmen{readyCount > 0 ? ` (${readyCount})` : ""}
                        </Button>
                        <Button
                            leftSection={<IconRefresh size={16} />}
                            onClick={handleFetch}
                            loading={fetchBauportal.isPending}
                            variant="light"
                        >
                            Bauportal abrufen
                        </Button>
                    </Group>
                </Group>

                <Group justify="space-between">
                    <UnconfirmedFilter checked={onlyUnconfirmed} onChange={setOnlyUnconfirmed} />
                    {entries && (
                        <Text size="sm" c="dimmed">
                            {entries.length} Einträge · {confirmedCount} aktiv
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
                        <Table striped highlightOnHover verticalSpacing="sm">
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Bauportal-Projekt</Table.Th>
                                    <Table.Th>Phase</Table.Th>
                                    <Table.Th>Bauzeitraum</Table.Th>
                                    <Table.Th>Zuordnung</Table.Th>
                                    <Table.Th>Übernehmen</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {entries.map((entry) => (
                                    <MatchRow
                                        key={entry.id}
                                        entry={entry}
                                        projectOptions={projectOptions}
                                        onCreateDraft={setDraftFor}
                                    />
                                ))}
                            </Table.Tbody>
                        </Table>
                    </Table.ScrollContainer>
                )}
            </Stack>

            <CreateDraftProjectModal
                opened={draftFor !== null}
                onClose={() => setDraftFor(null)}
                initialName={draftFor?.shorttitle}
                sourceLabel="DB-Bauportal"
                onCreated={draftFor ? handleDraftCreated(draftFor) : () => {}}
            />
        </Container>
    );
}
