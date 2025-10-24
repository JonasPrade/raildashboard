import { Group, Title } from "@mantine/core";
import { NavLink } from "react-router-dom";
import type { CSSProperties } from "react";

export function Header() {
    const baseStyle: CSSProperties = {
        textDecoration: "none",
        color: "inherit",
        padding: "6px 12px",
        borderRadius: 8,
        fontWeight: 500
    };

    return (
        <Group justify="space-between" px="md" py="xs">
            <Title order={2}>Railway projects dashboard</Title>
            <Group gap="xs">
                <NavLink
                    to="/"
                    end
                    style={({ isActive }) => ({
                        ...baseStyle,
                        backgroundColor: isActive ? "rgba(17, 34, 64, 0.08)" : "transparent"
                    })}
                >
                    Map
                </NavLink>
                <NavLink
                    to="/documentation"
                    style={({ isActive }) => ({
                        ...baseStyle,
                        backgroundColor: isActive ? "rgba(17, 34, 64, 0.08)" : "transparent"
                    })}
                >
                    Documentation
                </NavLink>
                <NavLink
                    to="/projects"
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