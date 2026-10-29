import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BauportalSection from "./BauportalSection";

const api = vi.hoisted(() => vi.fn());
vi.mock("../../../shared/api/client", () => ({ api }));

function renderSection() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
        <QueryClientProvider client={client}>
            <MantineProvider>
                <BauportalSection projectId={7} />
            </MantineProvider>
        </QueryClientProvider>,
    );
}

const entry = (id: number, over: Record<string, unknown> = {}) => ({
    id,
    bauportal_id: 100 + id,
    shorttitle: `Bauprojekt ${id}`,
    status_raw: "Projekt in der Bauphase",
    mapped_phase: "BAU",
    projecttime_raw: "2024 – 2026",
    url: `https://bauprojekte.deutschebahn.com/p/${id}`,
    fetched_at: "2026-10-20T08:00:00",
    ...over,
});

beforeEach(() => api.mockReset());

describe("BauportalSection", () => {
    it("shows the card with an external link, status, Bauzeit and Stand", async () => {
        api.mockResolvedValue([entry(1), entry(2)]);
        const { container } = renderSection();
        const link = await screen.findByRole("link", { name: "Bauprojekt 1" });
        expect(link).toHaveAttribute("href", "https://bauprojekte.deutschebahn.com/p/1");
        expect(link).toHaveAttribute("target", "_blank");
        expect(link).toHaveAttribute("rel", "noopener noreferrer");
        expect(screen.getByRole("heading", { name: "DB-Bauportal" })).toBeInTheDocument();
        expect(screen.getAllByTestId("bauportal-entry")).toHaveLength(2);
        expect(screen.getAllByText("Projekt in der Bauphase")).toHaveLength(2);
        expect(screen.getAllByText("Bauzeit: 2024 – 2026")).toHaveLength(2);
        expect(container.textContent).toContain("Stand:");
    });

    it("renders nothing when no entry has a link", async () => {
        api.mockResolvedValue([entry(1, { url: null })]);
        const { container } = renderSection();
        await vi.waitFor(() => expect(api).toHaveBeenCalled());
        expect(screen.queryByText("DB-Bauportal")).not.toBeInTheDocument();
        expect(container.querySelector(".mantine-Paper-root")).toBeNull();
    });

    it("renders nothing for an empty list", async () => {
        api.mockResolvedValue([]);
        const { container } = renderSection();
        await vi.waitFor(() => expect(api).toHaveBeenCalled());
        expect(screen.queryByText("DB-Bauportal")).not.toBeInTheDocument();
        expect(container.querySelector(".mantine-Paper-root")).toBeNull();
    });

    it("only lists entries with a link", async () => {
        api.mockResolvedValue([entry(1, { url: null }), entry(2)]);
        renderSection();
        expect(await screen.findByRole("link", { name: "Bauprojekt 2" })).toBeInTheDocument();
        expect(screen.queryByText("Bauprojekt 1")).not.toBeInTheDocument();
    });
});
