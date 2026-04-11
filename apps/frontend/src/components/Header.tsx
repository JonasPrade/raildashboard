import React from "react";
import { Burger, Button, Drawer, Group, Stack, Text, Title } from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { NavLink } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { LoginModal } from "../features/auth/LoginModal";

const baseStyle: React.CSSProperties = {
    textDecoration: "none",
    color: "inherit",
    padding: "6px 12px",
    borderRadius: 8,
    fontWeight: 500,
};


export function Header() {
    const { user, logout } = useAuth();
    const [loginOpened, { open: openLogin, close: closeLogin }] = useDisclosure(false);
    const [drawerOpened, { open: openDrawer, close: closeDrawer }] = useDisclosure(false);
    const isMobile = useMediaQuery("(max-width: 100em)");

    const navLinks = (
        <>
            <NavLink
                to="/"
                end
                style={({ isActive }) => ({
                    ...baseStyle,
                    backgroundColor: isActive ? "rgba(17, 34, 64, 0.08)" : "transparent",
                })}
                onClick={closeDrawer}
            >
                Projekte
            </NavLink>
            <NavLink
                to="/finves"
                style={({ isActive }) => ({
                    ...baseStyle,
                    backgroundColor: isActive ? "rgba(17, 34, 64, 0.08)" : "transparent",
                })}
                onClick={closeDrawer}
            >
                Haushalt
            </NavLink>
{(user?.role === "editor" || user?.role === "admin") && (
                <NavLink
                    to="/admin/haushalt-import"
                    style={({ isActive }) => ({
                        ...baseStyle,
                        backgroundColor: isActive ? "rgba(17, 34, 64, 0.08)" : "transparent",
                    })}
                    onClick={closeDrawer}
                >
                    Haushalts-Import
                </NavLink>
            )}
            {(user?.role === "editor" || user?.role === "admin") && (
                <NavLink
                    to="/admin/vib-import"
                    style={({ isActive }) => ({
                        ...baseStyle,
                        backgroundColor: isActive ? "rgba(17, 34, 64, 0.08)" : "transparent",
                    })}
                    onClick={closeDrawer}
                >
                    VIB-Import
                </NavLink>
            )}
            {user?.role === "admin" && (
                <NavLink
                    to="/admin"
                    style={({ isActive }) => ({
                        ...baseStyle,
                        backgroundColor: isActive ? "rgba(17, 34, 64, 0.08)" : "transparent",
                    })}
                    onClick={closeDrawer}
                >
                    Administration
                </NavLink>
            )}
        </>
    );

    const authSection = user ? (
        <Group gap="xs">
            <Text size="sm" c="dimmed">
                {user.username}
            </Text>
            <Button variant="subtle" size="xs" onClick={logout}>
                Abmelden
            </Button>
        </Group>
    ) : (
        <Button variant="subtle" size="sm" onClick={() => { closeDrawer(); openLogin(); }}>
            Anmelden
        </Button>
    );

    return (
        <>
            <Group justify="space-between" px="md" py="xs">
                <NavLink to="/" className="header-title-link"><Title order={2}>Schienenprojekte-Dashboard</Title></NavLink>
                {isMobile ? (
                    <Burger opened={drawerOpened} onClick={openDrawer} aria-label="Navigation öffnen" />
                ) : (
                    <Group gap="xs">
                        {navLinks}
                        {authSection}
                    </Group>
                )}
            </Group>

            <Drawer
                opened={drawerOpened}
                onClose={closeDrawer}
                title="Navigation"
                position="right"
                size="xs"
            >
                <Stack gap="xs">
                    {navLinks}
                    {authSection}
                </Stack>
            </Drawer>

            <LoginModal opened={loginOpened} onClose={closeLogin} />
        </>
    );
}
