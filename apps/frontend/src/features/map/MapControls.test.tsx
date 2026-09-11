import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { describe, it, expect, afterEach, vi } from "vitest";

import MapControls from "./MapControls";
import { MOBILE_QUERY } from "../../shared/hooks/useBreakpoint";

const originalMatchMedia = window.matchMedia;

function mockViewport({ mobile }: { mobile: boolean }) {
    Object.defineProperty(window, "matchMedia", {
        writable: true,
        value: (query: string) => ({
            matches: mobile && query === MOBILE_QUERY,
            media: query,
            onchange: null,
            addEventListener: () => {},
            removeEventListener: () => {},
            addListener: () => {},
            removeListener: () => {},
            dispatchEvent: () => false,
        }),
    });
}

afterEach(() => {
    Object.defineProperty(window, "matchMedia", { writable: true, value: originalMatchMedia });
});

function renderControls() {
    return render(
        <MantineProvider>
            <MapControls
                onOpenFilters={vi.fn()}
                lineWidth={4}
                onLineWidthChange={vi.fn()}
                pointSize={5}
                onPointSizeChange={vi.fn()}
                onlySuperior
                onOnlySuperiorChange={vi.fn()}
                searchTerm=""
                onSearchChange={vi.fn()}
                totalProjects={42}
                filteredCount={42}
                showConstituencies={false}
                onShowConstituenciesChange={vi.fn()}
            />
        </MantineProvider>,
    );
}

describe("MapControls", () => {
    it("shows the full control panel on a desktop viewport", () => {
        mockViewport({ mobile: false });
        renderControls();

        expect(screen.getByPlaceholderText("Projekt suchen…")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Projektgruppen" })).toBeInTheDocument();
        expect(screen.getByLabelText("Wahlkreise")).toBeInTheDocument();
    });

    it("keeps only the search field on the map and moves the settings into a sheet on a phone", () => {
        mockViewport({ mobile: true });
        renderControls();

        expect(screen.getByPlaceholderText("Projekt suchen…")).toBeInTheDocument();
        expect(screen.getByLabelText("Karteneinstellungen öffnen")).toBeInTheDocument();
        // The layer switches live in the closed bottom sheet, not over the map.
        expect(screen.queryByLabelText("Wahlkreise")).not.toBeInTheDocument();
        expect(screen.queryByRole("button", { name: "Projektgruppen" })).not.toBeInTheDocument();
    });
});
