import { useEffect, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
    Alert,
    Container,
    Group,
    Loader,
    Select,
    SimpleGrid,
    Stack,
    Text,
} from "@mantine/core";

import { useProjectGroups, type Project, type ProjectGroup } from "../../shared/api/queries";
import { ChronicleCard, ChronicleDataChip, ChronicleHeadline } from "../../components/chronicle";

const hasNumericId = (
    group: ProjectGroup,
): group is ProjectGroup & { id: number } => typeof group.id === "number";

export default function ProjectGroupsPage() {
    const { data, isLoading, isError, error } = useProjectGroups();
    const [searchParams, setSearchParams] = useSearchParams();

    const groups = useMemo(
        () => (data ?? []).filter((g): g is ProjectGroup & { id: number } => hasNumericId(g) && g.is_visible !== false),
        [data],
    );

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
                    <ChronicleHeadline as="h2">Projekte nach Projektgruppen</ChronicleHeadline>
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
                    <ChronicleCard>
                        <Stack gap="xs">
                            <Group justify="space-between" align="flex-start">
                                <Stack gap={4}>
                                    <ChronicleHeadline as="h3">{selectedGroup.name}</ChronicleHeadline>
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
                        <Group justify="space-between" align="center">
                            <ChronicleHeadline as="h3">Projekte</ChronicleHeadline>
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

    const cardContent = (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <span
                    style={{
                        fontFamily: "var(--font-display)",
                        fontWeight: 700,
                        fontSize: "20px",
                        lineHeight: 1.15,
                        letterSpacing: "-0.005em",
                        textTransform: "uppercase",
                        color: "var(--ink)",
                    }}
                >
                    {project.name}
                </span>
                {project.project_number && (
                    <span
                        style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "11px",
                            fontWeight: 700,
                            letterSpacing: "0.1em",
                            textTransform: "uppercase",
                            color: "var(--ink3)",
                        }}
                    >
                        ▸ Nr. {project.project_number}
                    </span>
                )}
            </div>

            {project.description ? (
                <p
                    style={{
                        fontFamily: "var(--font-sans)",
                        fontSize: "15px",
                        lineHeight: 1.65,
                        color: "var(--ink2)",
                        margin: 0,
                        display: "-webkit-box",
                        WebkitLineClamp: 3,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                    }}
                >
                    {project.description}
                </p>
            ) : (
                <p
                    style={{
                        fontFamily: "var(--font-sans)",
                        fontSize: "15px",
                        lineHeight: 1.65,
                        fontStyle: "italic",
                        color: "var(--ink3)",
                        margin: 0,
                    }}
                >
                    Keine Projektbeschreibung vorhanden.
                </p>
            )}

            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {lengthValue && <ChronicleDataChip>Länge: {lengthValue} km</ChronicleDataChip>}
                {project.elektrification && <ChronicleDataChip>Elektrifizierung</ChronicleDataChip>}
                {project.second_track && <ChronicleDataChip>Zweigleisiger Ausbau</ChronicleDataChip>}
                {project.new_station && <ChronicleDataChip>Neuer Bahnhof</ChronicleDataChip>}
            </div>
        </div>
    );

    if (hasProjectId) {
        return (
            <Link to={`/projects/${project.id}`} style={{ textDecoration: "none", display: "block" }}>
                <ChronicleCard accent>
                    {cardContent}
                </ChronicleCard>
            </Link>
        );
    }
    return (
        <ChronicleCard>
            {cardContent}
        </ChronicleCard>
    );
}
