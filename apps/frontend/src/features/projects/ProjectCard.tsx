import type { CSSProperties } from "react";
import { Badge, Paper, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";

import { type ProjectOverview } from "../../shared/api/queries";
import { usePrefetchProjectPage } from "./usePrefetchProjectPage";
import PhaseBadge from "./components/progress/PhaseBadge";

export function ProjectCard({ project }: { project: ProjectOverview }) {
    const lengthValue = typeof project.length === "number" ? `${project.length.toLocaleString("de-DE")}` : null;
    const hasProjectId = typeof project.id === "number" && Number.isFinite(project.id);
    const prefetchProjectPage = usePrefetchProjectPage();

    const cardContent = (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {/* Only list items carry the stored headline phase (undefined elsewhere). */}
                {project.headline_phase !== undefined && (
                    <PhaseBadge phase={project.headline_phase} lifecycle={project.lifecycle_status} />
                )}
                <Title order={3}>{project.name}</Title>
                {project.project_number && (
                    <Text size="sm" c="dimmed">
                        Nr. {project.project_number}
                    </Text>
                )}
            </div>

            {project.description ? (
                <p
                    style={{
                        fontFamily: "var(--font-sans)",
                        fontSize: "15px",
                        lineHeight: 1.65,
                        color: "var(--text-body)",
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
                        color: "var(--text-muted)",
                        margin: 0,
                    }}
                >
                    Keine Projektbeschreibung vorhanden.
                </p>
            )}

            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {lengthValue && <Badge variant="outline">Länge: {lengthValue} km</Badge>}
                {project.elektrification && <Badge variant="outline">Elektrifizierung</Badge>}
                {project.second_track && <Badge variant="outline">Zweigleisiger Ausbau</Badge>}
                {project.new_station && <Badge variant="outline">Neuer Bahnhof</Badge>}
            </div>
        </div>
    );

    if (hasProjectId) {
        const prefetch = () => prefetchProjectPage(project.id as number);
        return (
            <Link
                to={`/projects/${project.id}`}
                style={{ textDecoration: "none", display: "block" }}
                onMouseEnter={prefetch}
                onFocus={prefetch}
                onTouchStart={prefetch}
            >
                <Paper withBorder p="var(--card-pad)" style={{ "--card-accent": "var(--accent-primary)" } as CSSProperties}>
                    {cardContent}
                </Paper>
            </Link>
        );
    }
    return (
        <Paper withBorder p="var(--card-pad)">
            {cardContent}
        </Paper>
    );
}
