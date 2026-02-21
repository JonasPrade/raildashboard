import { useState } from "react";
import {
    Alert,
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
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import { useDeleteUser, useUpdateUserRole, useUsers } from "../../shared/api/queries";
import { CreateUserModal } from "./CreateUserModal";
import { SetPasswordModal } from "./SetPasswordModal";

const ROLE_OPTIONS = [
    { value: "viewer", label: "Viewer" },
    { value: "editor", label: "Editor" },
    { value: "admin", label: "Admin" },
];

export default function UsersPage() {
    const { user: currentUser } = useAuth();
    const [createOpened, { open: openCreate, close: closeCreate }] = useDisclosure(false);
    const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
    const [passwordUserId, setPasswordUserId] = useState<number | null>(null);

    const { data: users, isLoading, isError } = useUsers();
    const updateRole = useUpdateUserRole();
    const deleteUser = useDeleteUser();

    if (currentUser?.role !== "admin") {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    if (isLoading) {
        return (
            <Container size="md" py="xl">
                <Group justify="center">
                    <Loader />
                </Group>
            </Container>
        );
    }

    if (isError) {
        return (
            <Container size="md" py="xl">
                <Alert color="red" variant="light" title="Fehler">
                    Nutzerliste konnte nicht geladen werden.
                </Alert>
            </Container>
        );
    }

    const handleRoleChange = async (userId: number, newRole: string) => {
        try {
            await updateRole.mutateAsync({ userId, role: newRole });
            notifications.show({
                color: "green",
                message: "Rolle aktualisiert.",
            });
        } catch {
            notifications.show({
                color: "red",
                message: "Rolle konnte nicht geändert werden.",
            });
        }
    };

    const handleDelete = async (userId: number, username: string) => {
        try {
            await deleteUser.mutateAsync(userId);
            setConfirmDeleteId(null);
            notifications.show({
                color: "green",
                message: `Nutzer „${username}" wurde gelöscht.`,
            });
        } catch {
            notifications.show({
                color: "red",
                message: "Nutzer konnte nicht gelöscht werden.",
            });
        }
    };

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Group justify="space-between">
                    <Title order={2}>Benutzerverwaltung</Title>
                    <Button onClick={openCreate}>Neuen Nutzer anlegen</Button>
                </Group>

                <Table striped highlightOnHover withTableBorder>
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th>Benutzername</Table.Th>
                            <Table.Th>Rolle</Table.Th>
                            <Table.Th>Erstellt am</Table.Th>
                            <Table.Th>Aktionen</Table.Th>
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        {users?.map((u) => {
                            const isSelf = u.id === currentUser?.id;
                            const isConfirmingDelete = confirmDeleteId === u.id;

                            return (
                                <Table.Tr key={u.id}>
                                    <Table.Td>
                                        <Text fw={isSelf ? 600 : undefined}>
                                            {u.username}
                                            {isSelf && (
                                                <Text span size="xs" c="dimmed" ml={6}>
                                                    (ich)
                                                </Text>
                                            )}
                                        </Text>
                                    </Table.Td>
                                    <Table.Td>
                                        <Select
                                            data={ROLE_OPTIONS}
                                            value={u.role}
                                            onChange={(v) => v && handleRoleChange(u.id, v)}
                                            disabled={isSelf || updateRole.isPending}
                                            allowDeselect={false}
                                            size="xs"
                                            w={120}
                                        />
                                    </Table.Td>
                                    <Table.Td>
                                        <Text size="sm" c="dimmed">
                                            {new Date(u.created_at).toLocaleDateString("de-DE")}
                                        </Text>
                                    </Table.Td>
                                    <Table.Td>
                                        <Group gap="xs">
                                            <Button
                                                size="xs"
                                                variant="subtle"
                                                onClick={() => setPasswordUserId(u.id)}
                                            >
                                                Passwort setzen
                                            </Button>
                                            {!isSelf && (
                                                isConfirmingDelete ? (
                                                    <>
                                                        <Button
                                                            size="xs"
                                                            color="red"
                                                            loading={deleteUser.isPending}
                                                            onClick={() => handleDelete(u.id, u.username)}
                                                        >
                                                            Wirklich löschen
                                                        </Button>
                                                        <Button
                                                            size="xs"
                                                            variant="default"
                                                            onClick={() => setConfirmDeleteId(null)}
                                                        >
                                                            Abbrechen
                                                        </Button>
                                                    </>
                                                ) : (
                                                    <Button
                                                        size="xs"
                                                        variant="subtle"
                                                        color="red"
                                                        onClick={() => setConfirmDeleteId(u.id)}
                                                    >
                                                        Löschen
                                                    </Button>
                                                )
                                            )}
                                        </Group>
                                    </Table.Td>
                                </Table.Tr>
                            );
                        })}
                    </Table.Tbody>
                </Table>
            </Stack>

            <CreateUserModal opened={createOpened} onClose={closeCreate} />
            {passwordUserId !== null && (() => {
                const u = users?.find((u) => u.id === passwordUserId);
                return u ? (
                    <SetPasswordModal
                        opened
                        onClose={() => setPasswordUserId(null)}
                        userId={u.id}
                        username={u.username}
                    />
                ) : null;
            })()}
        </Container>
    );
}
