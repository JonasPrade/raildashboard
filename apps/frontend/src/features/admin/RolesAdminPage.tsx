import { useState } from "react";
import { Link } from "react-router-dom";
import {
    ActionIcon,
    Alert,
    Anchor,
    Container,
    Group,
    Loader,
    Stack,
    Text,
    Tooltip,
} from "@mantine/core";
import { IconChevronLeft, IconPencil, IconPlus, IconTrash } from "@tabler/icons-react";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import {
    ChronicleHeadline,
    ChronicleCard,
    ChronicleDataChip,
    ChronicleButton,
} from "../../components/chronicle";
import { useAuth } from "../../lib/auth";
import { useDeleteRole, useRoles, type Role } from "../../shared/api/queries";
import { RoleFormModal } from "./RoleFormModal";

export default function RolesAdminPage() {
    const { can } = useAuth();
    const canManage = can("role.manage");

    const { data: roles, isLoading, isError } = useRoles();
    const deleteRole = useDeleteRole();

    const [modalOpened, setModalOpened] = useState(false);
    const [editingRole, setEditingRole] = useState<Role | null>(null);

    if (!canManage) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Die Rollenverwaltung ist nur mit der Berechtigung „Rollen & Rechte verwalten" zugänglich.
                </Alert>
            </Container>
        );
    }

    const openCreate = () => {
        setEditingRole(null);
        setModalOpened(true);
    };

    const openEdit = (role: Role) => {
        setEditingRole(role);
        setModalOpened(true);
    };

    const handleDelete = (role: Role) => {
        modals.openConfirmModal({
            title: "Rolle löschen",
            children: (
                <Text size="sm">
                    Soll die Rolle „{role.name}" wirklich gelöscht werden? Das ist nur möglich,
                    wenn ihr keine Nutzer mehr zugeordnet sind.
                </Text>
            ),
            labels: { confirm: "Löschen", cancel: "Abbrechen" },
            confirmProps: { color: "red" },
            onConfirm: () => {
                deleteRole.mutate(role.id, {
                    onSuccess: () =>
                        notifications.show({
                            color: "green",
                            title: "Rolle gelöscht",
                            message: `Die Rolle „${role.name}" wurde gelöscht.`,
                        }),
                    onError: () =>
                        notifications.show({
                            color: "red",
                            title: "Fehler",
                            message: "Die Rolle konnte nicht gelöscht werden – sind ihr noch Nutzer zugeordnet?",
                        }),
                });
            },
        });
    };

    return (
        <Container size="md" py="xl">
            <Stack gap="lg">
                <Anchor component={Link} to="/admin" size="sm" c="dimmed">
                    <Group gap={4} align="center">
                        <IconChevronLeft size={14} />
                        Zurück zur Administration
                    </Group>
                </Anchor>

                <Group justify="space-between" align="flex-start">
                    <Stack gap="xs">
                        <ChronicleHeadline as="h1">Rollen & Berechtigungen</ChronicleHeadline>
                        <Text c="dimmed" size="sm">
                            Rollen anlegen und ihnen granulare Bearbeitungsrechte zuweisen.
                        </Text>
                    </Stack>
                    <ChronicleButton onClick={openCreate}>
                        <IconPlus size={16} /> Neue Rolle
                    </ChronicleButton>
                </Group>

                {isError && (
                    <Alert color="red" variant="light" title="Fehler beim Laden">
                        Rollen konnten nicht geladen werden.
                    </Alert>
                )}

                {isLoading ? (
                    <Group justify="center" py="xl">
                        <Loader />
                    </Group>
                ) : (
                    <Stack gap="sm">
                        {(roles ?? []).map((role) => (
                            <ChronicleCard key={role.id}>
                                <Group justify="space-between" align="center">
                                    <Stack gap={2}>
                                        <Group gap="xs" align="center">
                                            <Text size="sm" fw={500}>{role.name}</Text>
                                            {role.is_system && <ChronicleDataChip>System</ChronicleDataChip>}
                                        </Group>
                                        <Text size="xs" c="dimmed">
                                            {role.description || "Keine Beschreibung"}
                                            {" · "}
                                            {role.name === "admin"
                                                ? "alle Rechte"
                                                : `${role.permissions.length} Recht(e)`}
                                        </Text>
                                    </Stack>
                                    <Group gap="xs">
                                        <Tooltip label="Rolle bearbeiten" withArrow>
                                            <ActionIcon
                                                variant="subtle"
                                                color="gray"
                                                onClick={() => openEdit(role)}
                                                aria-label={`${role.name} bearbeiten`}
                                            >
                                                <IconPencil size={18} />
                                            </ActionIcon>
                                        </Tooltip>
                                        <Tooltip
                                            label={role.is_system ? "Systemrollen können nicht gelöscht werden" : "Rolle löschen"}
                                            withArrow
                                        >
                                            <ActionIcon
                                                variant="subtle"
                                                color="red"
                                                onClick={() => handleDelete(role)}
                                                disabled={role.is_system || deleteRole.isPending}
                                                aria-label={`${role.name} löschen`}
                                            >
                                                <IconTrash size={18} />
                                            </ActionIcon>
                                        </Tooltip>
                                    </Group>
                                </Group>
                            </ChronicleCard>
                        ))}

                        {(roles ?? []).length === 0 && (
                            <Alert color="gray" variant="light" title="Keine Rollen">
                                Es sind noch keine Rollen vorhanden.
                            </Alert>
                        )}
                    </Stack>
                )}
            </Stack>

            <RoleFormModal
                opened={modalOpened}
                onClose={() => setModalOpened(false)}
                role={editingRole}
            />
        </Container>
    );
}
