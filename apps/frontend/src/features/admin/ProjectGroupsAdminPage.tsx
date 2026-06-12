import { useMemo, useState } from "react";
import {
    ActionIcon,
    Alert,
    Container,
    Group,
    Loader,
    SegmentedControl,
    Stack,
    Switch,
    Text,
    Tooltip,
} from "@mantine/core";
import { IconPencil, IconPlus, IconTrash } from "@tabler/icons-react";
import { modals } from "@mantine/modals";
import { ChronicleHeadline, ChronicleCard, ChronicleDataChip, ChronicleButton } from "../../components/chronicle";
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
    const { data: groups, isLoading, isError } = useProjectGroups();
    const { data: appSettings } = useAppSettings();
    const updateGroup = useUpdateProjectGroup();
    const deleteGroup = useDeleteProjectGroup();
    const updateSettings = useUpdateAppSettings();

    const [modalOpened, setModalOpened] = useState(false);
    const [editingGroup, setEditingGroup] = useState<ProjectGroup | null>(null);

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
        updateSettings.mutate(value as MapGroupMode, {
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

    return (
        <Container size="md" py="xl">
            <Stack gap="xl">
                <Group justify="space-between" align="flex-start">
                    <Stack gap="xs">
                        <ChronicleHeadline as="h1">Projektgruppen – Kartenansicht</ChronicleHeadline>
                        <Text c="dimmed" size="sm">
                            Lege fest, welche Projektgruppen auf der Karte angezeigt und vorausgewählt werden.
                        </Text>
                    </Stack>
                    <ChronicleButton onClick={openCreate}>
                        <IconPlus size={16} /> Neue Gruppe
                    </ChronicleButton>
                </Group>

                <ChronicleCard>
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
                </ChronicleCard>

                {isError && (
                    <Alert color="red" variant="light" title="Fehler beim Laden">
                        Projektgruppen konnten nicht geladen werden.
                    </Alert>
                )}

                {isLoading ? (
                    <Group justify="center" py="xl">
                        <Loader />
                    </Group>
                ) : (
                    <Stack gap="sm">
                        {/* Column headers */}
                        {sortedGroups.length > 0 && (
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

                        {sortedGroups.map((group) => (
                            <ChronicleCard key={group.id}>
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
                                            <ChronicleDataChip>Ausgeblendet</ChronicleDataChip>
                                        )}
                                        {group.is_visible && group.is_default_selected && (
                                            <ChronicleDataChip>Vorausgewählt</ChronicleDataChip>
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
                                                    <IconPencil size={18} />
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
                                                    <IconTrash size={18} />
                                                </ActionIcon>
                                            </Tooltip>
                                        </Group>
                                    </Group>
                                </Group>
                            </ChronicleCard>
                        ))}

                        {sortedGroups.length === 0 && (
                            <Alert color="gray" variant="light" title="Keine Projektgruppen">
                                Es sind noch keine Projektgruppen vorhanden.
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
