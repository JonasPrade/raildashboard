import { Button, Group, Text, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { NavLink } from "react-router-dom";
import type { CSSProperties } from "react";
import { useAuth } from "../lib/auth";
import { LoginModal } from "../features/auth/LoginModal";

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
    const { user, logout } = useAuth();
    const [loginOpened, { open: openLogin, close: closeLogin }] = useDisclosure(false);

    return (
        <>
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
                    {user?.role === "admin" && (
                        <NavLink
                            to="/admin"
                            style={({ isActive }) => ({
                                ...baseStyle,
                                backgroundColor: isActive ? "rgba(17, 34, 64, 0.08)" : "transparent",
                            })}
                        >
                            Administration
                        </NavLink>
                    )}
                    {user ? (
                        <Group gap="xs">
                            <Text size="sm" c="dimmed">
                                {user.username}
                            </Text>
                            <Button variant="subtle" size="xs" onClick={logout}>
                                Abmelden
                            </Button>
                        </Group>
                    ) : (
                        <Button variant="subtle" size="sm" onClick={openLogin}>
                            Anmelden
                        </Button>
                    )}
                </Group>
            </Group>
            <LoginModal opened={loginOpened} onClose={closeLogin} />
        </>
    );
}
