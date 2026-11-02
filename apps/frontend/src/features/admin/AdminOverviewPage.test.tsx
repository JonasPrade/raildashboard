import { render, screen, within } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminOverviewPage from "./AdminOverviewPage";

const permissions = new Set<string>();

vi.mock("../../lib/auth", () => ({
    useAuth: () => ({ can: (perm: string) => permissions.has(perm) }),
}));

const list = (n: number) => ({ data: Array.from({ length: n }, (_, i) => ({ id: i })) });

vi.mock("../../shared/api/queries", () => ({
    useAppSettings: () => ({
        data: { impressum_url: null, impressum_markdown: "Text", datenschutz_url: "https://example.org", datenschutz_markdown: null },
    }),
    useUnassignedFinves: () => list(2),
    useUnassignedVibEntries: () => list(1),
    useUnassignedGvfgEntries: () => list(0),
    useUnassignedInfraplanEntries: () => list(0),
    useProgressConflicts: () => list(4),
    useDraftProjects: () => list(0),
    useWorkerHealth: () => ({ data: { status: "ok" } }),
    useRoutineJobs: () => ({ data: { needs_attention: false, enabled: true } }),
}));

function renderPage() {
    return render(
        <MantineProvider>
            <MemoryRouter>
                <AdminOverviewPage />
            </MemoryRouter>
        </MantineProvider>,
    );
}

describe("AdminOverviewPage", () => {
    beforeEach(() => permissions.clear());

    it("groups tiles into sections and shows open counts on top", () => {
        ["assignment.manage", "progress.edit", "settings.manage", "user.manage"].forEach((p) => permissions.add(p));
        renderPage();

        expect(screen.getByRole("heading", { level: 2, name: "Zuordnen & prüfen" })).toBeInTheDocument();
        expect(screen.getByRole("heading", { level: 2, name: "Betrieb & Website" })).toBeInTheDocument();

        const todo = screen.getByRole("region", { name: "Zu erledigen" });
        expect(within(todo).getByRole("link", { name: /3\s*Einträge ohne Projekt/ })).toHaveAttribute("href", "/admin/unassigned");
        expect(within(todo).getByRole("link", { name: /4\s*Konflikte/ })).toBeInTheDocument();
    });

    it("links the legal tile to its own page with the current state", () => {
        permissions.add("settings.manage");
        renderPage();

        const tile = screen.getByRole("link", { name: /Impressum & Datenschutz/ });
        expect(tile).toHaveAttribute("href", "/admin/rechtliches");
        expect(within(tile).getByText("Impressum: eigene Seite · Datenschutz: Weiterleitung")).toBeInTheDocument();
    });

    it("hides sections without a permitted tile", () => {
        permissions.add("mcp.access");
        renderPage();

        expect(screen.getByRole("heading", { level: 2, name: "Zugang & Rechte" })).toBeInTheDocument();
        expect(screen.queryByRole("heading", { level: 2, name: "Projekte" })).not.toBeInTheDocument();
        expect(screen.queryByRole("region", { name: "Zu erledigen" })).not.toBeInTheDocument();
    });
});
