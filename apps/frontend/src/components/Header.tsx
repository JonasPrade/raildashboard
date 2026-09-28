import React from "react";
import { Badge, Burger, Drawer, Group, Stack } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { NavLink } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { LoginModal } from "../features/auth/LoginModal";
import { useUnassignedFinves, useUnassignedVibEntries } from "../shared/api/queries";
import { useIsCompact } from "../shared/hooks/useBreakpoint";
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

// Drawer entries are thumb targets, not pointer targets: full width, 48px tall.
const drawerNavBase: React.CSSProperties = {
    ...navLinkBase,
    display: "flex",
    alignItems: "center",
    minHeight: 48,
    fontSize: "13px",
    padding: "12px",
    borderBottom: "1px solid var(--rule)",
};

const drawerNavActive: React.CSSProperties = {
    ...drawerNavBase,
    color: "var(--ink)",
    borderBottom: "2px solid var(--led)",
};

export function Header() {
    const { user, logout, can } = useAuth();
    const [loginOpened, { open: openLogin, close: closeLogin }] = useDisclosure(false);
    const [drawerOpened, { open: openDrawer, close: closeDrawer }] = useDisclosure(false);
    // Phones and small tablets navigate through the drawer; from 62em up the
    // five entries plus the auth section fit into the bar.
    const isCompact = useIsCompact();

    // The Admin entry is shown when the user holds any admin-area capability.
    const canAdmin =
        can("assignment.manage") ||
        can("haushalt.import") ||
        can("vib.import") ||
        can("project.create") ||
        can("projectgroup.create") ||
        can("projectgroup.edit") ||
        can("user.manage") ||
        can("role.manage");
    const canAssignments = can("assignment.manage");
    const { data: unassignedFinves } = useUnassignedFinves(canAssignments);
    const { data: unassignedVibEntries } = useUnassignedVibEntries(canAssignments);
    const totalUnassigned = canAssignments
        ? (unassignedFinves?.length ?? 0) + (unassignedVibEntries?.length ?? 0)
        : 0;

    // One source of truth for both the bar and the drawer — they only differ in
    // the style they render with.
    const navItems: Array<{ to: string; label: string; end?: boolean; visible: boolean; badge?: number }> = [
        { to: "/", label: "Projekte", end: true, visible: true },
        { to: "/finves", label: "Haushalt", visible: true },
        { to: "/abgeordnete", label: "Abgeordnete", visible: true },
        { to: "/tasks", label: "Aufgaben", visible: user !== null },
        { to: "/admin", label: "Admin", visible: canAdmin, badge: totalUnassigned },
    ];

    const renderNavLinks = (base: React.CSSProperties, active: React.CSSProperties) =>
        navItems
            .filter((item) => item.visible)
            .map((item) => (
                <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    style={({ isActive }) => (isActive ? active : base)}
                    onClick={closeDrawer}
                >
                    <Group gap={6} align="center" wrap="nowrap">
                        <span>▸ {item.label}</span>
                        {item.badge !== undefined && item.badge > 0 && (
                            <Badge color="gold.5" size="xs" variant="filled" circle styles={{ root: { color: "var(--ink)" } }}>
                                {item.badge}
                            </Badge>
                        )}
                    </Group>
                </NavLink>
            ));

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

    return (
        <>
            <Group
                justify="space-between"
                px="var(--page-pad)"
                py={6}
                wrap="nowrap"
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
                    style={{ display: "inline-flex", alignItems: "center", gap: 12, minWidth: 0 }}
                >
                    <Signet size={36} title="Schienendashboard" />
                    {/* Below 30em the wordmark would push the burger off screen —
                        the signet carries the brand there. */}
                    <span className="header-wordmark">
                        <Wordmark size="sm">Schienendashboard</Wordmark>
                    </span>
                </NavLink>
                {isCompact ? (
                    <Burger
                        opened={drawerOpened}
                        onClick={openDrawer}
                        aria-label="Navigation öffnen"
                        color="var(--ink)"
                        size="md"
                    />
                ) : (
                    <Group gap="xs" wrap="nowrap">
                        {renderNavLinks(navLinkBase, navLinkActive)}
                        {authSection}
                    </Group>
                )}
            </Group>

            <Drawer
                opened={drawerOpened}
                onClose={closeDrawer}
                title="Navigation"
                position="right"
                size={isCompact ? "80%" : "xs"}
            >
                <Stack gap={0}>
                    {renderNavLinks(drawerNavBase, drawerNavActive)}
                </Stack>
                <Group pt="md">{authSection}</Group>
            </Drawer>

            <LoginModal opened={loginOpened} onClose={closeLogin} />
        </>
    );
}
