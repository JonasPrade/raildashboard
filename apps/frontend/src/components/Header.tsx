import { useMemo } from "react";
import { ActionIcon, Button, Drawer, Group, Stack, useComputedColorScheme, useMantineColorScheme } from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { Link, NavLink } from "react-router-dom";
import { LogOut, Menu, Moon, Sun } from "lucide-react";
import { useAuth } from "../lib/auth";
import { LoginModal } from "../features/auth/LoginModal";
import {
    useTodos,
    useUnassignedFinves,
    useUnassignedGvfgEntries,
    useUnassignedInfraplanEntries,
    useUnassignedVibEntries,
} from "../shared/api/queries";
import { isOverdue } from "../features/todos/todoConstants";
import { useIsCompact } from "../shared/hooks/useBreakpoint";

// Same value as the 80em block for .app-header in app.css.
const NARROW_BAR_QUERY = "(max-width: 80em)";

type NavItem = {
    to: string;
    label: string;
    end?: boolean;
    visible: boolean;
    count?: number;
    // Red frame on the counter — only when the list holds something overdue
    // (status rule of the Anwendungsebene, W7 in feature-idt-design.md).
    overdue?: boolean;
};

/**
 * App bar of the IDT design (docs/DESIGN.md → Shell): paper surface, 2px ink
 * line, brand mark plus product name, text links with a violet underline on
 * the active entry, counters in an ink frame on violet-soft. Styles live in
 * app.css (`.app-header*`) so hover and the breakpoints stay in CSS.
 */
export function Header() {
    const { user, logout, can } = useAuth();
    const [loginOpened, { open: openLogin, close: closeLogin }] = useDisclosure(false);
    const [drawerOpened, { open: openDrawer, close: closeDrawer }] = useDisclosure(false);
    // Phones and small tablets navigate through the drawer; from 62em up the
    // entries plus the auth section fit into the bar.
    const isCompact = useIsCompact();

    // The Einstellungen entry is shown when the user holds any admin-area capability.
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

    // Aufgaben counter: every task that is not done — the same list the
    // tasks page shows without the done column. Red frame once one of them is
    // past its due date.
    const { data: openTodos } = useTodos({ include_done: false }, user !== null);
    const openTodoList = useMemo(
        () => (openTodos ?? []).filter((t) => t.status !== "DONE"),
        [openTodos],
    );
    const todosOverdue = openTodoList.some((t) => isOverdue(t.due_date));

    // One source of truth for both the bar and the drawer — they only differ in
    // the class they render with.
    const navItems: NavItem[] = [
        { to: "/", label: "Projekte", end: true, visible: true },
        { to: "/finanzen", label: "Finanzen", visible: true },
        { to: "/infraplan", label: "Infraplan", visible: true },
        { to: "/abgeordnete", label: "Abgeordnete", visible: user !== null },
        { to: "/tasks", label: "Aufgaben", visible: user !== null, count: openTodoList.length, overdue: todosOverdue },
        { to: "/admin", label: "Einstellungen", visible: canAdmin, count: totalUnassigned },
    ];

    const renderNavLinks = (className: string) =>
        navItems
            .filter((item) => item.visible)
            .map((item) => (
                <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) => (isActive ? `${className} is-active` : className)}
                    onClick={closeDrawer}
                >
                    {item.label}
                    {item.count !== undefined && item.count > 0 && (
                        <span
                            className={item.overdue ? "app-header__count is-overdue" : "app-header__count"}
                            aria-label={item.overdue ? `${item.count}, davon überfällige` : String(item.count)}
                        >
                            {item.count}
                        </span>
                    )}
                </NavLink>
            ));

    // Between 62em and 80em six entries, the auth section and the toggle only
    // fit when the logout shrinks to an icon (name in its label) — see the
    // 80em rule for .app-header in app.css.
    const isNarrowBar = useMediaQuery(NARROW_BAR_QUERY, false, { getInitialValueInEffect: false }) ?? false;
    const logoutLabel = user ? `Abmelden (${user.username})` : "Abmelden";
    const authSection = (inDrawer: boolean) =>
        user ? (
            !inDrawer && isNarrowBar ? (
                <ActionIcon variant="default" size={40} onClick={logout} aria-label={logoutLabel} title={logoutLabel}>
                    <LogOut size={20} aria-hidden />
                </ActionIcon>
            ) : (
                <Group gap="xs" wrap="nowrap">
                    <span className="app-header__user">{user.username}</span>
                    <Button variant="default" h={40} onClick={logout}>
                        Abmelden
                    </Button>
                </Group>
            )
        ) : (
            <Button h={40} onClick={() => { closeDrawer(); openLogin(); }}>
                Anmelden
            </Button>
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
            <div className="app-header">
                <Link to="/" className="app-header__brand">
                    <img src="/bildmarke.png" width={40} height={40} alt="" />
                    <span>Schienendashboard</span>
                </Link>
                {isCompact ? (
                    <div className="app-header__right">
                        {themeToggle}
                        <ActionIcon
                            variant="default"
                            size={40}
                            onClick={openDrawer}
                            aria-label="Navigation öffnen"
                            aria-expanded={drawerOpened}
                            title="Navigation öffnen"
                        >
                            <Menu size={20} aria-hidden />
                        </ActionIcon>
                    </div>
                ) : (
                    <>
                        <nav className="app-header__nav" aria-label="Hauptnavigation">
                            {renderNavLinks("app-header__link")}
                        </nav>
                        <div className="app-header__right">
                            {authSection(false)}
                            {themeToggle}
                        </div>
                    </>
                )}
            </div>

            <Drawer
                opened={drawerOpened}
                onClose={closeDrawer}
                title="Navigation"
                position="right"
                size={isCompact ? "80%" : "xs"}
            >
                <Stack gap={0} component="nav" aria-label="Hauptnavigation">
                    {renderNavLinks("app-drawer__link")}
                </Stack>
                <Group pt="md">{authSection(true)}</Group>
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
