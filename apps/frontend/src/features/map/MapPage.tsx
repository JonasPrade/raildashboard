import { useMemo } from "react";
import { Container } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useSearchParams } from "react-router-dom";

import GroupFilterDrawer, { type ProjectGroupOption } from "../projects/GroupFilterDrawer";
import MapControls from "./MapControls";
import MapView from "./MapView";
import { useProjectGroups, type ProjectGroup, type Project } from "../../shared/api/queries";

const DEFAULT_GROUP_COLOR = "#2563eb";
const hasNumericId = (
    group: ProjectGroup,
): group is ProjectGroup & { id: number } => typeof group.id === "number";
const hasNumericProjectId = (project: Project): project is Project & { id: number } =>
    typeof project.id === "number";

export default function MapPage() {
    const [opened, { open, close }] = useDisclosure(false);
    const { data, isLoading, isError, error } = useProjectGroups();
    const [searchParams] = useSearchParams();

    const projectGroupOptions = useMemo<ProjectGroupOption[]>(() => {
        if (!data) return [];
        return data
            .filter(hasNumericId)
            .map((group) => ({
                id: group.id,
                name: group.name,
                color: group.color && group.color.trim().length > 0 ? group.color : DEFAULT_GROUP_COLOR,
                count: group.projects?.length,
            }));
    }, [data]);

    const selectedGroupIds = useMemo<number[]>(() => {
        const rawGroups = searchParams.get("group");
        if (!rawGroups) return [];
        return rawGroups
            .split(",")
            .map((value) => Number(value))
            .filter((value) => Number.isFinite(value));
    }, [searchParams]);

    const selectedGroups = useMemo(() => {
        if (!data) return [];
        if (selectedGroupIds.length === 0) return data.filter(hasNumericId);
        const selectedSet = new Set(selectedGroupIds);
        return data.filter((group) => hasNumericId(group) && selectedSet.has(group.id));
    }, [data, selectedGroupIds]);

    const selectedProjects = useMemo(() => {
        const projectMap = new Map<number, { id: number; name: string; groupColor?: string }>();
        selectedGroups.forEach((group) => {
            const groupColor = group.color?.trim().length ? group.color : DEFAULT_GROUP_COLOR;
            group.projects?.filter(hasNumericProjectId).forEach((project) => {
                if (!projectMap.has(project.id)) {
                    projectMap.set(project.id, { id: project.id, name: project.name, groupColor });
                }
            });
        });
        return Array.from(projectMap.values());
    }, [selectedGroups]);

    const errorMessage = isError
        ? error instanceof Error
            ? error.message
            : "Unbekannter Fehler beim Laden der Projektgruppen"
        : undefined;

    return (
        <>
            <Container size="xl" style={{ height: "100%", position: "relative" }}>
                <MapView projects={selectedProjects} />
                <MapControls onOpenFilters={open} />
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
