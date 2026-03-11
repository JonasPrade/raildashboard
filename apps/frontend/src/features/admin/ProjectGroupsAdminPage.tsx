import {
    Alert,
    Badge,
    Card,
    Container,
    Divider,
    Group,
    Loader,
    SegmentedControl,
    Stack,
    Switch,
    Text,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
    useProjectGroups,
    useUpdateProjectGroup,
    useAppSettings,
    useUpdateAppSettings,
    type MapGroupMode,
} from "../../shared/api/queries";

const MODE_DATA: { value: MapGroupMode; label: string; description: string }[] = [
    {
        value: "preconfigured",
        label: "Vorkonfiguriert",
        description: "Nur die unten markierten Gruppen werden beim Öffnen der Karte vorausgewählt.",
    },
    {
        value: "all",
        label: "Alle anzeigen",
        description: "Alle Projekte werden angezeigt, unabhängig von Gruppenfiltern.",
    },
];

export default function ProjectGroupsAdminPage() {
    const { data: groups, isLoading, isError } = useProjectGroups();
    const { data: appSettings } = useAppSettings();
    const updateGroup = useUpdateProjectGroup();
    const updateSettings = useUpdateAppSettings();

    const currentMode: MapGroupMode = appSettings?.map_group_mode ?? "preconfigured";

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

    const handleToggle = (groupId: number, checked: boolean) => {
        updateGroup.mutate(
            { groupId, isDefaultSelected: checked },
            {
                onError: () =>
                    notifications.show({
                        color: "red",
                        title: "Fehler",
                        message: "Standardauswahl konnte nicht gespeichert werden.",
                    }),
            },
        );
    };

    const activeMode = MODE_DATA.find((m) => m.value === currentMode);

    return (
        <Container size="md" py="xl">
            <Stack gap="xl">
                <Stack gap="xs">
                    <Title order={2}>Projektgruppen – Kartenansicht</Title>
                    <Text c="dimmed" size="sm">
                        Lege fest, welche Projektgruppen beim Öffnen der Karte angezeigt werden.
                    </Text>
                </Stack>

                <Card withBorder radius="md" padding="md">
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
                </Card>

                <Divider label="Vorkonfigurierte Gruppen" labelPosition="center" />

                <Text size="sm" c={currentMode === "all" ? "dimmed" : undefined}>
                    {currentMode === "all"
                        ? "Nicht aktiv — wird nur im Modus „Vorkonfiguriert" verwendet."
                        : "Wähle die Gruppen, die beim Öffnen der Karte vorausgewählt sein sollen."}
                </Text>

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
                        {[...(groups ?? [])].sort((a, b) => Number(b.is_default_selected) - Number(a.is_default_selected)).map((group) => (
                            <Card key={group.id} withBorder radius="md" padding="md"
                                style={{ opacity: currentMode === "all" ? 0.5 : 1 }}>
                                <Group justify="space-between" align="center">
                                    <Group gap="sm" align="center">
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
                                            <Text size="xs" c="dimmed">{group.short_name} · {group.projects?.length ?? 0} Projekte</Text>
                                        </Stack>
                                        {group.is_default_selected && (
                                            <Badge size="xs" color="blue" variant="light">
                                                Vorausgewählt
                                            </Badge>
                                        )}
                                    </Group>
                                    <Switch
                                        checked={group.is_default_selected}
                                        onChange={(e) => handleToggle(group.id!, e.currentTarget.checked)}
                                        disabled={updateGroup.isPending || currentMode === "all"}
                                        aria-label={`${group.name} als Standard vorauswählen`}
                                    />
                                </Group>
                            </Card>
                        ))}
                        {(groups ?? []).length === 0 && (
                            <Alert color="gray" variant="light" title="Keine Projektgruppen">
                                Es sind noch keine Projektgruppen vorhanden.
                            </Alert>
                        )}
                    </Stack>
                )}
            </Stack>
        </Container>
    );
}
