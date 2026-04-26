import React from "react";
import { Badge, Burger, Drawer, Group, Stack } from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { NavLink } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { LoginModal } from "../features/auth/LoginModal";
import { useUnassignedFinves, useUnassignedVibEntries } from "../shared/api/queries";
import { ChronicleButton } from "./chronicle";
import { Wordmark, Signet } from "./tafel";

const navLinkBase: React.CSSProperties = {
    textDecoration: "none",
    color: "var(--ink2)",
    padding: "8px 12px",
    fontFamily: "var(--font-mono)",
    fontWeight: 700,
    fontSize: "12px",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
};

const navLinkActive: React.CSSProperties = {
    ...navLinkBase,
    color: "var(--ink)",
    borderBottom: "2px solid var(--led)",
};

const drawerNavBase: React.CSSProperties = {
    ...navLinkBase,
    display: "block",
    padding: "10px 12px",
};

const drawerNavActive: React.CSSProperties = {
    ...drawerNavBase,
    color: "var(--ink)",
    borderBottom: "2px solid var(--led)",
};

export function Header() {
    const { user, logout } = useAuth();
    const [loginOpened, { open: openLogin, close: closeLogin }] = useDisclosure(false);
    const [drawerOpened, { open: openDrawer, close: closeDrawer }] = useDisclosure(false);
    const isMobile = useMediaQuery("(max-width: 100em)");

    const isEditorOrAdmin = user?.role === "editor" || user?.role === "admin";
    const { data: unassignedFinves } = useUnassignedFinves(isEditorOrAdmin);
    const { data: unassignedVibEntries } = useUnassignedVibEntries(isEditorOrAdmin);
    const totalUnassigned = isEditorOrAdmin
        ? (unassignedFinves?.length ?? 0) + (unassignedVibEntries?.length ?? 0)
        : 0;

    const desktopNavLinks = (
        <>
            <NavLink to="/" end style={({ isActive }) => isActive ? navLinkActive : navLinkBase} onClick={closeDrawer}>
                ▸ Projekte
            </NavLink>
            <NavLink to="/finves" style={({ isActive }) => isActive ? navLinkActive : navLinkBase} onClick={closeDrawer}>
                ▸ Haushalt
            </NavLink>
            {isEditorOrAdmin && (
                <NavLink to="/admin" style={({ isActive }) => isActive ? navLinkActive : navLinkBase} onClick={closeDrawer}>
                    <Group gap={6} align="center" wrap="nowrap">
                        <span>▸ Admin</span>
                        {totalUnassigned > 0 && (
                            <Badge color="gold.5" size="xs" variant="filled" circle styles={{ root: { color: "var(--ink)" } }}>
                                {totalUnassigned}
                            </Badge>
                        )}
                    </Group>
                </NavLink>
            )}
        </>
    );

    const drawerNavLinks = (
        <>
            <NavLink to="/" end style={({ isActive }) => isActive ? drawerNavActive : drawerNavBase} onClick={closeDrawer}>
                ▸ Projekte
            </NavLink>
            <NavLink to="/finves" style={({ isActive }) => isActive ? drawerNavActive : drawerNavBase} onClick={closeDrawer}>
                ▸ Haushalt
            </NavLink>
            {isEditorOrAdmin && (
                <NavLink to="/admin" style={({ isActive }) => isActive ? drawerNavActive : drawerNavBase} onClick={closeDrawer}>
                    <Group gap={6} align="center" wrap="nowrap">
                        <span>▸ Admin</span>
                        {totalUnassigned > 0 && (
                            <Badge color="gold.5" size="xs" variant="filled" circle styles={{ root: { color: "var(--ink)" } }}>
                                {totalUnassigned}
                            </Badge>
                        )}
                    </Group>
                </NavLink>
            )}
        </>
    );

    const userBadge = user && (
        <span
            style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10.5px",
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: "var(--ink3)",
                fontWeight: 700,
            }}
        >
            ▸ {user.username}
        </span>
    );

    const authSection = user ? (
        <Group gap="xs">
            {userBadge}
            <ChronicleButton variant="ghost" size="sm" onClick={logout}>
                Abmelden
            </ChronicleButton>
        </Group>
    ) : (
        <ChronicleButton variant="primary" size="sm" onClick={() => { closeDrawer(); openLogin(); }}>
            Anmelden
        </ChronicleButton>
    );

    const drawerAuthSection = user ? (
        <Group gap="xs">
            {userBadge}
            <ChronicleButton variant="ghost" size="sm" onClick={logout}>
                Abmelden
            </ChronicleButton>
        </Group>
    ) : (
        <ChronicleButton variant="primary" size="sm" onClick={() => { closeDrawer(); openLogin(); }}>
            Anmelden
        </ChronicleButton>
    );

    return (
        <>
            <Group
                justify="space-between"
                px="md"
                py={6}
                style={{
                    backgroundColor: "var(--bg)",
                    height: "100%",
                    borderTop: "2px solid var(--ink)",
                    borderBottom: "1px solid var(--rule)",
                }}
            >
                <NavLink
                    to="/"
                    className="header-title-link"
                    style={{ display: "inline-flex", alignItems: "center", gap: 12 }}
                >
                    <Signet size={36} title="Schienendashboard" />
                    <Wordmark size="sm">Schienendashboard</Wordmark>
                </NavLink>
                {isMobile ? (
                    <Burger
                        opened={drawerOpened}
                        onClick={openDrawer}
                        aria-label="Navigation öffnen"
                        color="var(--ink)"
                    />
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
