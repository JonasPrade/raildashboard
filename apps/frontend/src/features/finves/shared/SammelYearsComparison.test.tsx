import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { SammelYearsComparison } from "./SammelYearsComparison";

const data = {
    finve_id: 763,
    name: "SV Lph. 1/2 A",
    starting_year: 2012,
    years: [
        {
            year: 2025,
            previous_year: null,
            added: [],
            kept: [{ id: 1, name: "ABS Alt" }, { id: 2, name: "NBS Bleibt" }],
            removed: [],
        },
        {
            year: 2026,
            previous_year: 2025,
            added: [{ id: 3, name: "NBS Neu" }],
            kept: [{ id: 2, name: "NBS Bleibt" }],
            removed: [{ id: 1, name: "ABS Alt" }],
        },
    ],
};

vi.mock("../../../shared/api/queries", () => ({
    useSammelFinveYears: () => ({ data, isLoading: false, isError: false, refetch: vi.fn() }),
}));
vi.mock("../../projects/ProjectHoverCard", () => ({
    default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

function renderComparison() {
    return render(
        <MantineProvider>
            <MemoryRouter>
                <SammelYearsComparison finveId={763} />
            </MemoryRouter>
        </MantineProvider>,
    );
}

function column(label: string) {
    return screen.getByText(label).closest("div[class*='Stack']") as HTMLElement;
}

describe("SammelYearsComparison", () => {
    it("shows the newest edition split into new, kept and dropped projects", () => {
        renderComparison();
        expect(screen.getByText("im Vergleich zu 2025")).toBeInTheDocument();
        expect(within(column("Neu aufgenommen")).getByText("NBS Neu")).toBeInTheDocument();
        expect(within(column("Weiterhin enthalten")).getByText("NBS Bleibt")).toBeInTheDocument();
        expect(within(column("Nicht mehr enthalten")).getByText("ABS Alt")).toBeInTheDocument();
    });

    it("marks the earliest edition as having no previous year", async () => {
        renderComparison();
        await userEvent.click(screen.getByText("2025"));
        expect(screen.getByText(/kein Vorjahr zum Vergleich/)).toBeInTheDocument();
        expect(within(column("Enthalten")).getByText("ABS Alt")).toBeInTheDocument();
    });
});
