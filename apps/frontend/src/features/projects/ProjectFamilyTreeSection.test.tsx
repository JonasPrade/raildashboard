import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProjectFamilyTreeSection from "./ProjectFamilyTreeSection";

const api = vi.hoisted(() => vi.fn());
vi.mock("../../shared/api/client", () => ({ api }));

function renderSection(projectId: number) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
        <QueryClientProvider client={client}>
            <MantineProvider>
                <MemoryRouter>
                    <ProjectFamilyTreeSection projectId={projectId} />
                </MemoryRouter>
            </MantineProvider>
        </QueryClientProvider>,
    );
}

beforeEach(() => {
    api.mockReset();
    api.mockResolvedValue([
        { id: 1, name: "ABS Hamburg–Puttgarden", project_number: "2-001" },
        { id: 2, name: "Lübeck–Puttgarden", superior_project_id: 1 },
        { id: 3, name: "Hamburg–Lübeck", superior_project_id: 1 },
        { id: 4, name: "Fehmarnsundquerung", superior_project_id: 2 },
    ]);
});

describe("ProjectFamilyTreeSection", () => {
    it("counts and shows the projects above, beside and below", async () => {
        renderSection(2);
        expect(await screen.findByText("1 darüber · 1 daneben · 1 darunter")).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: "Anzeigen" }));
        expect(await screen.findByRole("link", { name: "ABS Hamburg–Puttgarden" })).toHaveAttribute("href", "/projects/1");
        expect(screen.getByRole("link", { name: "Hamburg–Lübeck" })).toHaveAttribute("href", "/projects/3");
        expect(screen.getByRole("link", { name: "Fehmarnsundquerung" })).toHaveAttribute("href", "/projects/4");
        // The current project is marked, not linked.
        expect(screen.queryByRole("link", { name: "Lübeck–Puttgarden" })).not.toBeInTheDocument();
        expect(screen.getByText("dieses Projekt")).toBeInTheDocument();
    });

    it("renders nothing for a project outside the hierarchy (draft)", async () => {
        const { container } = renderSection(99);
        await vi.waitFor(() => expect(api).toHaveBeenCalled());
        await vi.waitFor(() => expect(container.querySelector(".mantine-Paper-root")).toBeNull());
    });
});
