import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LegalPage from "./LegalPage";

const permissions = new Set<string>();
let settings: Record<string, unknown> = {};

vi.mock("../../lib/auth", () => ({
    useAuth: () => ({ can: (perm: string) => permissions.has(perm) }),
}));

vi.mock("../../shared/api/queries", () => ({
    useAppSettings: () => ({
        data: { map_group_mode: "preconfigured", ...settings },
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
    }),
}));

function renderPage(kind: "impressum" | "datenschutz") {
    return render(
        <MantineProvider>
            <MemoryRouter>
                <LegalPage kind={kind} />
            </MemoryRouter>
        </MantineProvider>,
    );
}

describe("LegalPage", () => {
    const replace = vi.fn();
    const originalLocation = window.location;

    beforeEach(() => {
        permissions.clear();
        settings = {};
        replace.mockReset();
        Object.defineProperty(window, "location", {
            configurable: true,
            value: { ...originalLocation, replace },
        });
    });

    afterEach(() => {
        Object.defineProperty(window, "location", { configurable: true, value: originalLocation });
    });

    it("renders the stored markdown under the page title", () => {
        settings = { impressum_markdown: "## Anschrift\n\nMusterstraße **1**" };
        renderPage("impressum");

        expect(screen.getByRole("heading", { level: 1, name: "Impressum" })).toBeInTheDocument();
        expect(screen.getByRole("heading", { level: 2, name: "Anschrift" })).toBeInTheDocument();
        expect(screen.getByText("1").tagName).toBe("STRONG");
        expect(replace).not.toHaveBeenCalled();
    });

    it("shows the empty state without an admin link for visitors", () => {
        renderPage("datenschutz");

        expect(screen.getByRole("heading", { level: 1, name: "Datenschutzerklärung" })).toBeInTheDocument();
        expect(screen.getByText("Noch keine Datenschutzerklärung hinterlegt")).toBeInTheDocument();
        expect(screen.queryByRole("link", { name: /Administration/ })).not.toBeInTheDocument();
    });

    it("links to the admin card in the empty state for settings.manage", () => {
        permissions.add("settings.manage");
        renderPage("impressum");

        expect(screen.getByText("Noch kein Impressum hinterlegt")).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /Administration/ })).toHaveAttribute(
            "href",
            "/admin#impressum-datenschutz",
        );
    });

    it("redirects with location.replace when a URL is set", () => {
        settings = { datenschutz_url: "https://example.org/datenschutz" };
        renderPage("datenschutz");

        expect(replace).toHaveBeenCalledWith("https://example.org/datenschutz");
    });
});
