import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { Project } from "../../shared/api/queries";
import { ArchiveBanner } from "./ProjectArchive";

function renderBanner(project: Partial<Project>, replacement: unknown) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
    client.setQueryData(["projectReplacement", project.id], replacement);
    return render(
        <QueryClientProvider client={client}>
            <MantineProvider>
                <MemoryRouter>
                    <ArchiveBanner project={project as Project} />
                </MemoryRouter>
            </MantineProvider>
        </QueryClientProvider>,
    );
}

describe("ArchiveBanner", () => {
    it("links an archived project to its successor", () => {
        renderBanner(
            { id: 1477, name: "ABS/NBS Hannover - Bielefeld (BVWP)", is_archived: true, archived_reason: "D-14" },
            { replaced_by: { id: 1535, name: "NBS/ABS Bielefeld – Seelze", project_number: "D-14" }, replaces: [] },
        );
        expect(screen.getByRole("link", { name: "NBS/ABS Bielefeld – Seelze (D-14)" })).toHaveAttribute(
            "href",
            "/projects/1535",
        );
    });

    it("shows the back-reference on the successor", () => {
        renderBanner(
            { id: 1535, name: "NBS/ABS Bielefeld – Seelze", is_archived: false },
            { replaced_by: null, replaces: [{ id: 1477, name: "ABS/NBS Hannover - Bielefeld (BVWP)" }] },
        );
        expect(screen.getByText("Nachfolgeprojekt")).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "ABS/NBS Hannover - Bielefeld (BVWP)" })).toHaveAttribute(
            "href",
            "/projects/1477",
        );
    });

    it("shows nothing for an active project that replaces nothing", () => {
        renderBanner({ id: 7, name: "X", is_archived: false }, { replaced_by: null, replaces: [] });
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
});
