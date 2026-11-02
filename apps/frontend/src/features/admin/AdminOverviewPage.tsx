import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
    Alert,
    Anchor,
    Badge,
    Container,
    Group,
    Paper,
    SimpleGrid,
    Stack,
    Text,
    Title,
    UnstyledButton,
} from "@mantine/core";
import { useAuth } from "../../lib/auth";
import {
    useAppSettings,
    useDraftProjects,
    useProgressConflicts,
    useUnassignedFinves,
    useUnassignedGvfgEntries,
    useUnassignedInfraplanEntries,
    useUnassignedVibEntries,
    useRoutineJobs,
    useWorkerHealth,
} from "../../shared/api/queries";
import { LEGAL_SETTINGS_PATH, legalStatusLabel } from "../legal/legal";

type Tile = {
    to: string;
    title: string;
    description: string;
    visible: boolean;
    /** Badges next to the title (counts, worker state). */
    badges?: ReactNode;
    /** Extra line under the description, e.g. the current state. */
    status?: string;
};

type Section = {
    title: string;
    description: string;
    tiles: Tile[];
};

type TodoItem = {
    to: string;
    value: string;
    label: string;
    color: string;
    visible: boolean;
};

function TileCard({ tile }: { tile: Tile }) {
    return (
        <Paper withBorder p="var(--card-pad)">
            <Link to={tile.to} style={{ textDecoration: "none", color: "inherit" }}>
                <Stack gap={4}>
                    <Group gap={6} align="center">
                        <Text fw={500}>{tile.title}</Text>
                        {tile.badges}
                    </Group>
                    <Text size="sm" c="dimmed">{tile.description}</Text>
                    {tile.status && <Text size="xs">{tile.status}</Text>}
                </Stack>
            </Link>
        </Paper>
    );
}

function CountBadge({ count, color = "red" }: { count: number; color?: string }) {
    if (count <= 0) return null;
    return (
        <Badge color={color} size="xs" variant="filled" circle>
            {count}
        </Badge>
    );
}

/**
 * /admin ("Einstellungen" in the header): tiles grouped into sections, with a
 * "Zu erledigen" strip that collects every open count on top. Sections without
 * a single permitted tile disappear.
 */
