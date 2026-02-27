import { useMemo, useState } from "react";
import { useAuth } from "../../lib/auth";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
    Alert,
    Badge,
    Button,
    Card,
    Collapse,
    Container,
    Grid,
    Group,
    Loader,
    Stack,
    Text,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
    type Project,
    type ProjectUpdatePayload,
    updateProject,
    useProject,
    useProjects,
} from "../../shared/api/queries";
import ProjectEdit, { type ProjectEditFormValues } from "./ProjectEdit";
import ProjectSummaryCard from "./ProjectSummaryCard";
import MapView, { type MapViewProject } from "../map/MapView";
import ProjectHistorySection from "../changelog/ProjectHistorySection";
import ProjectTextsSection from "./ProjectTextsSection";

type RouteParams = {
    projectId?: string;
};

import { trainCategoryLabels, featureGroups } from "./projectFeatureConfig";

// ── Detail rows (Projektstammdaten) ──────────────────────────────────────────
// getValue returning null → Zeile wird nicht dargestellt

const detailRows: Array<{ label: string; getValue: (project: Project) => string | null }> = [
    {
        label: "Projektnummer",
        getValue: (project) => project.project_number ?? null,
    },
    {
        label: "Länge",
        getValue: (project) =>
            project.length !== null && project.length !== undefined
                ? `${project.length.toLocaleString("de-DE")} km`
                : null,
    },
    {
        label: "Übergeordnetes Projekt",
        getValue: (project) =>
            project.superior_project_id !== null && project.superior_project_id !== undefined
                ? String(project.superior_project_id)
                : null,
    },
    {
        label: "Neue Vmax",
        getValue: (project) =>
            project.increase_speed && project.new_vmax !== null && project.new_vmax !== undefined
                ? `${project.new_vmax} km/h`
                : null,
    },
    {
        label: "ETCS-Level",
        getValue: (project) =>
            project.etcs && project.etcs_level !== null && project.etcs_level !== undefined
                ? String(project.etcs_level)
                : null,
    },
    {
        label: "Anzahl Knotenbahnhöfe",
        getValue: (project) =>
            project.junction_station &&
            project.number_junction_station !== null &&
            project.number_junction_station !== undefined
                ? String(project.number_junction_station)
                : null,
    },
    {
        label: "Anzahl Überholbahnhöfe",
        getValue: (project) =>
            project.overtaking_station &&
            project.number_overtaking_station !== null &&
            project.number_overtaking_station !== undefined
                ? String(project.number_overtaking_station)
                : null,
    },
    {
        label: "Anzahl Tankstellen",
        getValue: (project) =>
            (project.filling_stations_efuel ||
                project.filling_stations_h2 ||
                project.filling_stations_diesel) &&
            project.filling_stations_count !== null &&
            project.filling_stations_count !== undefined
                ? String(project.filling_stations_count)
                : null,
    },
];

