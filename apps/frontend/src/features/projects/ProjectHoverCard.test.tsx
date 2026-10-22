import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Link } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ProjectHoverCard from "./ProjectHoverCard";

const api = vi.hoisted(() => vi.fn());
vi.mock("../../shared/api/client", () => ({ api }));
// The progress strip has its own query; not under test here.
vi.mock("./components/progress/ProgressMini", () => ({ default: () => null }));
// Warming the detail page chunk is irrelevant (and slow) in tests.
vi.mock("./ProjectDetail", () => ({ default: () => null }));

const originalMatchMedia = window.matchMedia;

function setCanHover(canHover: boolean) {
    window.matchMedia = ((query: string) => ({
        matches: canHover && query.includes("hover: hover"),
        media: query,
        onchange: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
}

function renderLink() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 5 * 60 * 1000 } } });
    return render(
        <QueryClientProvider client={client}>
            <MantineProvider>
                <MemoryRouter>
                    <ProjectHoverCard projectId={7}>
                        <Link to="/projects/7">Knoten Köln</Link>
                    </ProjectHoverCard>
                </MemoryRouter>
            </MantineProvider>
        </QueryClientProvider>,
    );
}

beforeEach(() => {
    api.mockReset();
    api.mockResolvedValue({ id: 7, name: "Knoten Köln", project_number: "K-003-V01", description: "Ausbau" });
});

afterEach(() => {
    window.matchMedia = originalMatchMedia;
});

describe("ProjectHoverCard", () => {
    it("loads the project only on hover and shows its Kurzansicht", async () => {
        setCanHover(true);
        renderLink();
        expect(api).not.toHaveBeenCalled();

        await userEvent.hover(screen.getByRole("link", { name: "Knoten Köln" }));

        expect(await screen.findByText("K-003-V01")).toBeInTheDocument();
        expect(screen.getByText("Ausbau")).toBeInTheDocument();
        expect(api).toHaveBeenCalledTimes(1);
    });

    it("stays a plain link on touch devices", async () => {
        setCanHover(false);
        renderLink();

        await userEvent.hover(screen.getByRole("link", { name: "Knoten Köln" }));

        await new Promise((r) => setTimeout(r, 500));
        expect(screen.queryByText("K-003-V01")).not.toBeInTheDocument();
        expect(api).not.toHaveBeenCalled();
    });
});
