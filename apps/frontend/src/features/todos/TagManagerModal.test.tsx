import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MantineProvider } from "@mantine/core";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TagManagerModal from "./TagManagerModal";

const updateTag = vi.fn();

vi.mock("../../shared/hooks/useBreakpoint", () => ({ useIsMobile: () => false }));
vi.mock("../../shared/api/queries", () => ({
    useTodoTags: () => ({
        data: [{ id: 1, name: "@LLM", description: "Vom LLM zu erledigen", todo_count: 2 }],
    }),
    useUpdateTodoTag: () => ({ mutateAsync: updateTag, isPending: false }),
    useDeleteTodoTag: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

function renderModal(canDelete = true) {
    return render(
        <MantineProvider>
            <TagManagerModal opened onClose={() => {}} canDelete={canDelete} />
        </MantineProvider>,
    );
}

describe("TagManagerModal", () => {
    beforeEach(() => updateTag.mockReset());

    it("saves a rename and clears an emptied description", async () => {
        const user = userEvent.setup();
        renderModal();

        const save = screen.getByRole("button", { name: "Speichern" });
        expect(save).toBeDisabled();

        await user.clear(screen.getByLabelText("Name"));
        await user.type(screen.getByLabelText("Name"), "LLM");
        await user.clear(screen.getByLabelText("Beschreibung"));
        await user.click(save);

        expect(updateTag).toHaveBeenCalledWith({ id: 1, payload: { name: "LLM", clear_description: true } });
    });

    it("shows a conflict when the name is taken", async () => {
        updateTag.mockRejectedValueOnce({ status: 409 });
        const user = userEvent.setup();
        renderModal();

        await user.type(screen.getByLabelText("Name"), "x");
        await user.click(screen.getByRole("button", { name: "Speichern" }));

        expect(await screen.findByText("Es gibt schon ein Tag „@LLMx“.")).toBeInTheDocument();
    });

    it("hides delete without the permission", () => {
        renderModal(false);
        expect(screen.queryByLabelText("Tag löschen")).not.toBeInTheDocument();
    });
});
