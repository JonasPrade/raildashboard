import { useState } from "react";
import { Link } from "react-router-dom";
import {
    Alert,
    Badge,
    Button,
    Container,
    Group,
    Loader,
    Select,
    SimpleGrid,
    Stack,
    Table,
    Text,
} from "@mantine/core";
import { ChronicleHeadline, ChronicleCard, ChronicleButton } from "../../components/chronicle";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import {
    useDeleteUser,
    useUnassignedFinves,
    useUnassignedVibEntries,
    useUpdateUserRole,
    useUsers,
} from "../../shared/api/queries";
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

    const isAdmin = currentUser?.role === "admin";
    const isEditorOrAdmin = currentUser?.role === "editor" || isAdmin;

    const { data: users, isLoading: usersLoading, isError: usersError } = useUsers();
    const { data: unassignedFinves } = useUnassignedFinves(isEditorOrAdmin);
    const { data: unassignedVibEntries } = useUnassignedVibEntries(isEditorOrAdmin);
    const totalUnassigned =
        (unassignedFinves?.length ?? 0) + (unassignedVibEntries?.length ?? 0);

    const updateRole = useUpdateUserRole();
    const deleteUser = useDeleteUser();

    if (!isEditorOrAdmin) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
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
                                        {new Date(u.created_at).toLocaleDateString("de-DE", { timeZone: "Europe/Berlin" })}
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
                <ChronicleHeadline as="h1">Administration</ChronicleHeadline>

                <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm">
                    <ChronicleCard style={{ textDecoration: "none" }}>
                        <Link to="/admin/unassigned" style={{ textDecoration: "none", color: "inherit" }}>
                            <Stack gap={4}>
                                <Group gap={6} align="center">
                                    <Text fw={500}>Offene Zuordnungen</Text>
                                    {totalUnassigned > 0 && (
                                        <Badge color="red" size="xs" variant="filled" circle>
                                            {totalUnassigned}
                                        </Badge>
                                    )}
                                </Group>
                                <Text size="sm" c="dimmed">FinVes und VIB-Einträge ohne Projektzuordnung</Text>
                            </Stack>
                        </Link>
                    </ChronicleCard>
                    <ChronicleCard style={{ textDecoration: "none" }}>
                        <Link to="/admin/haushalt-import" style={{ textDecoration: "none", color: "inherit" }}>
                            <Stack gap={4}>
                                <Text fw={500}>Haushalts-Import</Text>
                                <Text size="sm" c="dimmed">Jährlichen VWIB-Bundeshaushalt importieren</Text>
                            </Stack>
                        </Link>
                    </ChronicleCard>
                    <ChronicleCard style={{ textDecoration: "none" }}>
                        <Link to="/admin/vib-import" style={{ textDecoration: "none", color: "inherit" }}>
                            <Stack gap={4}>
                                <Text fw={500}>VIB-Import</Text>
                                <Text size="sm" c="dimmed">Verkehrsinvestitionsbericht (Schienenwege) importieren</Text>
                            </Stack>
                        </Link>
                    </ChronicleCard>
                    <ChronicleCard style={{ textDecoration: "none" }}>
                        <Link to="/admin/projects/new" style={{ textDecoration: "none", color: "inherit" }}>
                            <Stack gap={4}>
                                <Text fw={500}>Neues Projekt anlegen</Text>
                                <Text size="sm" c="dimmed">Wizard: Stammdaten, Geometrie, Eigenschaften, FinVes, VIB</Text>
                            </Stack>
                        </Link>
                    </ChronicleCard>
                    <ChronicleCard style={{ textDecoration: "none" }}>
                        <Link to="/admin/project-groups" style={{ textDecoration: "none", color: "inherit" }}>
                            <Stack gap={4}>
                                <Text fw={500}>Projektgruppen</Text>
                                <Text size="sm" c="dimmed">Standardauswahl auf der Karte konfigurieren</Text>
                            </Stack>
                        </Link>
                    </ChronicleCard>
                </SimpleGrid>

                {isAdmin && (
                    <>
                        <Group justify="space-between">
                            <ChronicleHeadline as="h2">Benutzerverwaltung</ChronicleHeadline>
                            <ChronicleButton onClick={openCreate}>Neuen Nutzer anlegen</ChronicleButton>
                        </Group>
                        {renderUsersTable()}
                    </>
                )}
            </Stack>

            {isAdmin && <CreateUserModal opened={createOpened} onClose={closeCreate} />}
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
