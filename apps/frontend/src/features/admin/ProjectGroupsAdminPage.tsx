import { useMemo, useState } from "react";
import {
    ActionIcon,
    Alert,
    Badge,
    Button,
    Container,
    Group,
    Paper,
    SegmentedControl,
    Stack,
    Switch,
    Text,
    TextInput,
    Title,
    Tooltip,
} from "@mantine/core";
import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import {
    useProjectGroups,
    useUpdateProjectGroup,
    useDeleteProjectGroup,
    useAppSettings,
    useUpdateAppSettings,
    type MapGroupMode,
    type ProjectGroup,
} from "../../shared/api/queries";
import { ProjectGroupFormModal } from "./ProjectGroupFormModal";
import { LoadingState } from "../../shared/ui/LoadingState";
import { ErrorState } from "../../shared/ui/ErrorState";

const MODE_DATA: { value: MapGroupMode; label: string; description: string }[] = [
    {
        value: "preconfigured",
        label: "Vorkonfiguriert",
        description: "Nur die unten markierten Gruppen werden beim Öffnen der Karte vorausgewählt.",
    },
    {
        value: "all",
        label: "Alle anzeigen",
        description: "Alle sichtbaren Gruppen werden beim Öffnen der Karte angezeigt.",
    },
];

export default function ProjectGroupsAdminPage() {
    const { data: groups, isLoading, isError, refetch } = useProjectGroups();
    const { data: appSettings } = useAppSettings();
    const updateGroup = useUpdateProjectGroup();
    const deleteGroup = useDeleteProjectGroup();
    const updateSettings = useUpdateAppSettings();

    const [modalOpened, setModalOpened] = useState(false);
    const [editingGroup, setEditingGroup] = useState<ProjectGroup | null>(null);
    const [search, setSearch] = useState("");

    const currentMode: MapGroupMode = appSettings?.map_group_mode ?? "preconfigured";

    const openCreate = () => {
        setEditingGroup(null);
        setModalOpened(true);
    };

    const openEdit = (group: ProjectGroup) => {
        setEditingGroup(group);
        setModalOpened(true);
    };

    const handleModeChange = (value: string) => {
        updateSettings.mutate({ map_group_mode: value as MapGroupMode }, {
            onError: () =>
                notifications.show({
                    color: "red",
                    title: "Fehler",
                    message: "Anzeigemodus konnte nicht gespeichert werden.",
                }),
        });
    };

    const handleToggle = (
        groupId: number,
        field: "is_visible" | "is_default_selected",
        checked: boolean,
    ) => {
        const errorMessages = {
            is_visible: "Sichtbarkeit konnte nicht gespeichert werden.",
            is_default_selected: "Standardauswahl konnte nicht gespeichert werden.",
        };
        updateGroup.mutate(
            { groupId, [field]: checked },
            {
                onError: () =>
                    notifications.show({
                        color: "red",
                        title: "Fehler",
                        message: errorMessages[field],
                    }),
            },
        );
    };

    const handleDelete = (group: ProjectGroup) => {
        modals.openConfirmModal({
            title: "Projektgruppe löschen",
            children: (
                <Text size="sm">
                    Soll die Projektgruppe „{group.name}" wirklich gelöscht werden? Die
                    zugeordneten Projekte bleiben erhalten, nur die Zuordnung zur Gruppe wird
                    entfernt.
                </Text>
            ),
            labels: { confirm: "Löschen", cancel: "Abbrechen" },
            confirmProps: { color: "red" },
            onConfirm: () => {
                deleteGroup.mutate(group.id!, {
                    onSuccess: () =>
                        notifications.show({
                            color: "green",
                            title: "Gruppe gelöscht",
                            message: `Die Projektgruppe „${group.name}" wurde gelöscht.`,
                        }),
                    onError: () =>
                        notifications.show({
                            color: "red",
                            title: "Fehler",
                            message: "Die Gruppe konnte nicht gelöscht werden.",
                        }),
                });
            },
        });
    };

    const activeMode = MODE_DATA.find((m) => m.value === currentMode);
    const sortedGroups = useMemo(
        () =>
            [...(groups ?? [])].sort(
                (a, b) =>
                    Number(b.is_visible) - Number(a.is_visible) ||
                    Number(b.is_default_selected) - Number(a.is_default_selected),
            ),
        [groups],
    );
    const filteredGroups = useMemo(() => {
        const query = search.trim().toLowerCase();
        if (!query) return sortedGroups;
        return sortedGroups.filter(
            (group) =>
                group.name.toLowerCase().includes(query) ||
                (group.short_name ?? "").toLowerCase().includes(query),
        );
    }, [sortedGroups, search]);

    return (
        <Container size="md" py="xl">
            <Stack gap="xl">
                <Group justify="space-between" align="flex-start">
                    <Stack gap="xs">
                        <Title order={1}>Projektgruppen – Kartenansicht</Title>
                        <Text c="dimmed" size="sm">
                            Projektgruppen verwalten sowie Standardauswahl auf Karte
                        </Text>
                        <Text c="dimmed" size="sm">
                            Lege fest, welche Projektgruppen auf der Karte angezeigt und vorausgewählt werden.
                        </Text>
                    </Stack>
                    <Button onClick={openCreate}>
                        <Plus size={16} /> Neue Gruppe
                    </Button>
                </Group>

                <Paper withBorder p="var(--card-pad)">
                    <Stack gap="sm">
                        <Text size="sm" fw={500}>Anzeigemodus</Text>
                        <SegmentedControl
                            value={currentMode}
                            onChange={handleModeChange}
                            disabled={updateSettings.isPending}
                            data={MODE_DATA.map((m) => ({ value: m.value, label: m.label }))}
                        />
                        {activeMode && (
                            <Text size="xs" c="dimmed">{activeMode.description}</Text>
                        )}
                    </Stack>
                </Paper>

                {isError && (
                    <ErrorState onRetry={() => void refetch()}>Projektgruppen konnten nicht geladen werden.</ErrorState>
                )}

                {isLoading ? (
                    <LoadingState rows={6} />
                ) : (
                    <Stack gap="sm">
                        {sortedGroups.length > 0 && (
                            <TextInput
                                placeholder="Projektgruppe nach Name oder Kürzel suchen …"
                                leftSection={<Search size={16} />}
                                value={search}
                                onChange={(e) => setSearch(e.currentTarget.value)}
                                aria-label="Projektgruppen durchsuchen"
                            />
                        )}
                        {/* Column headers */}
                        {filteredGroups.length > 0 && (
                            <Group justify="flex-end" gap="xl" pr={4}>
                                <Tooltip label={"Gruppe auf der Karte anzeigen"} withArrow>
                                    <Text size="xs" c="dimmed" fw={500} style={{ minWidth: 80, textAlign: "center" }}>
                                        Sichtbar
                                    </Text>
                                </Tooltip>
                                <Tooltip label={"Gruppe beim Öffnen vorauswählen (nur im Modus Vorkonfiguriert)"} withArrow>
                                    <Text size="xs" c="dimmed" fw={500} style={{ minWidth: 80, textAlign: "center" }}>
                                        Vorausgewählt
                                    </Text>
                                </Tooltip>
                            </Group>
                        )}

                        {filteredGroups.map((group) => (
                            <Paper withBorder p="var(--card-pad)" key={group.id}>
                                <Group justify="space-between" align="center">
                                    <Group gap="sm" align="center" style={{ opacity: group.is_visible ? 1 : 0.4 }}>
                                        <span
                                            aria-hidden
                                            style={{
                                                display: "inline-block",
                                                width: 14,
                                                height: 14,
                                                borderRadius: "50%",
                                                backgroundColor: group.color,
                                                flexShrink: 0,
                                            }}
                                        />
                                        <Stack gap={2}>
                                            <Text size="sm" fw={500}>{group.name}</Text>
                                            <Text size="xs" c="dimmed">
                                                {group.short_name} · {group.projects?.length ?? 0} Projekte
                                            </Text>
                                        </Stack>
                                        {!group.is_visible && (
                                            <Badge variant="outline">Ausgeblendet</Badge>
                                        )}
                                        {group.is_visible && group.is_default_selected && (
                                            <Badge variant="outline">Vorausgewählt</Badge>
                                        )}
                                    </Group>

                                    <Group gap="xl" align="center">
                                        <Switch
                                            checked={group.is_visible}
                                            onChange={(e) => handleToggle(group.id!, "is_visible", e.currentTarget.checked)}
                                            disabled={updateGroup.isPending}
                                            aria-label={`${group.name} auf Karte anzeigen`}
                                            style={{ minWidth: 80, display: "flex", justifyContent: "center" }}
                                        />
                                        <Switch
                                            checked={group.is_default_selected}
                                            onChange={(e) => handleToggle(group.id!, "is_default_selected", e.currentTarget.checked)}
                                            disabled={updateGroup.isPending || !group.is_visible || currentMode === "all"}
                                            aria-label={`${group.name} als Standard vorauswählen`}
                                            style={{ minWidth: 80, display: "flex", justifyContent: "center" }}
                                        />
                                        <Group gap="xs">
                                            <Tooltip label="Gruppe bearbeiten" withArrow>
                                                <ActionIcon
                                                    variant="subtle"
                                                    color="gray"
                                                    onClick={() => openEdit(group)}
                                                    aria-label={`${group.name} bearbeiten`}
                                                >
                                                    <Pencil size={16} />
                                                </ActionIcon>
                                            </Tooltip>
                                            <Tooltip label="Gruppe löschen" withArrow>
                                                <ActionIcon
                                                    variant="subtle"
                                                    color="red"
                                                    onClick={() => handleDelete(group)}
                                                    disabled={deleteGroup.isPending}
                                                    aria-label={`${group.name} löschen`}
                                                >
                                                    <Trash2 size={16} />
                                                </ActionIcon>
                                            </Tooltip>
                                        </Group>
                                    </Group>
                                </Group>
                            </Paper>
                        ))}

                        {sortedGroups.length === 0 && (
                            <Alert color="gray" variant="light" title="Keine Projektgruppen">
                                Es sind noch keine Projektgruppen vorhanden.
                            </Alert>
                        )}

                        {sortedGroups.length > 0 && filteredGroups.length === 0 && (
                            <Alert color="gray" variant="light" title="Keine Treffer">
                                Keine Projektgruppe passt zur Suche „{search}".
                            </Alert>
                        )}
                    </Stack>
                )}
            </Stack>

            <ProjectGroupFormModal
                opened={modalOpened}
                onClose={() => setModalOpened(false)}
                group={editingGroup}
            />
        </Container>
    );
}
