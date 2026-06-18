import { Link } from "react-router-dom";
import {
    Alert,
    Badge,
    Container,
    Group,
    SimpleGrid,
    Stack,
    Text,
} from "@mantine/core";
import { ChronicleHeadline, ChronicleCard } from "../../components/chronicle";
import { useAuth } from "../../lib/auth";
import { useUnassignedFinves, useUnassignedVibEntries } from "../../shared/api/queries";

export default function AdminOverviewPage() {
    const { can } = useAuth();
    const canAssignments = can("assignment.manage");
    const canHaushalt = can("haushalt.import");
    const canVib = can("vib.import");
    const canCreateProject = can("project.create");
    const canProjectGroups = can("projectgroup.create") || can("projectgroup.edit");
    const canUsers = can("user.manage");
    const canRoles = can("role.manage");
    const hasAnyAdmin =
        canAssignments ||
        canHaushalt ||
        canVib ||
        canCreateProject ||
        canProjectGroups ||
        canUsers ||
        canRoles;

    const { data: unassignedFinves } = useUnassignedFinves(canAssignments);
    const { data: unassignedVibEntries } = useUnassignedVibEntries(canAssignments);
    const totalUnassigned =
        (unassignedFinves?.length ?? 0) + (unassignedVibEntries?.length ?? 0);

    if (!hasAnyAdmin) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Sie haben keine Administrationsrechte.
                </Alert>
            </Container>
        );
    }

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <ChronicleHeadline as="h1">Administration</ChronicleHeadline>

                <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm">
                    {canAssignments && (
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
                    )}
                    {canHaushalt && (
                        <ChronicleCard style={{ textDecoration: "none" }}>
                            <Link to="/admin/haushalt-import" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Haushalts-Import</Text>
                                    <Text size="sm" c="dimmed">Jährlichen VWIB-Bundeshaushalt importieren</Text>
                                </Stack>
                            </Link>
                        </ChronicleCard>
                    )}
                    {canVib && (
                        <ChronicleCard style={{ textDecoration: "none" }}>
                            <Link to="/admin/vib-import" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>VIB-Import</Text>
                                    <Text size="sm" c="dimmed">Verkehrsinvestitionsbericht (Schienenwege) importieren</Text>
                                </Stack>
                            </Link>
                        </ChronicleCard>
                    )}
                    {canCreateProject && (
                        <ChronicleCard style={{ textDecoration: "none" }}>
                            <Link to="/admin/projects/new" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Neues Projekt anlegen</Text>
                                    <Text size="sm" c="dimmed">Wizard: Stammdaten, Geometrie, Eigenschaften, FinVes, VIB</Text>
                                </Stack>
                            </Link>
                        </ChronicleCard>
                    )}
                    {canProjectGroups && (
                        <ChronicleCard style={{ textDecoration: "none" }}>
                            <Link to="/admin/project-groups" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Projektgruppen</Text>
                                    <Text size="sm" c="dimmed">Standardauswahl auf der Karte konfigurieren</Text>
                                </Stack>
                            </Link>
                        </ChronicleCard>
                    )}
                    {canUsers && (
                        <ChronicleCard style={{ textDecoration: "none" }}>
                            <Link to="/admin/users" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Benutzerverwaltung</Text>
                                    <Text size="sm" c="dimmed">Nutzer anlegen, Rollen ändern, Passwörter setzen</Text>
                                </Stack>
                            </Link>
                        </ChronicleCard>
                    )}
                    {canRoles && (
                        <ChronicleCard style={{ textDecoration: "none" }}>
                            <Link to="/admin/roles" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Rollen & Berechtigungen</Text>
                                    <Text size="sm" c="dimmed">Rollen anlegen und granulare Rechte zuweisen</Text>
                                </Stack>
                            </Link>
                        </ChronicleCard>
                    )}
                </SimpleGrid>
            </Stack>
        </Container>
    );
}
