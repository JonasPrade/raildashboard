import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import FinveProjectsDrawer from "./FinveProjectsDrawer";
import type { FinveListItem } from "../../shared/api/queries";

const mutate = vi.fn();

vi.mock("../../shared/hooks/useBreakpoint", () => ({ useIsMobile: () => false }));
vi.mock("../../shared/api/queries", () => ({
    useUpdateFinveProjects: () => ({ mutate, isPending: false }),
}));
// Confirm at once — the dialog itself is covered by the shared confirmModal.
vi.mock("../../shared/ui/confirmModal", () => ({
    openConfirmModal: ({ onConfirm }: { onConfirm: () => void }) => onConfirm(),
}));
vi.mock("../projects/ProjectSearchSelect", () => ({
    default: ({ label, onChange }: { label: string; onChange: (id: number | null) => void }) => (
        <button type="button" onClick={() => onChange(2221)}>
            {label}
        </button>
    ),
}));

const finve = {
    id: 900008,
    name: "Digitaler Knoten Stuttgart",
    is_sammel_finve: false,
    temporary_finve_number: true,
    project_count: 2,
    project_names: ["Stuttgart 21", "Gäubahn Abschnitt Nord"],
    projects: [
        { id: 2183, name: "Stuttgart 21" },
        { id: 2221, name: "Gäubahn Abschnitt Nord" },
    ],
    // 2183 only through a Sammel-FinVe year link in this fixture.
    permanent_project_ids: [2221],
    budgets: [],
} as unknown as FinveListItem;

function renderDrawer(item: FinveListItem = finve) {
    return render(
        <MantineProvider>
            <MemoryRouter>
                <FinveProjectsDrawer finve={item} onClose={() => {}} />
            </MemoryRouter>
        </MantineProvider>,
    );
}

describe("FinveProjectsDrawer", () => {
    beforeEach(() => mutate.mockReset());

    it("offers removal only for permanent links", () => {
        renderDrawer();
        expect(screen.getAllByRole("button", { name: "Entfernen" })).toHaveLength(1);
        expect(screen.getByText("Haushaltsjahr")).toBeInTheDocument();
    });

    it("marks the year links of an archived project", () => {
        renderDrawer({
            ...finve,
            projects: [...finve.projects, { id: 1471, name: "Optimiertes Alpha-E mit Bremen", is_archived: true }],
        } as FinveListItem);
        expect(screen.getByText("Archiviert")).toBeInTheDocument();
        expect(screen.getAllByRole("button", { name: "Entfernen" })).toHaveLength(1);
    });

    it("removes a project from the FinVe", async () => {
        const user = userEvent.setup();
        renderDrawer();
        await user.click(screen.getByRole("button", { name: "Entfernen" }));
        expect(mutate).toHaveBeenCalledWith(
            { finveId: 900008, removeProjectIds: [2221] },
            expect.anything(),
        );
    });

    it("adds the picked project", async () => {
        const user = userEvent.setup();
        renderDrawer();
        const add = screen.getByRole("button", { name: "Hinzufügen" });
        expect(add).toBeDisabled();
        await user.click(screen.getByRole("button", { name: "Projekt hinzufügen" }));
        await user.click(add);
        expect(mutate).toHaveBeenCalledWith({ finveId: 900008, addProjectIds: [2221] }, expect.anything());
    });
});
