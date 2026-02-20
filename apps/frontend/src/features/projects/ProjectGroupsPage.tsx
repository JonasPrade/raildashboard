import { useEffect, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
    Alert,
    Badge,
    Card,
    Container,
    Group,
    Loader,
    Select,
    SimpleGrid,
    Stack,
    Text,
    Title,
} from "@mantine/core";

import { useProjectGroups, type Project, type ProjectGroup } from "../../shared/api/queries";

const hasNumericId = (
    group: ProjectGroup,
): group is ProjectGroup & { id: number } => typeof group.id === "number";

export default function ProjectGroupsPage() {
    const { data, isLoading, isError, error } = useProjectGroups();
    const [searchParams, setSearchParams] = useSearchParams();

    const groups = useMemo(() => (data ?? []).filter(hasNumericId), [data]);

    const selectedGroupId = useMemo(() => {
        const param = searchParams.get("group");
        if (!param) return null;
        const id = Number(param.split(",")[0]);
        return Number.isFinite(id) ? id : null;
    }, [searchParams]);

    useEffect(() => {
        if (groups.length === 0) return;
        if (selectedGroupId !== null && groups.some((g) => g.id === selectedGroupId)) return;
        setSearchParams((prev) => {
            prev.set("group", String(groups[0]!.id));
            return prev;
        }, { replace: true });
    }, [groups, selectedGroupId, setSearchParams]);

    const selectedGroup = selectedGroupId
        ? groups.find((group) => group.id === selectedGroupId)
        : undefined;

    const projects = (selectedGroup?.projects ?? []).filter(Boolean) as Project[];

    const selectData = groups.map((group) => ({
        value: String(group.id),
        label: group.name,
    }));

    const handleGroupChange = (value: string | null) => {
        setSearchParams((prev) => {
            if (value) prev.set("group", value);
            else prev.delete("group");
            return prev;
        });
    };

    const errorMessage = isError
        ? error instanceof Error
            ? error.message
            : "Unbekannter Fehler beim Laden der Projektgruppen"
        : undefined;

    return (
        <Container size="xl" py="xl">
            <Stack gap="xl">
                <Stack gap="xs">
                    <Title order={2}>Projekte nach Projektgruppen</Title>
                    <Text size="sm" c="dimmed">
                        Wähle eine Projektgruppe aus, um alle zugehörigen Projekte zu sehen.
                    </Text>
                </Stack>

                <Stack gap="sm">
                    <Select
                        label="Projektgruppe"
                        placeholder="Projektgruppe wählen"
                        data={selectData}
                        value={selectedGroupId !== null ? String(selectedGroupId) : null}
                        onChange={handleGroupChange}
                        disabled={isLoading && groups.length === 0}
                        rightSection={isLoading ? <Loader size="xs" /> : undefined}
                        nothingFoundMessage={isLoading ? "Lade…" : "Keine Projektgruppen gefunden"}
                        searchable
                        clearable
                    />

                    {errorMessage && (
                        <Alert color="red" variant="light" title="Projektgruppen konnten nicht geladen werden">
                            {errorMessage}
                        </Alert>
                    )}
                </Stack>

                {selectedGroup && (
                    <Card withBorder radius="md" padding="lg" shadow="xs">
                        <Stack gap="xs">
                            <Group justify="space-between" align="flex-start">
                                <Stack gap={4}>
                                    <Title order={3}>{selectedGroup.name}</Title>
                                    <Text size="sm" c="dimmed">
                                        Kurzname: {selectedGroup.short_name}
                                    </Text>
                                </Stack>
                                <Group gap="xs">
                                    <Badge
                                        variant="light"
                                        color="gray"
                                        leftSection={
                                            <span
                                                aria-hidden
                                                style={{
                                                    display: "inline-block",
                                                    width: 10,
                                                    height: 10,
                                                    borderRadius: "50%",
                                                    backgroundColor: selectedGroup.color,
                                                }}
                                            />
                                        }
                                    >
                                        {selectedGroup.projects?.length ?? 0} Projekte
                                    </Badge>
                                </Group>
                            </Group>
                            {selectedGroup.description ? (
                                <Text size="sm" c="dimmed">
                                    {selectedGroup.description}
                                </Text>
                            ) : (
                                <Text size="sm" c="dimmed" style={{ fontStyle: "italic" }}>
                                    Keine Beschreibung verfügbar.
                                </Text>
                            )}
                        </Stack>
                    </Card>
                )}

                {!isLoading && groups.length === 0 && (
                    <Alert color="gray" variant="light" title="Keine Projektgruppen verfügbar">
                        Sobald Projektgruppen vorhanden sind, werden sie hier angezeigt.
                    </Alert>
                )}

                {isLoading && groups.length === 0 ? (
                    <Group justify="center" py="xl">
                        <Loader />
                    </Group>
                ) : selectedGroup ? (
                    <Stack gap="md">
                        <Group justify="space-between" align="center">
                            <Title order={3}>Projekte</Title>
                            <Text size="sm" c="dimmed">
                                {projects.length === 1
                                    ? "1 Projekt in dieser Gruppe"
                                    : `${projects.length} Projekte in dieser Gruppe`}
                            </Text>
                        </Group>

                        {projects.length === 0 ? (
                            <Alert color="blue" variant="light" title="Keine Projekte gefunden">
                                Diese Projektgruppe enthält aktuell keine Projekte.
                            </Alert>
                        ) : (
                            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
                                {projects.map((project) => (
                                    <ProjectCard key={project.id ?? project.name} project={project} />
                                ))}
                            </SimpleGrid>
                        )}
                    </Stack>
                ) : groups.length > 0 ? (
                    <Alert color="blue" variant="light" title="Projektgruppe auswählen">
                        Bitte wähle eine Projektgruppe aus, um die Projekte anzuzeigen.
                    </Alert>
                ) : null}
            </Stack>
        </Container>
    );
}

export function ProjectCard({ project }: { project: Project }) {
    const lengthValue = typeof project.length === "number" ? `${project.length.toLocaleString("de-DE")}` : null;
    const hasProjectId = typeof project.id === "number" && Number.isFinite(project.id);
    const cardProps = hasProjectId
        ? ({
              component: Link,
              to: `/projects/${project.id}`,
              style: { textDecoration: "none" },
          } as const)
        : ({} as const);

    return (
        <Card withBorder shadow="xs" radius="md" padding="lg" {...cardProps}>
            <Stack gap="sm">
                <Stack gap={4}>
                    <Title order={4}>{project.name}</Title>
                    {project.project_number && (
                        <Text size="sm" c="dimmed">
                            Projektnummer: {project.project_number}
                        </Text>
                    )}
                </Stack>

                {project.description ? (
                    <Text size="sm" c="dimmed" lineClamp={3}>
                        {project.description}
                    </Text>
                ) : (
                    <Text size="sm" c="dimmed" style={{ fontStyle: "italic" }}>
                        Keine Projektbeschreibung vorhanden.
                    </Text>
                )}

                <Group gap="xs">
                    {lengthValue && (
                        <Badge variant="light" color="blue">
                            Länge: {lengthValue} km
                        </Badge>
                    )}
                    {project.elektrification && (
                        <Badge variant="light" color="green">
                            Elektrifizierung
                        </Badge>
                    )}
                    {project.second_track && (
                        <Badge variant="light" color="teal">
                            Zweigleisiger Ausbau
                        </Badge>
                    )}
                    {project.new_station && (
                        <Badge variant="light" color="violet">
                            Neuer Bahnhof
                        </Badge>
                    )}
                </Group>
            </Stack>
        </Card>
    );
}
