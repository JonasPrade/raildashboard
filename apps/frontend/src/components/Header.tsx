import React from "react";
import { Burger, Drawer, Group, Stack } from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { NavLink } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { LoginModal } from "../features/auth/LoginModal";
import { ChronicleButton, ChronicleHeadline } from "./chronicle";

const desktopNavLinkStyle: React.CSSProperties = {
    textDecoration: "none",
    color: "rgba(255,255,255,0.75)",
    padding: "6px 12px",
    borderRadius: 2,
    fontWeight: 500,
    fontSize: "0.9375rem",
};

const desktopNavLinkActiveStyle: React.CSSProperties = {
    ...desktopNavLinkStyle,
    color: "#ffffff",
    borderBottom: "2px solid var(--c-secondary)",
};

const drawerNavLinkStyle: React.CSSProperties = {
    textDecoration: "none",
    color: "var(--c-on-surface)",
    padding: "8px 12px",
    borderRadius: 2,
    fontWeight: 500,
    fontSize: "0.9375rem",
    display: "block",
};

const drawerNavLinkActiveStyle: React.CSSProperties = {
    ...drawerNavLinkStyle,
    color: "var(--c-secondary)",
    borderBottom: "2px solid var(--c-secondary)",
};

export function Header() {
    const { user, logout } = useAuth();
    const [loginOpened, { open: openLogin, close: closeLogin }] = useDisclosure(false);
    const [drawerOpened, { open: openDrawer, close: closeDrawer }] = useDisclosure(false);
    const isMobile = useMediaQuery("(max-width: 100em)");

    const desktopNavLinks = (
        <>
            <NavLink to="/" end style={({ isActive }) => isActive ? desktopNavLinkActiveStyle : desktopNavLinkStyle} onClick={closeDrawer}>
                Projekte
            </NavLink>
            <NavLink to="/finves" style={({ isActive }) => isActive ? desktopNavLinkActiveStyle : desktopNavLinkStyle} onClick={closeDrawer}>
                Haushalt
            </NavLink>
            {(user?.role === "editor" || user?.role === "admin") && (
                <NavLink to="/admin/haushalt-import" style={({ isActive }) => isActive ? desktopNavLinkActiveStyle : desktopNavLinkStyle} onClick={closeDrawer}>
                    Haushalts-Import
                </NavLink>
            )}
            {(user?.role === "editor" || user?.role === "admin") && (
                <NavLink to="/admin/vib-import" style={({ isActive }) => isActive ? desktopNavLinkActiveStyle : desktopNavLinkStyle} onClick={closeDrawer}>
                    VIB-Import
                </NavLink>
            )}
            {user?.role === "admin" && (
                <NavLink to="/admin" style={({ isActive }) => isActive ? desktopNavLinkActiveStyle : desktopNavLinkStyle} onClick={closeDrawer}>
                    Administration
                </NavLink>
            )}
        </>
    );

    const drawerNavLinks = (
        <>
            <NavLink to="/" end style={({ isActive }) => isActive ? drawerNavLinkActiveStyle : drawerNavLinkStyle} onClick={closeDrawer}>
                Projekte
            </NavLink>
            <NavLink to="/finves" style={({ isActive }) => isActive ? drawerNavLinkActiveStyle : drawerNavLinkStyle} onClick={closeDrawer}>
                Haushalt
            </NavLink>
            {(user?.role === "editor" || user?.role === "admin") && (
                <NavLink to="/admin/haushalt-import" style={({ isActive }) => isActive ? drawerNavLinkActiveStyle : drawerNavLinkStyle} onClick={closeDrawer}>
                    Haushalts-Import
                </NavLink>
            )}
            {(user?.role === "editor" || user?.role === "admin") && (
                <NavLink to="/admin/vib-import" style={({ isActive }) => isActive ? drawerNavLinkActiveStyle : drawerNavLinkStyle} onClick={closeDrawer}>
                    VIB-Import
                </NavLink>
            )}
            {user?.role === "admin" && (
                <NavLink to="/admin" style={({ isActive }) => isActive ? drawerNavLinkActiveStyle : drawerNavLinkStyle} onClick={closeDrawer}>
                    Administration
                </NavLink>
            )}
        </>
    );

    const authSection = user ? (
        <Group gap="xs">
            <span style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.875rem" }}>
                {user.username}
            </span>
            <ChronicleButton
                variant="ghost"
                onClick={logout}
                style={{ color: "var(--c-on-primary)", borderColor: "rgba(255,255,255,0.2)", fontSize: "0.875rem", padding: "4px 12px" }}
            >
                Abmelden
            </ChronicleButton>
        </Group>
    ) : (
        <ChronicleButton
            variant="ghost"
            onClick={() => { closeDrawer(); openLogin(); }}
            style={{ color: "var(--c-on-primary)", borderColor: "rgba(255,255,255,0.2)" }}
        >
            Anmelden
        </ChronicleButton>
    );

    const drawerAuthSection = user ? (
        <Group gap="xs">
            <span style={{ fontSize: "0.875rem", color: "var(--c-on-surface)", opacity: 0.6 }}>
                {user.username}
            </span>
            <ChronicleButton variant="ghost" onClick={logout} style={{ fontSize: "0.875rem", padding: "4px 12px" }}>
                Abmelden
            </ChronicleButton>
        </Group>
    ) : (
        <ChronicleButton onClick={() => { closeDrawer(); openLogin(); }}>
            Anmelden
        </ChronicleButton>
    );

    return (
        <>
            <Group
                justify="space-between"
                px="md"
                py="xs"
                style={{ backgroundColor: "var(--c-primary)", height: "100%" }}
            >
                <NavLink to="/" className="header-title-link">
                    <ChronicleHeadline as="h1" style={{ color: "var(--c-on-primary)", fontSize: "1.25rem" }}>
                        Schienenprojekte-Dashboard
                    </ChronicleHeadline>
                </NavLink>
                {isMobile ? (
                    <Burger opened={drawerOpened} onClick={openDrawer} aria-label="Navigation öffnen" color="white" />
                ) : (
                    <Group gap="xs">
                        {desktopNavLinks}
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
                    {drawerNavLinks}
                    {drawerAuthSection}
                </Stack>
            </Drawer>

            <LoginModal opened={loginOpened} onClose={closeLogin} />
        </>
    );
}
