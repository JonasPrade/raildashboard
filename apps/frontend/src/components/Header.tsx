import { Group, Title } from "@mantine/core";
import { NavLink } from "react-router-dom";
import type { CSSProperties } from "react";

const baseStyle: CSSProperties = {
    textDecoration: "none",
    color: "inherit",
    padding: "6px 12px",
    borderRadius: 8,
    fontWeight: 500,
};

const disabledStyle: CSSProperties = {
    ...baseStyle,
    color: "rgba(0, 0, 0, 0.3)",
    cursor: "not-allowed",
};

export function Header() {
    return (
        <Group justify="space-between" px="md" py="xs">
            <Title order={2}>Schienenprojekte-Dashboard</Title>
            <Group gap="xs">
                <NavLink
                    to="/"
                    end
                    style={({ isActive }) => ({
                        ...baseStyle,
                        backgroundColor: isActive ? "rgba(17, 34, 64, 0.08)" : "transparent",
                    })}
                >
                    Projekte
                </NavLink>
                <span style={disabledStyle} title="Noch nicht verfügbar">
                    Beschleunigungskommission Schiene - todo
                </span>
                <span style={disabledStyle} title="Noch nicht verfügbar">
                    Haushalt und Finanzierung - todo
                </span>
            </Group>
        </Group>
    );
}
