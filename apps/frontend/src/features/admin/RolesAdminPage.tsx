import { useState } from "react";
import { Link } from "react-router-dom";
import {
    ActionIcon,
    Alert,
    Anchor,
    Badge,
    Button,
    Container,
    Group,
    Paper,
    Stack,
    Text,
    Title,
    Tooltip,
} from "@mantine/core";
import { ChevronLeft, Pencil, Plus, Trash2 } from "lucide-react";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import RequirePermission from "../../components/RequirePermission";
import { useDeleteRole, useRoles, type Role } from "../../shared/api/queries";
import { RoleFormModal } from "./RoleFormModal";
import { LoadingState } from "../../shared/ui/LoadingState";
import { ErrorState } from "../../shared/ui/ErrorState";

function RolesAdminPageContent() {

    const { data: roles, isLoading, isError, refetch } = useRoles();
    const deleteRole = useDeleteRole();

    const [modalOpened, setModalOpened] = useState(false);
    const [editingRole, setEditingRole] = useState<Role | null>(null);

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
                        <ChevronLeft size={16} />
                        Zurück zur Administration
                    </Group>
                </Anchor>

                <Group justify="space-between" align="flex-start">
                    <Stack gap="xs">
                        <Title order={1}>Rollen & Berechtigungen</Title>
                        <Text c="dimmed" size="sm">
                            Rollen anlegen und ihnen granulare Bearbeitungsrechte zuweisen.
                        </Text>
                    </Stack>
                    <Button onClick={openCreate}>
                        <Plus size={16} /> Neue Rolle
                    </Button>
                </Group>

                {isError && (
                    <ErrorState onRetry={() => void refetch()}>Rollen konnten nicht geladen werden.</ErrorState>
                )}

                {isLoading ? (
                    <LoadingState rows={6} />
                ) : (
                    <Stack gap="sm">
                        {(roles ?? []).map((role) => (
                            <Paper withBorder p="var(--card-pad)" key={role.id}>
                                <Group justify="space-between" align="center">
                                    <Stack gap={2}>
                                        <Group gap="xs" align="center">
                                            <Text size="sm" fw={500}>{role.name}</Text>
                                            {role.is_system && <Badge variant="outline">System</Badge>}
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
                                                <Pencil size={16} />
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
                                                <Trash2 size={16} />
                                            </ActionIcon>
                                        </Tooltip>
                                    </Group>
                                </Group>
                            </Paper>
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

export default function RolesAdminPage() {
    return (
        <RequirePermission
            perm="role.manage"
            message={'Die Rollenverwaltung ist nur mit der Berechtigung „Rollen & Rechte verwalten" zugänglich.'}
        >
            <RolesAdminPageContent />
        </RequirePermission>
    );
}
