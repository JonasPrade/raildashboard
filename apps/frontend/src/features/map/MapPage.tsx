import { useMemo } from "react";
import { Container } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";

import GroupFilterDrawer, { type ProjectGroupOption } from "../projects/GroupFilterDrawer";
import MapControls from "./MapControls";
import MapView from "./MapView";
import { useProjectGroups, type ProjectGroup } from "../../shared/api/queries";

const DEFAULT_GROUP_COLOR = "#2563eb";
const hasNumericId = (
    group: ProjectGroup,
): group is ProjectGroup & { id: number } => typeof group.id === "number";

export default function MapPage() {
    const [opened, { open, close }] = useDisclosure(false);
    const { data, isLoading, isError, error } = useProjectGroups();

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

    const errorMessage = isError
        ? error instanceof Error
            ? error.message
            : "Unbekannter Fehler beim Laden der Projektgruppen"
        : undefined;

    return (
        <>
            <Container size="xl" style={{ height: "100%", position: "relative" }}>
                <MapView />
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
