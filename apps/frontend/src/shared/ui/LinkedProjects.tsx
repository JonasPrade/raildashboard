import { Link } from "react-router-dom";
import { Group, Stack, Text } from "@mantine/core";

export interface LinkedProject {
    id: number;
    name: string;
}

/** "Verknüpfte Projekte": one bordered link button per project (FinVe and Infraplan cards). */
export function LinkedProjects({ projects }: { projects: LinkedProject[] }) {
    if (projects.length === 0) return null;
    return (
        <Stack gap={6}>
            <Text size="xs" c="dimmed" fw={500} tt="uppercase" style={{ letterSpacing: "0.05em" }}>
                Verknüpfte Projekte
            </Text>
            <Group gap="xs" wrap="wrap">
                {projects.map((p) => (
                    <Link
                        key={p.id}
                        to={`/projects/${p.id}`}
                        style={{
                            textDecoration: "none",
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 6,
                            padding: "4px 8px",
                            border: "1px solid var(--mantine-color-default-border)",
                            borderRadius: 4,
                            transition: "background 0.15s",
                        }}
                    >
                        <Text size="xs" c="dimmed" ff="monospace">{p.id}</Text>
                        <Text size="xs" fw={500} c="dark">{p.name}</Text>
                    </Link>
                ))}
            </Group>
        </Stack>
    );
}
