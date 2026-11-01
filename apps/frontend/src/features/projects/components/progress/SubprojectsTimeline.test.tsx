import { fireEvent, render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SubprojectsTimeline from "./SubprojectsTimeline";

const api = vi.hoisted(() => vi.fn());
vi.mock("../../../../shared/api/client", () => ({ api }));

function renderTimeline() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
        <QueryClientProvider client={client}>
            <MantineProvider>
                <MemoryRouter>
                    <SubprojectsTimeline projectId={7} count={3} />
                </MemoryRouter>
            </MantineProvider>
        </QueryClientProvider>,
    );
}

const row = (id: number, name: string, ibn: string) => ({
    project_id: id,
    name,
    project_number: null,
    superior_project_id: 7,
    lifecycle_status: "AKTIV",
    milestones: [
        { kind: "PHASE", phase: "BAU", date: "2028-01-01", source: "Manuell", certainty: "CONCRETE", date_precision: "MONTH" },
        { kind: "PHASE", phase: "IN_BETRIEB", date: ibn, source: "Manuell", certainty: "CONCRETE", date_precision: "MONTH" },
    ],
    construction_periods: [],
    pending_parts: [],
});

beforeEach(() => api.mockReset());

describe("SubprojectsTimeline", () => {
    it("loads nothing until it is opened", () => {
        renderTimeline();
        expect(screen.getByRole("button", { name: /Zeitstrahl der Unterprojekte \(3\)/ })).toHaveAttribute(
            "aria-expanded",
            "false",
        );
        expect(api).not.toHaveBeenCalled();
    });

    it("shows one row per subproject, sorted by commissioning, and names the undated ones", async () => {
        api.mockResolvedValue({
            project_id: 7,
            items: [row(2, "Etappe 2", "2031-07-01"), row(1, "Etappe 1", "2028-07-01")],
            without_dates: [{ project_id: 3, name: "Etappe 3" }],
        });
        renderTimeline();
        fireEvent.click(screen.getByRole("button", { name: /Zeitstrahl der Unterprojekte/ }));

        await screen.findByRole("link", { name: "Etappe 1" });
        expect(api).toHaveBeenCalledWith("/api/v1/projects/7/subprojects/timeline");
        const names = screen.getAllByRole("img").map((el) => el.getAttribute("aria-label")?.split(":")[0]);
        expect(names).toEqual(["Etappe 1", "Etappe 2"]);
        expect(screen.getByText(/Ohne belastbare Termine \(1\)/)).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "Etappe 3" })).toHaveAttribute("href", "/projects/3");
    });

    it("says so when no subproject has dates", async () => {
        api.mockResolvedValue({ project_id: 7, items: [], without_dates: [] });
        renderTimeline();
        fireEvent.click(screen.getByRole("button", { name: /Zeitstrahl der Unterprojekte/ }));
        expect(await screen.findByText("Noch kein Unterprojekt hat belastbare Termine.")).toBeInTheDocument();
    });
});
