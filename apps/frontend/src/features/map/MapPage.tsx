import { useEffect, useMemo, useState } from "react";
import {
    ActionIcon,
    Alert,
    Box,
    Container,
    Group,
    List,
    Loader,
    Popover,
    SegmentedControl,
    Select,
    SimpleGrid,
    Stack,
    Switch,
    Text,
    TextInput,
    Title,
} from "@mantine/core";
import { ChronicleCard, ChronicleDataChip } from "../../components/chronicle";
import { FlapNumber, Eyebrow } from "../../components/tafel";
import { useDisclosure } from "@mantine/hooks";
import { IconHelp, IconSearch, IconX } from "@tabler/icons-react";
import { useSearchParams } from "react-router-dom";

import GroupFilterDrawer, { type ProjectGroupOption } from "../projects/GroupFilterDrawer";
import { ProjectCard } from "../projects/ProjectGroupsPage";
import MapControls from "./MapControls";
import MapView, { type MapViewProject } from "./MapView";
import { useProjectGroups, useAppSettings, type ProjectGroup, type Project } from "../../shared/api/queries";

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
    const { data: appSettings } = useAppSettings();
    const mapGroupMode = appSettings?.map_group_mode ?? "preconfigured";
    const [searchParams, setSearchParams] = useSearchParams();
    const [lineWidth, setLineWidth] = useState(DEFAULT_LINE_WIDTH);
    const [pointSize, setPointSize] = useState(DEFAULT_POINT_SIZE);

    const view = searchParams.get("view") ?? "map";
    const onlySuperior = searchParams.get("only_superior") !== "false"; // default true

    // --- Search state: local for immediate input, debounced to URL ---
    const [localSearch, setLocalSearch] = useState(() => searchParams.get("search") ?? "");

    useEffect(() => {
        const timer = setTimeout(() => {
            setSearchParams((prev) => {
                if (localSearch) prev.set("search", localSearch);
                else prev.delete("search");
                return prev;
            }, { replace: true });
        }, 200);
        return () => clearTimeout(timer);
    }, [localSearch, setSearchParams]);

    const handleOnlySuperiorChange = (checked: boolean) => {
        setSearchParams((prev) => {
            prev.set("only_superior", String(checked));
            return prev;
        });
    };

    // --- Shared: all groups with numeric ids ---
    const groups = useMemo(
        () => (data ?? []).filter((g): g is ProjectGroup & { id: number } => hasNumericId(g) && g.is_visible !== false),
        [data],
    );

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
        if (mapGroupMode === "all") return groups;
        if (selectedGroupIds.length === 0) {
            const defaults = groups.filter((g) => g.is_default_selected);
            return defaults.length > 0 ? defaults : groups;
        }
        const selectedSet = new Set(selectedGroupIds);
        return groups.filter((group) => selectedSet.has(group.id));
    }, [groups, selectedGroupIds, mapGroupMode]);

    const selectedProjects = useMemo(() => {
        const projectMap = new Map<number, MapViewProject>();
        selectedGroups.forEach((group) => {
            const groupColor = group.color?.trim().length ? group.color : DEFAULT_GROUP_COLOR;
            group.projects?.filter(hasNumericProjectId).forEach((project) => {
                if (!projectMap.has(project.id)) {
                    projectMap.set(project.id, { ...project, id: project.id, groupColor });
                }
            });
        });
        const allProjects = Array.from(projectMap.values());
        return onlySuperior
            ? allProjects.filter((p) => p.superior_project_id == null)
            : allProjects;
    }, [selectedGroups, onlySuperior]);

    const filteredMapProjects = useMemo(() => {
        const term = localSearch.trim().toLowerCase();
        if (!term) return selectedProjects;
        return selectedProjects.filter(
            (p) =>
                p.name?.toLowerCase().includes(term) ||
                p.project_number?.toLowerCase().includes(term) ||
                p.description?.toLowerCase().includes(term),
        );
    }, [selectedProjects, localSearch]);

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
        <Group justify="center" pb="sm" gap="xs">
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
            <Popover width={300} position="bottom" withArrow shadow="md">
                <Popover.Target>
                    <ActionIcon variant="subtle" color="gray" size="md" aria-label="Hilfe zur Suche und Filterung">
                        <IconHelp size={18} />
                    </ActionIcon>
                </Popover.Target>
                <Popover.Dropdown>
                    <Stack gap="xs">
                        <Text size="sm" fw={600}>So findest du Projekte</Text>
                        <List size="sm" spacing={6}>
                            <List.Item>
                                <Text size="sm" span fw={500}>Suche</Text>
                                <Text size="sm"> — Tippe einen Namen oder eine Nummer ein. Die Karte bzw. Liste aktualisiert sich sofort.</Text>
                            </List.Item>
                            <List.Item>
                                <Text size="sm" span fw={500}>Projektgruppen</Text>
                                <Text size="sm"> — Klicke auf „Projektgruppen", um nach Themengruppen zu filtern. Auf der Karte kannst du mehrere Gruppen gleichzeitig auswählen.</Text>
                            </List.Item>
                            <List.Item>
                                <Text size="sm" span fw={500}>Nur Hauptprojekte</Text>
                                <Text size="sm"> — Aktiviere diesen Schalter, um Teilprojekte auszublenden.</Text>
                            </List.Item>
                            <List.Item>
                                <Text size="sm" c="dimmed">Tipp: Die aktuelle Ansicht lässt sich als Link teilen – einfach die URL kopieren.</Text>
                            </List.Item>
                        </List>
                    </Stack>
                </Popover.Dropdown>
            </Popover>
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
        const superiorFiltered = onlySuperior
            ? rawProjects.filter((p) => p.superior_project_id == null)
            : rawProjects;
        const searchTerm = localSearch.trim().toLowerCase();
        const projects = searchTerm
            ? superiorFiltered.filter(
                  (p) =>
                      p.name?.toLowerCase().includes(searchTerm) ||
                      p.project_number?.toLowerCase().includes(searchTerm) ||
                      p.description?.toLowerCase().includes(searchTerm),
              )
            : superiorFiltered;
        const selectData = groups.map((group) => ({
            value: String(group.id),
            label: group.name,
        }));

        return (
            <Container size="xl" py="xl">
                <Stack gap="xl">
                    {viewToggle}
                    <Stack gap={6}>
                        <Eyebrow>Schienenprojekte · Liste</Eyebrow>
                        <Title
                            order={2}
                            style={{
                                fontFamily: "var(--font-display)",
                                textTransform: "uppercase",
                                margin: 0,
                                letterSpacing: "-0.015em",
                                lineHeight: 0.95,
                            }}
                        >
                            Projekte nach <em style={{ fontStyle: "normal", color: "var(--led)" }}>Projektgruppen</em>
                        </Title>
                        <Text size="sm" c="dimmed" style={{ maxWidth: 540 }}>
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
                            <TextInput
                                label="Suche"
                                placeholder="Name, Nr., Beschreibung…"
                                leftSection={<IconSearch size={14} />}
                                rightSection={
                                    localSearch ? (
                                        <ActionIcon variant="subtle" size="xs" onClick={() => setLocalSearch("")}>
                                            <IconX size={12} />
                                        </ActionIcon>
                                    ) : undefined
                                }
                                value={localSearch}
                                onChange={(e) => setLocalSearch(e.currentTarget.value)}
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
                        <ChronicleCard>
                            <Stack gap="xs">
                                <Group justify="space-between" align="flex-start">
                                    <Stack gap={4}>
                                        <Title order={3}>{selectedGroup.name}</Title>
                                        <Text size="sm" c="dimmed">
                                            Kurzname: {selectedGroup.short_name}
                                        </Text>
                                    </Stack>
                                    <Group gap="xs">
                                        <ChronicleDataChip>
                                            <span
                                                aria-hidden
                                                style={{
                                                    display: "inline-block",
                                                    width: 8,
                                                    height: 8,
                                                    borderRadius: "50%",
                                                    backgroundColor: selectedGroup.color,
                                                    marginRight: 6,
                                                    verticalAlign: "middle",
                                                }}
                                            />
                                            {selectedGroup.projects?.length ?? 0} Projekte
                                        </ChronicleDataChip>
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
                        </ChronicleCard>
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
                            <Group
                                justify="space-between"
                                align="center"
                                wrap="nowrap"
                                style={{
                                    background: "var(--bg2)",
                                    border: "1px solid var(--rule)",
                                    borderLeft: "3px solid var(--info)",
                                    padding: "16px 20px",
                                }}
                            >
                                <Group gap="md" align="center" wrap="nowrap">
                                    <FlapNumber
                                        n={projects.length}
                                        digits={Math.max(2, String(projects.length).length)}
                                        width={42}
                                        height={52}
                                        fontSize={32}
                                    />
                                    <Stack gap={2}>
                                        <Eyebrow>{selectedGroup.short_name ?? "Projektgruppe"}</Eyebrow>
                                        <Title
                                            order={3}
                                            style={{
                                                fontFamily: "var(--font-display)",
                                                textTransform: "uppercase",
                                                margin: 0,
                                                letterSpacing: "-0.005em",
                                            }}
                                        >
                                            Projekte
                                        </Title>
                                    </Stack>
                                </Group>
                                <Text
                                    style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: 11,
                                        letterSpacing: "0.14em",
                                        textTransform: "uppercase",
                                        color: "var(--ink3)",
                                        fontWeight: 700,
                                    }}
                                >
                                    {localSearch.trim()
                                        ? `${projects.length} von ${superiorFiltered.length} Projekten`
                                        : projects.length === 1
                                          ? "1 Projekt"
                                          : `${projects.length} Projekte${onlySuperior && rawProjects.length !== projects.length ? ` (von ${rawProjects.length})` : " in dieser Gruppe"}`}
                                </Text>
                            </Group>

                            {projects.length === 0 ? (
                                <Alert color="blue" variant="light" title="Keine Projekte gefunden">
                                    {localSearch.trim()
                                        ? `Keine Projekte für „${localSearch.trim()}" gefunden.`
                                        : "Diese Projektgruppe enthält aktuell keine Projekte."}
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
            <Container size="xl">
                {viewToggle}
                <Box style={{ position: "relative" }}>
                    <MapView projects={filteredMapProjects} lineWidth={lineWidth} pointSize={pointSize} />
                    {isLoading && groups.length === 0 && (
                        <Box
                            style={{
                                position: "absolute",
                                top: 0,
                                left: 0,
                                width: "100%",
                                height: "100%",
                                background: "rgba(255,255,255,0.7)",
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "center",
                                justifyContent: "center",
                                gap: 12,
                                zIndex: 4,
                            }}
                        >
                            <Loader size="lg" />
                            <Text size="sm" c="dimmed">Projektgruppen werden geladen…</Text>
                        </Box>
                    )}
                    {localSearch.trim() && filteredMapProjects.length === 0 && (
                        <Box
                            style={{
                                position: "absolute",
                                top: "50%",
                                left: "50%",
                                transform: "translate(-50%, -50%)",
                                zIndex: 5,
                                pointerEvents: "none",
                            }}
                        >
                            <Text
                                size="sm"
                                c="dimmed"
                                style={{
                                    background: "rgba(255,255,255,0.9)",
                                    padding: "8px 14px",
                                    borderRadius: 8,
                                    border: "1px solid #e0e0e0",
                                }}
                            >
                                Keine Projekte für „{localSearch.trim()}" gefunden
                            </Text>
                        </Box>
                    )}
                    <MapControls
                        onOpenFilters={open}
                        lineWidth={lineWidth}
                        onLineWidthChange={setLineWidth}
                        pointSize={pointSize}
                        onPointSizeChange={setPointSize}
                        onlySuperior={onlySuperior}
                        onOnlySuperiorChange={handleOnlySuperiorChange}
                        searchTerm={localSearch}
                        onSearchChange={setLocalSearch}
                        totalProjects={selectedProjects.length}
                        filteredCount={filteredMapProjects.length}
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