export default function AdminOverviewPage() {
    const { can } = useAuth();
    const canAssignments = can("assignment.manage");
    const canHaushalt = can("haushalt.import");
    const canGvfg = can("gvfg.import");
    const canInfraplan = can("infraplan.import");
    const canCondition = can("condition.import");
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
        canCondition ||
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
    // Scheduled routine jobs: a failed run, no successful run for twice the
    // interval, or the schedule switched off (feature-routine-abrufe.md, E3).
    const { data: routineJobs } = useRoutineJobs(canSettings, 300000);
    const routineAttention = routineJobs?.needs_attention === true;
    const routineLabel = routineJobs?.enabled === false ? "Zeitplan aus" : "Abrufe prüfen";

    const { data: appSettings } = useAppSettings();

    if (!hasAnyAdmin) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Sie haben keine Administrationsrechte.
                </Alert>
            </Container>
        );
    }

    const todos: TodoItem[] = [
        {
            to: "/admin/unassigned",
            value: String(totalUnassigned),
            label: "Einträge ohne Projekt",
            color: totalUnassigned > 0 ? "var(--idt-danger)" : "inherit",
            visible: canAssignments,
        },
        {
            to: "/admin/planungsstand-konflikte",
            value: String(conflictCount),
            label: "Konflikte im Planungsstand",
            color: conflictCount > 0 ? "var(--idt-danger)" : "inherit",
            visible: canProgress,
        },
        {
            to: "/admin/drafts",
            value: String(draftCount),
            label: "Projekt-Entwürfe offen",
            color: draftCount > 0 ? "var(--accent-primary)" : "inherit",
            visible: canCreateProject,
        },
        {
            to: "/admin/system",
            value: workersDown || routineAttention ? "!" : "ok",
            label: workersDown ? "Worker offline" : routineAttention ? routineLabel : "Worker und Abrufe laufen",
            color:
                workersDown || routineAttention
                    ? "var(--idt-danger)"
                    : "var(--idt-success)",
            visible: canSettings,
        },
    ].filter((item) => item.visible);

    const sections: Section[] = [
        {
            title: "Projekte",
            description: "Projekte anlegen, fertigstellen, archivieren und für die Karte bündeln",
            tiles: [
                {
                    to: "/admin/projects/new",
                    title: "Neues Projekt anlegen",
                    description: "Wizard: Stammdaten, Geometrie, Eigenschaften, FinVes, VIB",
                    visible: canCreateProject,
                },
                {
                    to: "/admin/drafts",
                    title: "Projekt-Entwürfe",
                    description: "Begonnene, noch nicht finalisierte Projekte fertigstellen",
                    visible: canCreateProject,
                    badges: <CountBadge count={draftCount} color="violet" />,
                },
                {
                    to: "/admin/archive",
                    title: "Archiv",
                    description: "Ersetzte und überholte Projekte ansehen und wiederherstellen",
                    visible: canDeleteProject,
                },
                {
                    to: "/admin/project-groups",
                    title: "Projektgruppen",
                    description: "Standardauswahl auf der Karte konfigurieren",
                    visible: canProjectGroups,
                },
            ],
        },
        {
            title: "Zuordnen & prüfen",
            description: "Was nach einem Import offen bleibt",
            tiles: [
                {
                    to: "/admin/unassigned",
                    title: "Offene Zuordnungen",
                    description: "FinVes, VIB-, GVFG- und Infraplan-Einträge ohne Projektzuordnung",
                    visible: canAssignments,
                    badges: <CountBadge count={totalUnassigned} />,
                },
                {
                    to: "/admin/planungsstand-konflikte",
                    title: "Planungsstand-Konflikte",
                    description: "Neuere Berichte mit niedrigerer Phase als ältere Angaben prüfen; alle Projekte neu berechnen",
                    visible: canProgress,
                    badges: <CountBadge count={conflictCount} />,
                },
                {
                    to: "/admin/finve-progress",
                    title: "Sammel-FinVe Phasen",
                    description: "Planungsphase von Sammel-FinVes zuordnen (Lph/EKrG)",
                    visible: canProgress,
                },
            ],
        },
        {
            title: "Finanzierung einlesen",
            description: "Quellen des Bundes zu Geld und Zusagen",
            tiles: [
                {
                    to: "/admin/haushalt-import",
                    title: "Haushalts-Import",
                    description: "Jährlichen VWIB-Bundeshaushalt importieren",
                    visible: canHaushalt,
                },
                {
                    to: "/admin/gvfg-import",
                    title: "GVFG-Import",
                    description: "GVFG-Bundesprogramm (ÖPNV-Förderung) importieren",
                    visible: canGvfg,
                },
                {
                    to: "/admin/infraplan-import",
                    title: "Infraplan",
                    description: "Infraplan (Fünfjahresplan Schiene) einlesen, zuordnen, Kennzahlen erfassen und freigeben; Kennzahl-Einstellungen unter „Allgemeines“",
                    visible: canInfraplan,
                },
                {
                    to: "/admin/vib-import",
                    title: "VIB-Import",
                    description: "Verkehrsinvestitionsbericht (Schienenwege) importieren",
                    visible: canVib,
                },
            ],
        },
        {
            title: "Planungsstand & Zustand",
            description: "Quellen zum Fortschritt der Projekte und zum Netzzustand",
            tiles: [
                {
                    to: "/admin/bauportal-import",
                    title: "DB-Bauportal",
                    description: "Bau-/Planungsstand aus der Bauportal-API abrufen & zuordnen",
                    visible: canProgress,
                },
                {
                    to: "/admin/fulda-import",
                    title: "Fulda-Runde",
                    description: "Kleine Anfrage (PDF) per OCR+KI nach Leistungsphase auswerten",
                    visible: canProgress,
                },
                {
                    to: "/admin/media-import",
                    title: "Medien / Presse",
                    description: "Presseartikel (URL/Text) per KI auswerten & als Beobachtung übernehmen",
                    visible: canProgress,
                },
                {
                    to: "/admin/zustandsbericht",
                    title: "Zustandsbericht",
                    description: "InfraGO-Zustandsbericht anlegen, PDF hochladen, eingelesene Werte prüfen und freigeben",
                    visible: canCondition,
                },
            ],
        },
        {
            title: "Politik",
            description: "Abgeordnete und Wahlkreise",
            tiles: [
                {
                    to: "/admin/abgeordnete",
                    title: "Abgeordnetenstand",
                    description: "Abgeordnete aus abgeordnetenwatch aktualisieren, Wahlkreis-Zuordnung neu berechnen",
                    visible: canParliament,
                },
            ],
        },
        {
            title: "Zugang & Rechte",
            description: "Wer was darf, und Zugänge für KI-Assistenten",
            tiles: [
                {
                    to: "/admin/users",
                    title: "Benutzerverwaltung",
                    description: "Nutzer anlegen, Rollen ändern, Passwörter setzen",
                    visible: canUsers,
                },
                {
                    to: "/admin/roles",
                    title: "Rollen & Berechtigungen",
                    description: "Rollen anlegen und granulare Rechte zuweisen",
                    visible: canRoles,
                },
                {
                    to: "/admin/api-keys",
                    title: "API-Keys & MCP",
                    description: "Persönliche Keys für KI-Assistenten (Claude Code) anlegen und widerrufen",
                    visible: canMcp,
                },
            ],
        },
        {
            title: "Betrieb & Website",
            description: "Technischer Zustand und die Pflichtseiten der Website",
            tiles: [
                {
                    to: "/admin/system",
                    title: "Systemstatus",
                    description: "Worker, Warteschlange, zeitgesteuerte Abrufe und was bei einem hängenden Import zu tun ist",
                    visible: canSettings,
                    badges: (
                        <>
                            <Badge
                                color={workersDown ? "red" : "teal"}
                                size="xs"
                                variant={workersDown ? "filled" : "light"}
                            >
                                {workersDown ? "Worker offline" : "Worker ok"}
                            </Badge>
                            {routineAttention && (
                                <Badge color="red" size="xs" variant="filled">
                                    {routineLabel}
                                </Badge>
                            )}
                        </>
                    ),
                },
                {
                    to: LEGAL_SETTINGS_PATH,
                    title: "Impressum & Datenschutz",
                    description: "Inhalt oder Weiterleitung der beiden Seiten in der Fußzeile",
                    visible: canSettings,
                    status: appSettings ? legalStatusLabel(appSettings) : undefined,
                },
            ],
        },
    ];

    const visibleSections = sections
        .map((section) => ({ ...section, tiles: section.tiles.filter((tile) => tile.visible) }))
        .filter((section) => section.tiles.length > 0);

    return (
        <Container size="lg" py="xl">
            <Stack gap="xl">
                <Group justify="space-between" align="baseline" wrap="wrap" gap="xs">
                    <Title order={1}>Einstellungen</Title>
                    <Anchor component={Link} to="/admin/anleitungen" size="sm">
                        Anleitungen zur Datenpflege →
                    </Anchor>
                </Group>

                {todos.length > 0 && (
                    <Stack gap="xs" component="section" aria-label="Zu erledigen">
                        <Text size="xs" fw={700} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.07em" }}>
                            Zu erledigen
                        </Text>
                        <SimpleGrid
                            cols={{ base: 2, sm: Math.min(todos.length, 4) }}
                            spacing={0}
                            style={{ border: "2px solid var(--border-frame)" }}
                        >
                            {todos.map((item) => (
                                <UnstyledButton
                                    key={item.to}
                                    component={Link}
                                    to={item.to}
                                    p="sm"
                                    style={{ borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)" }}
                                >
                                    <Text fw={700} fz={26} lh={1.1} style={{ color: item.color, fontVariantNumeric: "tabular-nums" }}>
                                        {item.value}
                                    </Text>
                                    <Text size="sm" c="dimmed">{item.label}</Text>
                                </UnstyledButton>
                            ))}
                        </SimpleGrid>
                    </Stack>
                )}

                {visibleSections.map((section) => (
                    <Stack key={section.title} gap="sm" component="section">
                        <Group justify="space-between" align="baseline" wrap="wrap" gap="xs" className="idt-section-head">
                            <Title order={2} className="idt-title-plain">{section.title}</Title>
                            <Text size="sm" c="dimmed">{section.description}</Text>
                        </Group>
                        <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="sm">
                            {section.tiles.map((tile) => (
                                <TileCard key={tile.to + tile.title} tile={tile} />
                            ))}
                        </SimpleGrid>
                    </Stack>
                ))}
            </Stack>
        </Container>
    );
}
