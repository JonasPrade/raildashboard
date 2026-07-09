import { useState } from "react";
import { Link } from "react-router-dom";
import {
    Alert,
    Anchor,
    Button,
    Container,
    Group,
    Loader,
    Select,
    Stack,
    Table,
    Text,
} from "@mantine/core";
import { IconChevronLeft, IconPencil } from "@tabler/icons-react";
import { ChronicleHeadline, ChronicleButton } from "../../components/chronicle";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import RequirePermission from "../../components/RequirePermission";
import {
    useDeleteUser,
    useRoles,
    useUpdateUserRole,
    useUsers,
} from "../../shared/api/queries";
import { formatDateNumeric } from "../../shared/format";
import { CreateUserModal } from "./CreateUserModal";
import { EditUserModal } from "./EditUserModal";
import { SetPasswordModal } from "./SetPasswordModal";

function UsersPageContent() {
    const { user: currentUser } = useAuth();
    const [createOpened, { open: openCreate, close: closeCreate }] = useDisclosure(false);
    const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
    const [passwordUserId, setPasswordUserId] = useState<number | null>(null);
    const [editUserId, setEditUserId] = useState<number | null>(null);

    const { data: users, isLoading: usersLoading, isError: usersError } = useUsers();
    const { data: roles } = useRoles();
    const roleOptions = (roles ?? []).map((r) => ({ value: r.name, label: r.name }));

    const updateRole = useUpdateUserRole();
    const deleteUser = useDeleteUser();

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

    const renderUsersTable = () => {
        if (usersLoading) {
            return <Group justify="center" py="md"><Loader /></Group>;
        }
        if (usersError) {
            return (
                <Alert color="red" variant="light" title="Fehler">
                    Nutzerliste konnte nicht geladen werden.
                </Alert>
            );
        }
        return (
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
                                        data={roleOptions}
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
                                        {formatDateNumeric(u.created_at)}
                                    </Text>
                                </Table.Td>
                                <Table.Td>
                                    <Group gap="xs">
                                        <Button
                                            size="xs"
                                            variant="subtle"
                                            leftSection={<IconPencil size={14} />}
                                            onClick={() => setEditUserId(u.id)}
                                        >
                                            Bearbeiten
                                        </Button>
                                        <Button
                                            size="xs"
                                            variant="subtle"
                                            onClick={() => setPasswordUserId(u.id)}
                                        >
                                            Passwort setzen
                                        </Button>
                                        {!isSelf && (isConfirmingDelete ? (
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
                                        ))}
                                    </Group>
                                </Table.Td>
                            </Table.Tr>
                        );
                    })}
                </Table.Tbody>
            </Table>
        );
    };

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Anchor component={Link} to="/admin" size="sm" c="dimmed">
                    <Group gap={4} align="center">
                        <IconChevronLeft size={14} />
                        Zurück zur Administration
                    </Group>
                </Anchor>

                <Group justify="space-between">
                    <ChronicleHeadline as="h1">Benutzerverwaltung</ChronicleHeadline>
                    <ChronicleButton onClick={openCreate}>Neuen Nutzer anlegen</ChronicleButton>
                </Group>
                {renderUsersTable()}
            </Stack>

            <CreateUserModal opened={createOpened} onClose={closeCreate} />
            {editUserId !== null && (() => {
                const u = users?.find((u) => u.id === editUserId);
                return u ? (
                    <EditUserModal
                        opened
                        onClose={() => setEditUserId(null)}
                        user={{ id: u.id, username: u.username, role: u.role }}
                        isSelf={u.id === currentUser?.id}
                    />
                ) : null;
            })()}
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

export default function UsersPage() {
    return (
        <RequirePermission
            perm="user.manage"
            message={'Die Benutzerverwaltung ist nur für Administratoren zugänglich.'}
        >
            <UsersPageContent />
        </RequirePermission>
    );
}
