import { Link } from "react-router-dom";

import { type Project } from "../../shared/api/queries";
import { ChronicleCard, ChronicleDataChip } from "../../components/chronicle";

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
