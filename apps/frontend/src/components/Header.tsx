import { Group, Title } from "@mantine/core";
import { NavLink, useLocation, useSearchParams } from "react-router-dom";
import type { CSSProperties } from "react";

export function Header() {
    const { pathname } = useLocation();
    const [searchParams] = useSearchParams();

    const baseStyle: CSSProperties = {
        textDecoration: "none",
        color: "inherit",
        padding: "6px 12px",
        borderRadius: 8,
        fontWeight: 500
    };

    // When navigating from the map, carry the active group filter to the projects page
    const groupParam = searchParams.get("group");
    const projectsTo = pathname === "/" && groupParam ? `/projects?group=${groupParam}` : "/projects";

    return (
        <Group justify="space-between" px="md" py="xs">
            <Title order={2}>Schienenprojekte-Dashboard</Title>
            <Group gap="xs">
                <NavLink
                    to="/"
                    end
                    style={({ isActive }) => ({
                        ...baseStyle,
                        backgroundColor: isActive ? "rgba(17, 34, 64, 0.08)" : "transparent"
                    })}
                >
                    Karte
                </NavLink>
                <NavLink
                    to={projectsTo}
                    style={({ isActive }) => ({
                        ...baseStyle,
                        backgroundColor: isActive ? "rgba(17, 34, 64, 0.08)" : "transparent"
                    })}
                >
                    Projekte
                </NavLink>
            </Group>
        </Group>
    );
}