function createUpdatePayload(values: ProjectEditFormValues): ProjectUpdatePayload {
    return {
        name: values.name.trim(),
        project_number: values.project_number?.trim() || null,
        description: values.description?.trim() || null,
        justification: values.justification?.trim() || null,
        length: typeof values.length === "number" ? values.length : null,
        new_vmax: typeof values.new_vmax === "number" ? values.new_vmax : null,
        etcs_level: typeof values.etcs_level === "number" ? values.etcs_level : null,
        number_junction_station: typeof values.number_junction_station === "number" ? values.number_junction_station : null,
        number_overtaking_station: typeof values.number_overtaking_station === "number" ? values.number_overtaking_station : null,
        filling_stations_count: typeof values.filling_stations_count === "number" ? values.filling_stations_count : null,
        effects_passenger_long_rail: values.effects_passenger_long_rail,
        effects_passenger_local_rail: values.effects_passenger_local_rail,
        effects_cargo_rail: values.effects_cargo_rail,
        nbs: values.nbs,
        abs: values.abs,
        second_track: values.second_track,
        third_track: values.third_track,
        fourth_track: values.fourth_track,
        curve: values.curve,
        increase_speed: values.increase_speed,
        tunnel_structural_gauge: values.tunnel_structural_gauge,
        tilting: values.tilting,
        new_station: values.new_station,
        platform: values.platform,
        junction_station: values.junction_station,
        overtaking_station: values.overtaking_station,
        depot: values.depot,
        level_free_platform_entrance: values.level_free_platform_entrance,
        double_occupancy: values.double_occupancy,
        simultaneous_train_entries: values.simultaneous_train_entries,
        buffer_track: values.buffer_track,
        overpass: values.overpass,
        noise_barrier: values.noise_barrier,
        railroad_crossing: values.railroad_crossing,
        gwb: values.gwb,
        etcs: values.etcs,
        new_estw: values.new_estw,
        new_dstw: values.new_dstw,
        block_increase: values.block_increase,
        station_railroad_switches: values.station_railroad_switches,
        flying_junction: values.flying_junction,
        elektrification: values.elektrification,
        optimised_electrification: values.optimised_electrification,
        charging_station: values.charging_station,
        small_charging_station: values.small_charging_station,
        battery: values.battery,
        h2: values.h2,
        efuel: values.efuel,
        filling_stations_efuel: values.filling_stations_efuel,
        filling_stations_h2: values.filling_stations_h2,
        filling_stations_diesel: values.filling_stations_diesel,
        sgv740m: values.sgv740m,
        sanierung: values.sanierung,
        closure: values.closure,
    };
}

