import React from "react";
import { ActionIcon, Badge, Burger, Button, Drawer, Group, Stack, useComputedColorScheme, useMantineColorScheme } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { NavLink } from "react-router-dom";
import { Moon, Sun } from "lucide-react";
import { useAuth } from "../lib/auth";
import { LoginModal } from "../features/auth/LoginModal";
import {
    useUnassignedFinves,
    useUnassignedGvfgEntries,
    useUnassignedInfraplanEntries,
    useUnassignedVibEntries,
} from "../shared/api/queries";
import { useIsCompact } from "../shared/hooks/useBreakpoint";
import { ChronicleButton } from "./chronicle";
import { Wordmark, Signet } from "./tafel";

const navLinkBase: React.CSSProperties = {
    textDecoration: "none",
    color: "var(--text-body)",
    padding: "8px 12px",
    fontFamily: "var(--font-mono)",
    fontWeight: 700,
    fontSize: "12px",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
};

const navLinkActive: React.CSSProperties = {
    ...navLinkBase,
    color: "var(--text-strong)",
    borderBottom: "2px solid var(--accent-primary)",
};

// Drawer entries are thumb targets, not pointer targets: full width, 48px tall.
const drawerNavBase: React.CSSProperties = {
    ...navLinkBase,
    display: "flex",
    alignItems: "center",
    minHeight: 48,
    fontSize: "13px",
    padding: "12px",
    borderBottom: "1px solid var(--border)",
};

const drawerNavActive: React.CSSProperties = {
    ...drawerNavBase,
    color: "var(--text-strong)",
    borderBottom: "2px solid var(--accent-primary)",
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
        can("gvfg.import") ||
        can("infraplan.import") ||
        can("vib.import") ||
        can("project.create") ||
        can("projectgroup.create") ||
        can("projectgroup.edit") ||
        can("user.manage") ||
        can("role.manage") ||
        can("parliament.import") ||
        can("mcp.access");
    const canAssignments = can("assignment.manage");
    const { data: unassignedFinves } = useUnassignedFinves(canAssignments);
    const { data: unassignedVibEntries } = useUnassignedVibEntries(canAssignments);
    const { data: unassignedGvfgEntries } = useUnassignedGvfgEntries(canAssignments);
    const { data: unassignedInfraplanEntries } = useUnassignedInfraplanEntries(canAssignments);
    const totalUnassigned = canAssignments
        ? (unassignedFinves?.length ?? 0) +
          (unassignedVibEntries?.length ?? 0) +
          (unassignedGvfgEntries?.length ?? 0) +
          (unassignedInfraplanEntries?.length ?? 0)
        : 0;

    // One source of truth for both the bar and the drawer — they only differ in
    // the style they render with.
    const navItems: Array<{ to: string; label: string; end?: boolean; visible: boolean; badge?: number }> = [
        { to: "/", label: "Projekte", end: true, visible: true },
        { to: "/finanzen", label: "Finanzen", visible: true },
        { to: "/infraplan", label: "Infraplan", visible: true },
        { to: "/abgeordnete", label: "Abgeordnete", visible: user !== null },
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
                            <Badge color="violet" size="xs" variant="filled" circle>
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
                letterSpacing: "var(--ls-label)",
                textTransform: "uppercase",
                color: "var(--text-muted)",
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

    // Dark mode: default follows the system, the toggle stores an explicit choice
    // (docs/DESIGN.md → Dunkelfassung).
    const { setColorScheme } = useMantineColorScheme();
    const isDark = useComputedColorScheme("light") === "dark";
    const toggleColorScheme = () => setColorScheme(isDark ? "light" : "dark");
    const themeToggleLabel = isDark ? "Hellfassung einschalten" : "Dunkelfassung einschalten";
    const themeToggle = (
        <ActionIcon
            variant="default"
            size={40}
            onClick={toggleColorScheme}
            aria-label={themeToggleLabel}
            title={themeToggleLabel}
        >
            {isDark ? <Sun size={20} aria-hidden /> : <Moon size={20} aria-hidden />}
        </ActionIcon>
    );

    return (
        <>
            <Group
                justify="space-between"
                px="var(--page-pad)"
                py={6}
                wrap="nowrap"
                style={{
                    backgroundColor: "var(--surface)",
                    height: "100%",
                    borderTop: "2px solid var(--border-frame)",
                    borderBottom: "1px solid var(--border)",
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
                    <Group gap="xs" wrap="nowrap">
                        {themeToggle}
                        <Burger
                            opened={drawerOpened}
                            onClick={openDrawer}
                            aria-label="Navigation öffnen"
                            color="var(--text-strong)"
                            size="md"
                        />
                    </Group>
                ) : (
                    <Group gap="xs" wrap="nowrap">
                        {renderNavLinks(navLinkBase, navLinkActive)}
                        {authSection}
                        {themeToggle}
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
                <Button
                    mt="md"
                    variant="default"
                    leftSection={isDark ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
                    onClick={toggleColorScheme}
                >
                    {themeToggleLabel}
                </Button>
            </Drawer>

            <LoginModal opened={loginOpened} onClose={closeLogin} />
        </>
    );
}
