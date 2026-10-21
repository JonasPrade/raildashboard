import { useDeferredValue, useEffect, useMemo, useState, type CSSProperties } from "react";
import {
    ActionIcon,
    Alert,
    Box,
    Button,
    Container,
    Group,
    List,
    Paper,
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
import { Stat } from "../../shared/ui/Stat";
import { SwatchTag } from "../../shared/ui/SwatchTag";
import { useDisclosure } from "@mantine/hooks";
import { CircleHelp, Search, X } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../../lib/auth";

import { useIsMobile } from "../../shared/hooks/useBreakpoint";
import GroupFilterDrawer, { type ProjectGroupOption } from "../projects/GroupFilterDrawer";
import { ProjectCard } from "../projects/ProjectCard";
import PhaseFilterSelect from "../projects/PhaseFilterSelect";
import {
    PHASE_PARAM,
    filterProjectsByPhase,
    parsePhaseParam,
    serializePhaseParam,
    type PhaseFilterValue,
} from "../projects/phaseFilter";
import ConstituencyPanel from "../abgeordnete/ConstituencyPanel";
import MapControls from "./MapControls";
import TimelineView from "../timeline/TimelineView";
import MapView, { type MapViewProject } from "./LazyMapView";
import { withActiveFeatures } from "../projects/projectFeatureConfig";
import {
    useAppSettings,
    useConstituencyGeojson,
    useProjectGroupGeometries,
    useProjectGroups,
    type ProjectGroup,
} from "../../shared/api/queries";
import { MAP_COLOR } from "../../shared/theme/semanticColors";
import { LoadingState } from "../../shared/ui/LoadingState";

const DEFAULT_GROUP_COLOR = MAP_COLOR.default;
const hasNumericId = (
    group: ProjectGroup,
): group is ProjectGroup & { id: number } => typeof group.id === "number";

// Project cards rendered per step in the list view. Large groups hold hundreds
// of projects; mounting them all at once made switching groups and typing in
// the search box sluggish.
const LIST_PAGE_SIZE = 48;

const DEFAULT_LINE_WIDTH = 4;
const DEFAULT_POINT_SIZE = 5;

export default function MapPage() {
    const isMobile = useIsMobile();
    const [opened, { open, close }] = useDisclosure(false);
    const { data, isLoading, isError, error } = useProjectGroups();
    const { data: appSettings } = useAppSettings();
    const mapGroupMode = appSettings?.map_group_mode ?? "preconfigured";
    const [searchParams, setSearchParams] = useSearchParams();
    const [lineWidth, setLineWidth] = useState(DEFAULT_LINE_WIDTH);
    const [selectedConstituencyId, setSelectedConstituencyId] = useState<number | null>(null);
    const [pointSize, setPointSize] = useState(DEFAULT_POINT_SIZE);
    const [listLimit, setListLimit] = useState(LIST_PAGE_SIZE);

    const view = searchParams.get("view") ?? "map";
    const onlySuperior = searchParams.get("only_superior") !== "false"; // default true
    // Layer state lives in the URL like the other map settings, so a link
    // carries the view someone was looking at. The layer leads to the members
    // of parliament, which only signed-in users may see.
    const { user } = useAuth();
    const canShowConstituencies = user !== null;
    const showConstituencies = canShowConstituencies && searchParams.get("wahlkreise") === "1";

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

    // --- Phase filter: ?phase=BAU,VORPLANUNG,UNBEKANNT (empty = all phases).
    //     Applies to map and list alike and, being a URL param, survives
    //     map↔list switches and shared links like the search does.
    const phaseParam = searchParams.get(PHASE_PARAM);
    const selectedPhases = useMemo(() => parsePhaseParam(phaseParam), [phaseParam]);

    const handlePhaseFilterChange = (values: PhaseFilterValue[]) => {
        const serialized = serializePhaseParam(values);
        setSearchParams((prev) => {
            if (serialized) prev.set(PHASE_PARAM, serialized);
            else prev.delete(PHASE_PARAM);
            return prev;
        });
    };

    const constituencyGeojson = useConstituencyGeojson(showConstituencies);

    const handleShowConstituenciesChange = (checked: boolean) => {
        if (!checked) setSelectedConstituencyId(null);
        setSearchParams((prev) => {
            if (checked) prev.set("wahlkreise", "1");
            else prev.delete("wahlkreise");
            return prev;
        });
    };

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

    // The group list carries metadata only; the (simplified) geometries are
    // loaded per selected group, so the page renders before they arrive.
    const selectedGroupIdsForMap = useMemo(() => selectedGroups.map((g) => g.id), [selectedGroups]);
    const {
        geometries,
        isLoading: geometriesLoading,
        isError: geometriesError,
    } = useProjectGroupGeometries(view === "map" ? selectedGroupIdsForMap : [], onlySuperior);

    const selectedProjects = useMemo(() => {
        const projectMap = new Map<number, MapViewProject>();
        selectedGroups.forEach((group) => {
            const groupColor = group.color?.trim().length ? group.color : DEFAULT_GROUP_COLOR;
            group.projects?.forEach((project) => {
                if (!projectMap.has(project.id)) {
                    projectMap.set(project.id, {
                        ...withActiveFeatures(project),
                        groupColor,
                        geometry: geometries.get(project.id),
                    });
                }
            });
        });
        const allProjects = Array.from(projectMap.values());
        return onlySuperior
            ? allProjects.filter((p) => p.superior_project_id == null)
            : allProjects;
    }, [selectedGroups, onlySuperior, geometries]);

    // Defer the search term for the map filter: the text input stays snappy
    // while the (cheap, but setData-triggering) map update lags a beat behind.
    const deferredSearch = useDeferredValue(localSearch);
    const filteredMapProjects = useMemo(() => {
        const phaseFiltered = filterProjectsByPhase(selectedProjects, selectedPhases);
        const term = deferredSearch.trim().toLowerCase();
        if (!term) return phaseFiltered;
        return phaseFiltered.filter(
            (p) =>
                p.name?.toLowerCase().includes(term) ||
                p.project_number?.toLowerCase().includes(term) ||
                p.description?.toLowerCase().includes(term),
        );
    }, [selectedProjects, selectedPhases, deferredSearch]);
    const isFiltered = localSearch.trim().length > 0 || selectedPhases.length > 0;
    const noMatchMessage = localSearch.trim()
        ? `Keine Projekte für „${localSearch.trim()}"${selectedPhases.length > 0 ? " in den gewählten Phasen" : ""} gefunden`
        : "Keine Projekte in den gewählten Phasen";

    // --- List tab: single-group selection (first entry in ?group) ---
    const selectedGroupId = useMemo(() => {
        const param = searchParams.get("group");
        if (!param) return null;
        const id = Number(param.split(",")[0]);
        return Number.isFinite(id) ? id : null;
    }, [searchParams]);

    // Start from the first page again whenever the shown list changes.
    const listKey = `${selectedGroupId}|${onlySuperior}|${deferredSearch}|${phaseParam ?? ""}`;
    const [prevListKey, setPrevListKey] = useState(listKey);
    if (listKey !== prevListKey) {
        setPrevListKey(listKey);
        setListLimit(LIST_PAGE_SIZE);
    }

    // Auto-select first group when on list tab and no valid group is selected
    useEffect(() => {
        if (view !== "list" && view !== "timeline") return;
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
        <Group justify="center" pb="sm" gap="xs" wrap="nowrap">
            <SegmentedControl
                value={view}
                onChange={handleViewChange}
                size="md"
                fullWidth={isMobile}
                style={isMobile ? { flex: 1, minWidth: 0 } : { minWidth: 360 }}
                data={[
                    { value: "map", label: "Karte" },
                    { value: "list", label: "Liste" },
                    { value: "timeline", label: "Zeitstrahl" },
                ]}
            />
            <Popover width={300} position="bottom" withArrow shadow="md">
                <Popover.Target>
                    <ActionIcon variant="subtle" color="gray" size="md" aria-label="Hilfe zur Suche und Filterung">
                        <CircleHelp size={16} />
                    </ActionIcon>
                </Popover.Target>
                <Popover.Dropdown>
                    <Stack gap="xs">
                        <Text size="sm" fw={600}>So findest du Projekte</Text>
                        <List size="sm" spacing={6}>
                            <List.Item>
                                <Text size="sm" span fw={500}>Suche</Text>
                                <Text size="sm"> — Tippe einen Namen oder eine Nummer ein. Karte, Liste und Zeitstrahl aktualisieren sich sofort.</Text>
                            </List.Item>
                            <List.Item>
                                <Text size="sm" span fw={500}>Projektgruppen</Text>
                                <Text size="sm"> — Klicke auf „Projektgruppen", um nach Themengruppen zu filtern. Auf der Karte kannst du mehrere Gruppen gleichzeitig auswählen.</Text>
                            </List.Item>
                            <List.Item>
                                <Text size="sm" span fw={500}>Planungsphase</Text>
                                <Text size="sm"> — Zeigt nur Projekte in den gewählten Phasen (Mehrfachauswahl). „Unbekannt" umfasst Projekte ohne bekannten Planungsstand.</Text>
                            </List.Item>
                            <List.Item>
                                <Text size="sm" span fw={500}>Nur Hauptprojekte</Text>
                                <Text size="sm"> — Aktiviere diesen Schalter, um Teilprojekte auszublenden.</Text>
                            </List.Item>
                            <List.Item>
                                <Text size="sm" span fw={500}>Zeitstrahl</Text>
                                <Text size="sm"> — Zeigt die Projekte einer Gruppe mit belastbaren Terminen (Baubeginn, Inbetriebnahme, Planfeststellung) auf einer Jahresachse.</Text>
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

    // --- List and timeline view (same group / search / superior controls) ---
    if (view === "list" || view === "timeline") {
        const isTimeline = view === "timeline";
        const selectedGroup = selectedGroupId
            ? groups.find((group) => group.id === selectedGroupId)
            : undefined;
        const rawProjects = (selectedGroup?.projects ?? []).map(withActiveFeatures);
        const superiorFiltered = onlySuperior
            ? rawProjects.filter((p) => p.superior_project_id == null)
            : rawProjects;
        const phaseFiltered = filterProjectsByPhase(superiorFiltered, selectedPhases);
        const searchTerm = deferredSearch.trim().toLowerCase();
        const projects = searchTerm
            ? phaseFiltered.filter(
                  (p) =>
                      p.name?.toLowerCase().includes(searchTerm) ||
                      p.project_number?.toLowerCase().includes(searchTerm) ||
                      p.description?.toLowerCase().includes(searchTerm),
              )
            : phaseFiltered;
        const selectData = groups.map((group) => ({
            value: String(group.id),
            label: group.name,
        }));

        return (
            <Container size="xl" py={{ base: "md", sm: "xl" }} px={{ base: 0, sm: "md" }}>
                <Stack gap="xl">
                    {viewToggle}
                    <Stack gap={6}>
                        <Text className="idt-eyebrow" component="div">Schienenprojekte · {isTimeline ? "Zeitstrahl" : "Liste"}</Text>
                        <Title order={2}>Projekte nach Projektgruppen</Title>
                        <Text size="sm" c="dimmed" style={{ maxWidth: 540 }}>
                            {isTimeline
                                ? "Wähle eine Projektgruppe aus, um ihre Projekte mit belastbaren Terminen auf einer Zeitachse zu sehen."
                                : "Wähle eine Projektgruppe aus, um alle zugehörigen Projekte zu sehen."}
                        </Text>
                    </Stack>

                    <Stack gap="sm">
                        <Group align="flex-end" gap="md" wrap="wrap">
                            <Select
                                label="Projektgruppe"
                                placeholder="Projektgruppe wählen"
                                data={selectData}
                                value={selectedGroupId !== null ? String(selectedGroupId) : null}
                                onChange={handleGroupChange}
                                disabled={isLoading && groups.length === 0}
                                                                nothingFoundMessage={isLoading ? "Lade…" : "Keine Projektgruppen gefunden"}
                                searchable
                                clearable
                                style={{ flex: "1 1 220px", minWidth: 0 }}
                            />
                            <TextInput
                                label="Suche"
                                placeholder="Name, Nr., Beschreibung…"
                                leftSection={<Search size={16} />}
                                rightSection={
                                    localSearch ? (
                                        <ActionIcon variant="subtle" size="xs" onClick={() => setLocalSearch("")}>
                                            <X size={12} />
                                        </ActionIcon>
                                    ) : undefined
                                }
                                value={localSearch}
                                onChange={(e) => setLocalSearch(e.currentTarget.value)}
                                style={{ flex: "1 1 220px", minWidth: 0 }}
                            />
                            <PhaseFilterSelect
                                label="Planungsphase"
                                value={selectedPhases}
                                onChange={handlePhaseFilterChange}
                                style={{ flex: "1 1 220px", minWidth: 0 }}
                            />
                            <Switch
                                label="Nur Hauptprojekte"
                                checked={onlySuperior}
                                onChange={(e) => handleOnlySuperiorChange(e.currentTarget.checked)}
                                size="sm"
                                pb={6}
                                style={{ flex: "0 0 auto" }}
                            />
                        </Group>
                        {errorMessage && (
                            <Alert color="red" variant="light" title="Projektgruppen konnten nicht geladen werden">
                                {errorMessage}
                            </Alert>
                        )}
                    </Stack>

                    {selectedGroup && (
                        <Paper withBorder p="var(--card-pad)">
                            <Stack gap="xs">
                                <Group justify="space-between" align="flex-start">
                                    <Stack gap={4}>
                                        <Title order={3}>{selectedGroup.name}</Title>
                                        <Text size="sm" c="dimmed">
                                            Kurzname: {selectedGroup.short_name}
                                        </Text>
                                    </Stack>
                                    <Group gap="xs">
                                        <SwatchTag color={selectedGroup.color}>
                                            {selectedGroup.projects?.length ?? 0} Projekte
                                        </SwatchTag>
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
                        </Paper>
                    )}

                    {!isLoading && groups.length === 0 && (
                        <Alert color="gray" variant="light" title="Keine Projektgruppen verfügbar">
                            Sobald Projektgruppen vorhanden sind, werden sie hier angezeigt.
                        </Alert>
                    )}

                    {isLoading && groups.length === 0 ? (
                        <LoadingState rows={6} />
                    ) : selectedGroup && isTimeline ? (
                        <TimelineView
                            // Remount per group so the row paging starts over.
                            key={selectedGroup.id}
                            groupId={selectedGroup.id}
                            onlySuperior={onlySuperior}
                            visibleProjectIds={new Set(projects.map((p) => p.id))}
                            searchActive={searchTerm.length > 0}
                        />
                    ) : selectedGroup ? (
                        <Stack gap="md">
                            <Paper
                                withBorder
                                p="var(--card-pad)"
                                style={{ "--card-accent": "var(--accent-primary)" } as CSSProperties}
                            >
                                <Group justify="space-between" align="center" wrap="wrap" gap="sm">
                                    <Group gap="md" align="center" wrap="nowrap">
                                        <Stat value={projects.length} />
                                        <Stack gap={2}>
                                            <Text className="idt-eyebrow" component="div">{selectedGroup.short_name ?? "Projektgruppe"}</Text>
                                            <Title order={3}>Projekte</Title>
                                        </Stack>
                                    </Group>
                                    <Text size="sm" c="dimmed">
                                        {isFiltered
                                            ? `${projects.length} von ${superiorFiltered.length} Projekten`
                                            : projects.length === 1
                                              ? "1 Projekt"
                                              : `${projects.length} Projekte${onlySuperior && rawProjects.length !== projects.length ? ` (von ${rawProjects.length})` : " in dieser Gruppe"}`}
                                    </Text>
                                </Group>
                            </Paper>

                            {projects.length === 0 ? (
                                <Alert color="blue" variant="light" title="Keine Projekte gefunden">
                                    {isFiltered
                                        ? `${noMatchMessage}.`
                                        : "Diese Projektgruppe enthält aktuell keine Projekte."}
                                </Alert>
                            ) : (
                                <Stack gap="lg">
                                    <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
                                        {projects.slice(0, listLimit).map((project) => (
                                            <ProjectCard key={project.id ?? project.name} project={project} />
                                        ))}
                                    </SimpleGrid>
                                    {projects.length > listLimit && (
                                        <Group justify="center">
                                            <Button
                                                variant="default"
                                                onClick={() => setListLimit((limit) => limit + LIST_PAGE_SIZE)}
                                            >
                                                Weitere {Math.min(LIST_PAGE_SIZE, projects.length - listLimit)} von{" "}
                                                {projects.length - listLimit} Projekten anzeigen
                                            </Button>
                                        </Group>
                                    )}
                                </Stack>
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
            <Container size="xl" px={{ base: 0, sm: "md" }}>
                {viewToggle}
                <Box style={{ position: "relative" }}>
                    <MapView
                        projects={filteredMapProjects}
                        lineWidth={lineWidth}
                        pointSize={pointSize}
                        constituencies={
                            showConstituencies ? constituencyGeojson.data ?? null : null
                        }
                        onConstituencySelect={
                            showConstituencies ? setSelectedConstituencyId : undefined
                        }
                        selectedConstituencyId={selectedConstituencyId}
                    />
                    {showConstituencies && selectedConstituencyId !== null && (
                        <ConstituencyPanel
                            constituencyId={selectedConstituencyId}
                            onClose={() => setSelectedConstituencyId(null)}
                        />
                    )}
                    {showConstituencies && constituencyGeojson.data?.attribution && (
                        <Text
                            size="xs"
                            c="dimmed"
                            style={{
                                position: "absolute",
                                bottom: 6,
                                left: 12,
                                zIndex: 5,
                                background: "var(--surface)",
                                padding: "2px 6px",
                            }}
                        >
                            {constituencyGeojson.data.attribution}
                        </Text>
                    )}
                    {isLoading && groups.length === 0 && (
                        <Box
                            style={{
                                position: "absolute",
                                top: 0,
                                left: 0,
                                width: "100%",
                                height: "100%",
                                background: "color-mix(in srgb, var(--surface) 70%, transparent)",
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "center",
                                justifyContent: "center",
                                gap: 12,
                                zIndex: 4,
                            }}
                        >
                            <Text size="sm" c="dimmed">Projektgruppen werden geladen…</Text>
                        </Box>
                    )}
                    {!isLoading && (geometriesLoading || geometriesError) && (
                        <Text
                            size="xs"
                            c={geometriesError ? "red" : "dimmed"}
                            role="status"
                            style={{
                                position: "absolute",
                                top: 12,
                                left: "50%",
                                transform: "translateX(-50%)",
                                zIndex: 5,
                                background: "var(--surface)",
                                border: "2px solid var(--border-frame)",
                                padding: "4px 10px",
                                borderRadius: 0,
                                pointerEvents: "none",
                            }}
                        >
                            {geometriesError
                                ? "Einige Projektverläufe konnten nicht geladen werden"
                                : "Projektverläufe werden geladen…"}
                        </Text>
                    )}
                    {isFiltered && selectedProjects.length > 0 && filteredMapProjects.length === 0 && (
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
                                    background: "var(--surface)",
                                    padding: "8px 14px",
                                    borderRadius: 0,
                                    border: "2px solid var(--border-frame)",
                                }}
                            >
                                {noMatchMessage}
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
                        phaseFilter={selectedPhases}
                        onPhaseFilterChange={handlePhaseFilterChange}
                        totalProjects={selectedProjects.length}
                        filteredCount={filteredMapProjects.length}
                        showConstituencies={showConstituencies}
                        onShowConstituenciesChange={
                            canShowConstituencies ? handleShowConstituenciesChange : undefined
                        }
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