export default function ProjectDetail() {
    const params = useParams<RouteParams>();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const queryClient = useQueryClient();
    const [editOpened, setEditOpened] = useState(false);
    const [subProjectsOpen, setSubProjectsOpen] = useState(false);
    const [historyOpen, setHistoryOpen] = useState(false);
    const { user } = useAuth();
    const canEdit = user !== null && (user.role === "editor" || user.role === "admin");
    const projectId = Number(params.projectId);

    const isInvalidId = Number.isNaN(projectId);

    const { data, isLoading, isError, error } = useProject(projectId);
    const { data: allProjects } = useProjects();

    const mutation = useMutation({
        mutationFn: (values: ProjectEditFormValues) => updateProject(projectId, createUpdatePayload(values)),
        onSuccess: (updatedProject) => {
            queryClient.setQueryData(["project", projectId], updatedProject);
            queryClient.invalidateQueries({ queryKey: ["projects"] });
            setEditOpened(false);
            notifications.show({
                color: "green",
                title: "Projekt aktualisiert",
                message: "Die Projektdaten wurden erfolgreich gespeichert.",
            });
        },
        onError: (mutationError: unknown) => {
            const message =
                mutationError instanceof Error
                    ? mutationError.message
                    : "Die Änderungen konnten nicht gespeichert werden.";
            notifications.show({
                color: "red",
                title: "Speichern fehlgeschlagen",
                message,
            });
        },
    });

    const project = data;

    const mutationErrorMessage = mutation.isError
        ? mutation.error instanceof Error
            ? mutation.error.message
            : "Die Änderungen konnten nicht gespeichert werden."
        : undefined;

    // Übergeordnetes Projekt (falls vorhanden)
    const superiorProject = useMemo(() => {
        if (!project?.superior_project_id || !allProjects) return null;
        return allProjects.find((p) => p.id === project.superior_project_id) ?? null;
    }, [project, allProjects]);

    // Unterprojekte (Projekte die dieses als superior haben)
    const subProjects = useMemo(() => {
        if (!project?.id || !allProjects) return [];
        return allProjects.filter(
            (p) => p.superior_project_id === project.id && typeof p.id === "number",
        );
    }, [project, allProjects]);

    // Projekte für die Detailkarte: Unterprojekte wenn vorhanden, sonst das Projekt selbst
    const MAP_COLOR = "#2563eb";
    const mapProjects = useMemo((): MapViewProject[] => {
        if (subProjects.length > 0) {
            return subProjects
                .filter((p): p is typeof p & { id: number } => typeof p.id === "number")
                .map((p) => ({ ...p, id: p.id, groupColor: MAP_COLOR }));
        }
        if (project && typeof project.id === "number") {
            return [{ ...project, id: project.id, groupColor: MAP_COLOR }];
        }
        return [];
    }, [project, subProjects]);

    // Nur Gruppen mit mindestens einem aktiven Feature
    const activeFeatureGroups = useMemo(() => {
        if (!project) return [];
        return featureGroups
            .map((group) => ({
                groupLabel: group.groupLabel,
                activeFeatures: group.features.filter(({ key }) => Boolean(project[key])),
            }))
            .filter(({ activeFeatures }) => activeFeatures.length > 0);
    }, [project]);

    if (isInvalidId) {
        return (
            <Container size="md" py="xl">
                <Alert color="red" title="Ungültige Projekt-ID" variant="light">
                    Die angeforderte Projektkennung ist ungültig. Bitte überprüfe den Link.
                </Alert>
                <Button mt="md" component={Link} to="/projects">
                    Zur Projektübersicht
                </Button>
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
        const message = error instanceof Error ? error.message : "Das Projekt konnte nicht geladen werden.";
        return (
            <Container size="md" py="xl">
                <Stack gap="md">
                    <Alert color="red" title="Projekt konnte nicht geladen werden" variant="light">
                        {message}
                    </Alert>
                    <Group>
                        <Button variant="default" onClick={() => navigate(-1)}>
                            Zurück
                        </Button>
                        <Button component={Link} to="/projects">
                            Projektübersicht öffnen
                        </Button>
                    </Group>
                </Stack>
            </Container>
        );
    }

    if (!project) {
        return (
            <Container size="md" py="xl">
                <Stack gap="md">
                    <Alert color="yellow" title="Projekt nicht gefunden" variant="light">
                        Das gewünschte Projekt existiert nicht oder wurde entfernt.
                    </Alert>
                    <Button component={Link} to="/projects">
                        Zur Projektübersicht
                    </Button>
                </Stack>
            </Container>
        );
    }

    const visibleDetailRows = detailRows
        .map(({ label, getValue }) => ({ label, value: getValue(project) }))
        .filter(({ value }) => value !== null) as Array<{ label: string; value: string }>;

    return (
        <Container size="lg" py="xl">
            <Stack gap="xl">
                <Group justify="space-between" align="flex-start">
                    <Stack gap={4}>
                        <Group gap="sm">
                            <Title order={2}>{project.name}</Title>
                            {project.project_number && (
                                <Badge color="gray" variant="light">
                                    {project.project_number}
                                </Badge>
                            )}
                        </Group>
                        <Text size="sm" c="dimmed">
                            Projekt-ID: {project.id ?? "–"}
                        </Text>
                    </Stack>
                    <Group gap="sm">
                        <Button variant="default" component={Link} to={`/?view=map${searchParams.get("group") ? `&group=${searchParams.get("group")}` : ""}`}>
                            Zur Karte
                        </Button>
                        <Button variant="default" component={Link} to={`/?view=list${searchParams.get("group") ? `&group=${searchParams.get("group")}` : ""}`}>
                            Zur Projektübersicht
                        </Button>
                        {canEdit && (
                            <Button onClick={() => setEditOpened(true)}>Bearbeiten</Button>
                        )}
                    </Group>
                </Group>

                {/* Zweispaltiges Layout: Details/Beschreibung links, Karte rechts */}
                {mapProjects.length > 0 ? (
                    <Grid gutter="md" align="stretch">
                        <Grid.Col span={{ base: 12, md: 4 }}>
                            <Stack gap="md" style={{ height: "100%" }}>
                                <Card withBorder radius="md" padding="lg" shadow="xs">
                                    <Stack gap="sm">
                                        <Title order={4}>Projektdetails</Title>
                                        {visibleDetailRows.length > 0 && (
                                            <Stack gap={8}>
                                                {visibleDetailRows.map(({ label, value }) => (
                                                    <DetailRow key={label} label={label} value={value} />
                                                ))}
                                            </Stack>
                                        )}
                                        <Text size="xs" fw={600} c="dimmed" tt="uppercase" lts={0.5}>Verkehrsarten</Text>
                                        <Group gap="xs">
                                            {trainCategoryLabels.map(({ key, label, color }) => {
                                                const isActive = Boolean(project[key]);
                                                return (
                                                    <Badge
                                                        key={String(key)}
                                                        variant={isActive ? "light" : "outline"}
                                                        color={isActive ? color : "gray"}
                                                    >
                                                        {label}
                                                    </Badge>
                                                );
                                            })}
                                        </Group>
                                        {activeFeatureGroups.length > 0 && (
                                            <>
                                                <Text size="xs" fw={600} c="dimmed" tt="uppercase" lts={0.5}>Merkmale</Text>
                                                <Stack gap="md">
                                                    {activeFeatureGroups.map(({ groupLabel, activeFeatures }) => (
                                                        <Stack key={groupLabel} gap={6}>
                                                            <Text size="xs" fw={600} c="dimmed">{groupLabel}</Text>
                                                            <Group gap="xs">
                                                                {activeFeatures.map(({ key, label }) => (
                                                                    <Badge key={String(key)} variant="light" color="blue">
                                                                        {label}
                                                                    </Badge>
                                                                ))}
                                                            </Group>
                                                        </Stack>
                                                    ))}
                                                </Stack>
                                            </>
                                        )}
                                    </Stack>
                                </Card>
                                {project.description && project.description.trim() !== "" && (
                                    <Card withBorder radius="md" padding="lg" shadow="xs">
                                        <Stack gap="sm">
                                            <Title order={4}>Beschreibung</Title>
                                            <Text size="sm">{project.description}</Text>
                                        </Stack>
                                    </Card>
                                )}
                            </Stack>
                        </Grid.Col>
                        <Grid.Col span={{ base: 12, md: 8 }}>
                            <Card withBorder radius="md" padding="lg" shadow="xs" style={{ height: "100%" }}>
                                <Stack gap="sm" style={{ height: "100%" }}>
                                    <Title order={4}>
                                        {subProjects.length > 0 ? "Karte – Unterprojekte" : "Karte"}
                                    </Title>
                                    <div style={{ flex: 1, minHeight: 400 }}>
                                        <MapView
                                            projects={mapProjects}
                                            height={500}
                                            clickable={subProjects.length > 0}
                                        />
                                    </div>
                                </Stack>
                            </Card>
                        </Grid.Col>
                    </Grid>
                ) : (
                    <>
                        <Card withBorder radius="md" padding="lg" shadow="xs">
                            <Stack gap="sm">
                                <Title order={4}>Projektdetails</Title>
                                {visibleDetailRows.length > 0 && (
                                    <Stack gap={8}>
                                        {visibleDetailRows.map(({ label, value }) => (
                                            <DetailRow key={label} label={label} value={value} />
                                        ))}
                                    </Stack>
                                )}
                                <Text size="xs" fw={600} c="dimmed" tt="uppercase" lts={0.5}>Verkehrsarten</Text>
                                <Group gap="xs">
                                    {trainCategoryLabels.map(({ key, label, color }) => {
                                        const isActive = Boolean(project[key]);
                                        return (
                                            <Badge
                                                key={String(key)}
                                                variant={isActive ? "light" : "outline"}
                                                color={isActive ? color : "gray"}
                                            >
                                                {label}
                                            </Badge>
                                        );
                                    })}
                                </Group>
                                {activeFeatureGroups.length > 0 && (
                                    <>
                                        <Text size="xs" fw={600} c="dimmed" tt="uppercase" lts={0.5}>Merkmale</Text>
                                        <Stack gap="md">
                                            {activeFeatureGroups.map(({ groupLabel, activeFeatures }) => (
                                                <Stack key={groupLabel} gap={6}>
                                                    <Text size="xs" fw={600} c="dimmed">{groupLabel}</Text>
                                                    <Group gap="xs">
                                                        {activeFeatures.map(({ key, label }) => (
                                                            <Badge key={String(key)} variant="light" color="blue">
                                                                {label}
                                                            </Badge>
                                                        ))}
                                                    </Group>
                                                </Stack>
                                            ))}
                                        </Stack>
                                    </>
                                )}
                            </Stack>
                        </Card>
                        {project.description && project.description.trim() !== "" && (
                            <Card withBorder radius="md" padding="lg" shadow="xs">
                                <Stack gap="sm">
                                    <Title order={4}>Beschreibung</Title>
                                    <Text size="sm">{project.description}</Text>
                                </Stack>
                            </Card>
                        )}
                    </>
                )}

                {/* Texte */}
                <ProjectTextsSection projectId={projectId} canEdit={canEdit} />

                {/* Begründung */}
                {project.justification && project.justification.trim() !== "" && (
                    <Card withBorder radius="md" padding="lg" shadow="xs">
                        <Stack gap="sm">
                            <Title order={4}>Begründung</Title>
                            <Text size="sm">{project.justification}</Text>
                        </Stack>
                    </Card>
                )}

                {/* Übergeordnetes Projekt */}
                {superiorProject && (
                    <Card withBorder radius="md" padding="lg" shadow="xs">
                        <Stack gap="sm">
                            <Title order={4}>Übergeordnetes Projekt</Title>
                            <Card withBorder radius="sm" padding="md">
                                <Stack gap="sm">
                                    <ProjectSummaryCard project={superiorProject} />
                                    <Button
                                        size="xs"
                                        variant="light"
                                        component={Link}
                                        to={`/projects/${superiorProject.id}`}
                                    >
                                        Zum Projekt
                                    </Button>
                                </Stack>
                            </Card>
                        </Stack>
                    </Card>
                )}

                {/* Unterprojekte */}
                {subProjects.length > 0 && (
                    <Card withBorder radius="md" padding="lg" shadow="xs">
                        <Stack gap="sm">
                            <Group justify="space-between" align="center">
                                <Title order={4}>Unterprojekte ({subProjects.length})</Title>
                                <Button
                                    size="xs"
                                    variant="subtle"
                                    color="gray"
                                    onClick={() => setSubProjectsOpen((o) => !o)}
                                >
                                    {subProjectsOpen ? "Ausblenden" : "Anzeigen"}
                                </Button>
                            </Group>
                            <Collapse in={subProjectsOpen}>
                                <Stack gap="sm">
                                    {subProjects.map((sub) => (
                                        <Card key={sub.id} withBorder radius="sm" padding="md">
                                            <Stack gap="sm">
                                                <ProjectSummaryCard project={sub} />
                                                <Button
                                                    size="xs"
                                                    variant="light"
                                                    component={Link}
                                                    to={`/projects/${sub.id}`}
                                                >
                                                    Zum Projekt
                                                </Button>
                                            </Stack>
                                        </Card>
                                    ))}
                                </Stack>
                            </Collapse>
                        </Stack>
                    </Card>
                )}

                

                

                {/* Versionshistorie – nur für eingeloggte Nutzer sichtbar */}
                {user !== null && (
                    <Card withBorder radius="md" padding="lg" shadow="xs">
                        <Stack gap="sm">
                            <Group justify="space-between" align="center">
                                <Title order={4}>Versionshistorie</Title>
                                <Button
                                    size="xs"
                                    variant="subtle"
                                    color="gray"
                                    onClick={() => setHistoryOpen((o) => !o)}
                                >
                                    {historyOpen ? "Ausblenden" : "Anzeigen"}
                                </Button>
                            </Group>
                            <Collapse in={historyOpen}>
                                <ProjectHistorySection projectId={projectId} canEdit={canEdit} />
                            </Collapse>
                        </Stack>
                    </Card>
                )}

            </Stack>

            <ProjectEdit
                project={project}
                opened={editOpened}
                onClose={() => setEditOpened(false)}
                onSubmit={(values) => mutation.mutate(values)}
                isSubmitting={mutation.isPending}
                errorMessage={mutationErrorMessage}
            />
        </Container>
    );
}

type DetailRowProps = {
    label: string;
    value: string;
};

function DetailRow({ label, value }: DetailRowProps) {
    return (
        <Group gap="md" align="flex-start">
            <Text fw={500} style={{ minWidth: 200 }}>
                {label}
            </Text>
            <Text size="sm">{value}</Text>
        </Group>
    );
}
