import { Stack, Text, UnstyledButton } from "@mantine/core";

import { Swatch } from "../../shared/ui/SwatchTag";
import { MAP_COLOR } from "../../shared/theme/semanticColors";

export type OverlapListProject = {
    id: number;
    name?: string | null;
    project_number?: string | null;
    groupColor?: string;
};

type Props = {
    projects: OverlapListProject[];
    /** Called with the hovered or focused entry, null when it is left. */
    onHighlight: (projectId: number | null) => void;
    onSelect: (projectId: number) => void;
};

/**
 * Popup list of every project at one spot of the map, shown when a click
 * hits more than one (docs/features/feature-map-overlapping-geometries.md → A).
 */
export default function MapOverlapList({ projects, onHighlight, onSelect }: Props) {
    return (
        <Stack gap="xs">
            <Text size="sm" fw={600} c="dimmed">
                {projects.length} Projekte an dieser Stelle
            </Text>
            <Stack
                gap={0}
                style={{ maxHeight: "min(45vh, 360px)", overflowY: "auto", margin: "0 -8px" }}
            >
                {projects.map((project) => (
                    <UnstyledButton
                        key={project.id}
                        className="idt-map-overlap-row"
                        onMouseEnter={() => onHighlight(project.id)}
                        onMouseLeave={() => onHighlight(null)}
                        onFocus={() => onHighlight(project.id)}
                        onBlur={() => onHighlight(null)}
                        onClick={() => onSelect(project.id)}
                    >
                        <Swatch color={project.groupColor ?? MAP_COLOR.default} size={12} />
                        <Text size="sm" fw={500} style={{ flex: 1, minWidth: 0 }}>
                            {project.name}
                        </Text>
                        {project.project_number && (
                            <Text size="xs" c="dimmed" style={{ fontVariantNumeric: "tabular-nums" }}>
                                {project.project_number}
                            </Text>
                        )}
                    </UnstyledButton>
                ))}
            </Stack>
        </Stack>
    );
}
