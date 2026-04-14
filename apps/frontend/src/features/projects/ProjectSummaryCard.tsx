import { Group, Stack, Text } from "@mantine/core";
import type { Project } from "../../shared/api/queries";
import { trainCategoryLabels, featureGroups } from "./projectFeatureConfig";
import { ChronicleDataChip } from "../../components/chronicle";

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
                    <ChronicleDataChip>{project.project_number}</ChronicleDataChip>
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
                        .map(({ key, label }) => (
                            <ChronicleDataChip key={String(key)}>{label}</ChronicleDataChip>
                        ))}
                </Group>
            )}

            {/* Aktive Merkmale */}
            {activeFeatures.length > 0 && (
                <Group gap={4} wrap="wrap">
                    {activeFeatures.map(({ key, label }) => (
                        <ChronicleDataChip key={String(key)}>{label}</ChronicleDataChip>
                    ))}
                </Group>
            )}
        </Stack>
    );
}
