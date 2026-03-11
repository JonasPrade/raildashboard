import {
    Alert,
    Badge,
    Card,
    Container,
    Group,
    Loader,
    Stack,
    Switch,
    Text,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useProjectGroups, useUpdateProjectGroup } from "../../shared/api/queries";

export default function ProjectGroupsAdminPage() {
    const { data: groups, isLoading, isError } = useProjectGroups();
    const updateGroup = useUpdateProjectGroup();

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

    return (
        <Container size="md" py="xl">
            <Stack gap="xl">
                <Stack gap="xs">
                    <Title order={2}>Projektgruppen – Standardauswahl</Title>
                    <Text c="dimmed" size="sm">
                        Hier kannst du festlegen, welche Projektgruppen auf der Karte vorausgewählt
                        sind, wenn ein Nutzer die Seite ohne einen gespeicherten Filter öffnet.
                    </Text>
                </Stack>

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
                        {(groups ?? []).map((group) => (
                            <Card key={group.id} withBorder radius="md" padding="md">
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
                                        disabled={updateGroup.isPending}
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
