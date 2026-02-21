import { useEffect, useMemo, useState } from "react";
import {
    Alert,
    Badge,
    Box,
    Card,
    Container,
    Group,
    Loader,
    SegmentedControl,
    Select,
    SimpleGrid,
    Stack,
    Switch,
    Text,
    Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useSearchParams } from "react-router-dom";

import GroupFilterDrawer, { type ProjectGroupOption } from "../projects/GroupFilterDrawer";
import { ProjectCard } from "../projects/ProjectGroupsPage";
import MapControls from "./MapControls";
import MapView from "./MapView";
import { useProjectGroups, type ProjectGroup, type Project } from "../../shared/api/queries";

const DEFAULT_GROUP_COLOR = "#2563eb";
const hasNumericId = (
    group: ProjectGroup,
): group is ProjectGroup & { id: number } => typeof group.id === "number";
const hasNumericProjectId = (project: Project): project is Project & { id: number } =>
    typeof project.id === "number";

const DEFAULT_LINE_WIDTH = 4;
const DEFAULT_POINT_SIZE = 5;

export default function MapPage() {
    const [opened, { open, close }] = useDisclosure(false);
    const { data, isLoading, isError, error } = useProjectGroups();
    const [searchParams, setSearchParams] = useSearchParams();
    const [lineWidth, setLineWidth] = useState(DEFAULT_LINE_WIDTH);
    const [pointSize, setPointSize] = useState(DEFAULT_POINT_SIZE);

    const view = searchParams.get("view") ?? "map";
    const onlySuperior = searchParams.get("only_superior") !== "false"; // default true

    const handleOnlySuperiorChange = (checked: boolean) => {
        setSearchParams((prev) => {
            prev.set("only_superior", String(checked));
            return prev;
        });
    };

    // --- Shared: all groups with numeric ids ---
    const groups = useMemo(() => (data ?? []).filter(hasNumericId), [data]);

    const projectGroupOptions = useMemo<ProjectGroupOption[]>(() => {
        return groups.map((group) => ({
            id: group.id,
            name: group.name,
            color: group.color && group.color.trim().length > 0 ? group.color : DEFAULT_GROUP_COLOR,
            count: group.projects?.length,
        }));
    }, [groups]);

    // --- Shared: selected group IDs from ?group (comma-separated) ---
    const selectedGroupIds = useMemo<number[]>(() => {
        const rawGroups = searchParams.get("group");
        if (!rawGroups) return [];
        return rawGroups
            .split(",")
            .map((value) => Number(value))
            .filter((value) => Number.isFinite(value));
    }, [searchParams]);

    // --- Map tab: multi-group filter ---
    const selectedGroups = useMemo(() => {
        if (selectedGroupIds.length === 0) return groups;
        const selectedSet = new Set(selectedGroupIds);
        return groups.filter((group) => selectedSet.has(group.id));
    }, [groups, selectedGroupIds]);

    const selectedProjects = useMemo(() => {
        const projectMap = new Map<
            number,
            { id: number; name: string; groupColor?: string; geojson_representation?: string | null; superior_project_id?: number | null; description?: string | null; project_number?: string | null; length?: number | null; elektrification?: boolean | null; second_track?: boolean | null; new_station?: boolean | null }
        >();
        selectedGroups.forEach((group) => {
            const groupColor = group.color?.trim().length ? group.color : DEFAULT_GROUP_COLOR;
            group.projects?.filter(hasNumericProjectId).forEach((project) => {
                if (!projectMap.has(project.id)) {
                    projectMap.set(project.id, {
                        id: project.id,
                        name: project.name,
                        groupColor,
                        geojson_representation: project.geojson_representation,
                        superior_project_id: project.superior_project_id,
                        description: project.description,
                        project_number: project.project_number,
                        length: project.length,
                        elektrification: project.elektrification,
                        second_track: project.second_track,
                        new_station: project.new_station,
                    });
                }
            });
        });
        const allProjects = Array.from(projectMap.values());
        return onlySuperior
            ? allProjects.filter((p) => p.superior_project_id == null)
            : allProjects;
    }, [selectedGroups, onlySuperior]);

    // --- List tab: single-group selection (first entry in ?group) ---
    const selectedGroupId = useMemo(() => {
        const param = searchParams.get("group");
        if (!param) return null;
        const id = Number(param.split(",")[0]);
        return Number.isFinite(id) ? id : null;
    }, [searchParams]);

    // Auto-select first group when on list tab and no valid group is selected
    useEffect(() => {
        if (view !== "list") return;
        if (groups.length === 0) return;
        if (selectedGroupId !== null && groups.some((g) => g.id === selectedGroupId)) return;
        setSearchParams((prev) => {
            prev.set("group", String(groups[0]!.id));
            return prev;
        }, { replace: true });
    }, [view, groups, selectedGroupId, setSearchParams]);

    const handleGroupChange = (value: string | null) => {
        setSearchParams((prev) => {
            if (value) prev.set("group", value);
            else prev.delete("group");
            return prev;
        });
    };

    const handleViewChange = (val: string) => {
        setSearchParams((prev) => {
            prev.set("view", val);
            return prev;
        });
    };

    const viewToggle = (
        <Group justify="center" pb="sm">
            <SegmentedControl
                value={view}
                onChange={handleViewChange}
                size="md"
                style={{ minWidth: 280 }}
                data={[
                    { value: "map", label: "Karte" },
                    { value: "list", label: "Liste" },
                ]}
            />
        </Group>
    );

    const errorMessage = isError
        ? error instanceof Error
            ? error.message
            : "Unbekannter Fehler beim Laden der Projektgruppen"
        : undefined;

    // --- List view ---
    if (view === "list") {
        const selectedGroup = selectedGroupId
            ? groups.find((group) => group.id === selectedGroupId)
            : undefined;
        const rawProjects = (selectedGroup?.projects ?? []).filter(Boolean) as Project[];
        const projects = onlySuperior
            ? rawProjects.filter((p) => p.superior_project_id == null)
            : rawProjects;
        const selectData = groups.map((group) => ({
            value: String(group.id),
            label: group.name,
        }));

        return (
            <Container size="xl" py="xl">
                <Stack gap="xl">
                    {viewToggle}
                    <Stack gap="xs">
                        <Title order={2}>Projekte nach Projektgruppen</Title>
                        <Text size="sm" c="dimmed">
                            Wähle eine Projektgruppe aus, um alle zugehörigen Projekte zu sehen.
                        </Text>
                    </Stack>

                    <Stack gap="sm">
                        <Group align="flex-end" gap="md">
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
                                style={{ flex: 1 }}
                            />
                            <Switch
                                label="Nur Hauptprojekte"
                                checked={onlySuperior}
                                onChange={(e) => handleOnlySuperiorChange(e.currentTarget.checked)}
                                size="sm"
                                pb={6}
                            />
                        </Group>
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
                                    {projects.length === 1 ? "1 Projekt" : `${projects.length} Projekte`}
                                    {onlySuperior && rawProjects.length !== projects.length
                                        ? ` (von ${rawProjects.length})`
                                        : " in dieser Gruppe"}
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

    // --- Map view (default) ---
    return (
        <>
            <Container size="xl" style={{ position: "relative" }}>
                {viewToggle}
                <Box style={{ position: "relative" }}>
                    <MapView projects={selectedProjects} lineWidth={lineWidth} pointSize={pointSize} />
                    <MapControls
                        onOpenFilters={open}
                        lineWidth={lineWidth}
                        onLineWidthChange={setLineWidth}
                        pointSize={pointSize}
                        onPointSizeChange={setPointSize}
                        onlySuperior={onlySuperior}
                        onOnlySuperiorChange={handleOnlySuperiorChange}
                    />
                </Box>
            </Container>
            <GroupFilterDrawer
                opened={opened}
                onClose={close}
                groups={projectGroupOptions}
                loading={isLoading}
                error={errorMessage}
            />
        </>
    );
}
