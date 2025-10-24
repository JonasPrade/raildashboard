import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
    Alert,
    Badge,
    Button,
    Card,
    Container,
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
} from "../../shared/api/queries";
import ProjectEdit, { type ProjectEditFormValues } from "./ProjectEdit";

type RouteParams = {
    projectId?: string;
};

const featureLabels: Array<{ key: keyof Project; label: string }> = [
    { key: "elektrification", label: "Elektrifizierung" },
    { key: "second_track", label: "Zweigleisiger Ausbau" },
    { key: "third_track", label: "Dreigleisiger Ausbau" },
    { key: "fourth_track", label: "Viergleisiger Ausbau" },
    { key: "new_station", label: "Neuer Bahnhof" },
    { key: "platform", label: "Plattformen" },
    { key: "junction_station", label: "Knotenbahnhof" },
    { key: "overtaking_station", label: "Überholbahnhof" },
    { key: "etcs", label: "ETCS" },
    { key: "increase_speed", label: "Geschwindigkeitsanhebung" },
    { key: "effects_passenger_long_rail", label: "Fernverkehr" },
    { key: "effects_passenger_local_rail", label: "Nahverkehr" },
    { key: "effects_cargo_rail", label: "Güterverkehr" },
];

const detailRows: Array<{ label: string; getValue: (project: Project) => string }> = [
    {
        label: "Projektnummer",
        getValue: (project) => project.project_number ?? "–",
    },
    {
        label: "Länge",
        getValue: (project) =>
            project.length !== null && project.length !== undefined
                ? `${project.length.toLocaleString("de-DE")} km`
                : "–",
    },
    {
        label: "Übergeordnetes Projekt",
        getValue: (project) =>
            project.superior_project_id !== null && project.superior_project_id !== undefined
                ? String(project.superior_project_id)
                : "–",
    },
    {
        label: "Ehemalige ID",
        getValue: (project) => (project.old_id ? String(project.old_id) : "–"),
    },
    {
        label: "Ehemalige ID des übergeordneten Projekts",
        getValue: (project) =>
            project.superior_project_old_id ? String(project.superior_project_old_id) : "–",
    },
    {
        label: "Beschreibung",
        getValue: (project) => project.description ?? "Keine Beschreibung hinterlegt.",
    },
    {
        label: "Begründung",
        getValue: (project) => project.justification ?? "Keine Begründung hinterlegt.",
    },
];

function createUpdatePayload(values: ProjectEditFormValues): ProjectUpdatePayload {
    return {
        name: values.name.trim(),
        project_number: values.project_number?.trim() || null,
        description: values.description?.trim() || null,
        justification: values.justification?.trim() || null,
        length: typeof values.length === "number" ? values.length : null,
        elektrification: values.elektrification,
        second_track: values.second_track,
        new_station: values.new_station,
    };
}

export default function ProjectDetail() {
    const params = useParams<RouteParams>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [editOpened, setEditOpened] = useState(false);
    const projectId = Number(params.projectId);

    const isInvalidId = Number.isNaN(projectId);

    const { data, isLoading, isError, error } = useProject(projectId);

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

    const featureBadges = useMemo(() => {
        if (!project) {
            return [];
        }
        return featureLabels.filter(({ key }) => Boolean(project[key]));
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
                        <Button variant="default" component={Link} to="/projects">
                            Zur Projektübersicht
                        </Button>
                        <Button onClick={() => setEditOpened(true)}>Bearbeiten</Button>
                    </Group>
                </Group>

                <Card withBorder radius="md" padding="lg" shadow="xs">
                    <Stack gap="sm">
                        <Title order={4}>Projektdetails</Title>
                        <Stack gap={8}>
                            {detailRows.map(({ label, getValue }) => (
                                <DetailRow key={label} label={label} value={getValue(project)} />
                            ))}
                        </Stack>
                    </Stack>
                </Card>

                <Card withBorder radius="md" padding="lg" shadow="xs">
                    <Stack gap="sm">
                        <Title order={4}>Merkmale</Title>
                        {featureBadges.length === 0 ? (
                            <Text size="sm" c="dimmed">
                                Für dieses Projekt sind keine besonderen Merkmale hinterlegt.
                            </Text>
                        ) : (
                            <Group gap="xs">
                                {featureBadges.map(({ key, label }) => (
                                    <Badge key={String(key)} variant="light" color="blue">
                                        {label}
                                    </Badge>
                                ))}
                            </Group>
                        )}
                    </Stack>
                </Card>

                {project.justification && project.justification.trim() !== "" && (
                    <Card withBorder radius="md" padding="lg" shadow="xs">
                        <Stack gap="sm">
                            <Title order={4}>Begründung</Title>
                            <Text size="sm">{project.justification}</Text>
                        </Stack>
                    </Card>
                )}

                {project.description && project.description.trim() !== "" && (
                    <Card withBorder radius="md" padding="lg" shadow="xs">
                        <Stack gap="sm">
                            <Title order={4}>Beschreibung</Title>
                            <Text size="sm">{project.description}</Text>
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

