import { Badge, Group, Stack, Text } from "@mantine/core";
import type { Project } from "../../shared/api/queries";
import { trainCategoryLabels, featureGroups } from "./projectFeatureConfig";

type Props = {
    project: Project;
};

/**
 * Kompakte Kurzansicht eines Projekts – verwendbar im Karten-Popup,
 * in Unter-/Übergeordnet-Abschnitten und an anderen Stellen.
 */
export default function ProjectSummaryCard({ project }: Props) {
    const activeFeatures = featureGroups
        .flatMap((g) => g.features)
        .filter(({ key }) => Boolean(project[key]));

    return (
        <Stack gap="xs">
            {/* Name + Projektnummer */}
            <Group gap="xs" align="center" wrap="wrap">
                <Text fw={600}>{project.name}</Text>
                {project.project_number && (
                    <Badge color="gray" variant="light" size="sm">
                        {project.project_number}
                    </Badge>
                )}
            </Group>

            {/* Beschreibung */}
            {project.description && (
                <Text size="sm" c="dimmed" lineClamp={2}>
                    {project.description}
                </Text>
            )}

            {/* Verkehrsarten – nur aktive */}
            {trainCategoryLabels.some(({ key }) => Boolean(project[key])) && (
                <Group gap={4} wrap="wrap">
                    {trainCategoryLabels
                        .filter(({ key }) => Boolean(project[key]))
                        .map(({ key, label, color }) => (
                            <Badge key={String(key)} size="xs" variant="light" color={color}>
                                {label}
                            </Badge>
                        ))}
                </Group>
            )}

            {/* Aktive Merkmale */}
            {activeFeatures.length > 0 && (
                <Group gap={4} wrap="wrap">
                    {activeFeatures.map(({ key, label }) => (
                        <Badge key={String(key)} size="xs" variant="light" color="blue">
                            {label}
                        </Badge>
                    ))}
                </Group>
            )}
        </Stack>
    );
}
