import { Link } from "react-router-dom";
import {
    Alert,
    Badge,
    Container,
    Group,
    Paper,
    SimpleGrid,
    Stack,
    Text,
    Title,
} from "@mantine/core";
import { LegalSettingsCard } from "./LegalSettingsCard";
import { useAuth } from "../../lib/auth";
import {
    useDraftProjects,
    useProgressConflicts,
    useUnassignedFinves,
    useUnassignedGvfgEntries,
    useUnassignedInfraplanEntries,
    useUnassignedVibEntries,
    useWorkerHealth,
} from "../../shared/api/queries";

export default function AdminOverviewPage() {
    const { can } = useAuth();
    const canAssignments = can("assignment.manage");
    const canHaushalt = can("haushalt.import");
    const canGvfg = can("gvfg.import");
    const canInfraplan = can("infraplan.import");
    const canVib = can("vib.import");
    const canCreateProject = can("project.create");
    const canDeleteProject = can("project.delete");
    const canProjectGroups = can("projectgroup.create") || can("projectgroup.edit");
    const canUsers = can("user.manage");
    const canRoles = can("role.manage");
    const canProgress = can("progress.edit");
    const canSettings = can("settings.manage");
    const canParliament = can("parliament.import");
    const canMcp = can("mcp.access");
    const hasAnyAdmin =
        canAssignments ||
        canParliament ||
        canHaushalt ||
        canGvfg ||
        canInfraplan ||
        canVib ||
        canCreateProject ||
        canDeleteProject ||
        canProjectGroups ||
        canUsers ||
        canRoles ||
        canProgress ||
        canSettings ||
        canMcp;

    const { data: unassignedFinves } = useUnassignedFinves(canAssignments);
    const { data: unassignedVibEntries } = useUnassignedVibEntries(canAssignments);
    const { data: unassignedGvfgEntries } = useUnassignedGvfgEntries(canAssignments);
    const { data: unassignedInfraplanEntries } = useUnassignedInfraplanEntries(canAssignments);
    const totalUnassigned =
        (unassignedFinves?.length ?? 0) +
        (unassignedVibEntries?.length ?? 0) +
        (unassignedGvfgEntries?.length ?? 0) +
        (unassignedInfraplanEntries?.length ?? 0);

    const { data: progressConflicts } = useProgressConflicts(canProgress);
    const conflictCount = progressConflicts?.length ?? 0;

    const { data: drafts } = useDraftProjects(canCreateProject);
    const draftCount = drafts?.length ?? 0;

    // Polled slowly: the badge is what tells an admin that imports are silently
    // piling up because no worker is running.
    const { data: workerHealth } = useWorkerHealth(canSettings, 60000);
    const workersDown = workerHealth != null && workerHealth.status !== "ok";

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
                <Title order={1}>Administration</Title>

                <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm">
                    <Paper withBorder p="var(--card-pad)">
                        <Link to="/admin/anleitungen" style={{ textDecoration: "none", color: "inherit" }}>
                            <Stack gap={4}>
                                <Text fw={500}>Anleitungen</Text>
                                <Text size="sm" c="dimmed">Workflows für die Datenpflege: Projektfortschritt, Haushalt, Fulda-Runde, Bauportal</Text>
                            </Stack>
                        </Link>
                    </Paper>
                    {canAssignments && (
                        <Paper withBorder p="var(--card-pad)">
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
                                    <Text size="sm" c="dimmed">FinVes, VIB-, GVFG- und Infraplan-Einträge ohne Projektzuordnung</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canHaushalt && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/haushalt-import" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Haushalts-Import</Text>
                                    <Text size="sm" c="dimmed">Jährlichen VWIB-Bundeshaushalt importieren</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canGvfg && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/gvfg-import" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>GVFG-Import</Text>
                                    <Text size="sm" c="dimmed">GVFG-Bundesprogramm (ÖPNV-Förderung) importieren</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canInfraplan && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/infraplan-import" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Infraplan</Text>
                                    <Text size="sm" c="dimmed">Infraplan (Fünfjahresplan Schiene) einlesen, zuordnen, Kennzahlen erfassen und freigeben; Kennzahl-Einstellungen unter „Allgemeines“</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canVib && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/vib-import" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>VIB-Import</Text>
                                    <Text size="sm" c="dimmed">Verkehrsinvestitionsbericht (Schienenwege) importieren</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canProgress && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/finve-progress" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Sammel-FinVe Phasen</Text>
                                    <Text size="sm" c="dimmed">Planungsphase von Sammel-FinVes zuordnen (Lph/EKrG)</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canProgress && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/planungsstand-konflikte" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Group gap={6} align="center">
                                        <Text fw={500}>Planungsstand-Konflikte</Text>
                                        {conflictCount > 0 && (
                                            <Badge color="red" size="xs" variant="filled" circle>
                                                {conflictCount}
                                            </Badge>
                                        )}
                                    </Group>
                                    <Text size="sm" c="dimmed">Neuere Berichte mit niedrigerer Phase als ältere Angaben prüfen; alle Projekte neu berechnen</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canProgress && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/bauportal-import" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>DB-Bauportal</Text>
                                    <Text size="sm" c="dimmed">Bau-/Planungsstand aus der Bauportal-API abrufen & zuordnen</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canProgress && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/media-import" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Medien / Presse</Text>
                                    <Text size="sm" c="dimmed">Presseartikel (URL/Text) per KI auswerten & als Beobachtung übernehmen</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canProgress && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/fulda-import" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Fulda-Runde</Text>
                                    <Text size="sm" c="dimmed">Kleine Anfrage (PDF) per OCR+KI nach Leistungsphase auswerten</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canParliament && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/abgeordnete" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Abgeordnetenstand</Text>
                                    <Text size="sm" c="dimmed">Abgeordnete aus abgeordnetenwatch aktualisieren, Wahlkreis-Zuordnung neu berechnen</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canCreateProject && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/projects/new" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Neues Projekt anlegen</Text>
                                    <Text size="sm" c="dimmed">Wizard: Stammdaten, Geometrie, Eigenschaften, FinVes, VIB</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canCreateProject && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/drafts" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Group gap={6} align="center">
                                        <Text fw={500}>Projekt-Entwürfe</Text>
                                        {draftCount > 0 && (
                                            <Badge color="violet" size="xs" variant="filled" circle>
                                                {draftCount}
                                            </Badge>
                                        )}
                                    </Group>
                                    <Text size="sm" c="dimmed">Begonnene, noch nicht finalisierte Projekte fertigstellen</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canDeleteProject && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/archive" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Archiv</Text>
                                    <Text size="sm" c="dimmed">Ersetzte und überholte Projekte ansehen und wiederherstellen</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canProjectGroups && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/project-groups" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Projektgruppen</Text>
                                    <Text size="sm" c="dimmed">Standardauswahl auf der Karte konfigurieren</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canSettings && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/system" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Group gap={6} align="center">
                                        <Text fw={500}>Systemstatus</Text>
                                        <Badge
                                            color={workersDown ? "red" : "teal"}
                                            size="xs"
                                            variant={workersDown ? "filled" : "light"}
                                        >
                                            {workersDown ? "Worker offline" : "Worker ok"}
                                        </Badge>
                                    </Group>
                                    <Text size="sm" c="dimmed">
                                        Laufen die Hintergrund-Aufträge? Worker, Warteschlange und
                                        was bei einem hängenden Import zu tun ist
                                    </Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canUsers && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/users" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Benutzerverwaltung</Text>
                                    <Text size="sm" c="dimmed">Nutzer anlegen, Rollen ändern, Passwörter setzen</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canMcp && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/api-keys" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>API-Keys & MCP</Text>
                                    <Text size="sm" c="dimmed">Persönliche Keys für KI-Assistenten (Claude Code) anlegen und widerrufen</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                    {canRoles && (
                        <Paper withBorder p="var(--card-pad)">
                            <Link to="/admin/roles" style={{ textDecoration: "none", color: "inherit" }}>
                                <Stack gap={4}>
                                    <Text fw={500}>Rollen & Berechtigungen</Text>
                                    <Text size="sm" c="dimmed">Rollen anlegen und granulare Rechte zuweisen</Text>
                                </Stack>
                            </Link>
                        </Paper>
                    )}
                </SimpleGrid>

                {canSettings && <LegalSettingsCard />}
            </Stack>
        </Container>
    );
}
