import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MantineProvider } from "@mantine/core";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TodoComments from "./TodoComments";

const createComment = vi.fn();
const updateComment = vi.fn();
let permissions: string[] = ["todo.edit"];

vi.mock("../../lib/auth", () => ({
    useAuth: () => ({ user: { id: 1, username: "jonas" }, can: (p: string) => permissions.includes(p) }),
}));
vi.mock("../../shared/ui/confirmModal", () => ({ openConfirmModal: vi.fn() }));
vi.mock("../../shared/api/queries", () => ({
    useTodoComments: () => ({
        data: [
            {
                id: 10,
                todo_id: 5,
                body: "Entwurf liegt vor.",
                user_id: 1,
                username_snapshot: "jonas",
                created_at: "2026-11-01T10:00:00",
                edited_at: null,
            },
            {
                id: 11,
                todo_id: 5,
                body: "Rückfrage gestellt.",
                user_id: 2,
                username_snapshot: "anna",
                created_at: "2026-11-02T09:00:00",
                edited_at: "2026-11-02T09:30:00",
            },
        ],
    }),
    useCreateTodoComment: () => ({ mutateAsync: createComment, isPending: false }),
    useUpdateTodoComment: () => ({ mutateAsync: updateComment, isPending: false }),
    useDeleteTodoComment: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

function renderComments() {
    return render(
        <MantineProvider>
            <TodoComments todoId={5} />
        </MantineProvider>,
    );
}

describe("TodoComments", () => {
    beforeEach(() => {
        createComment.mockReset();
        updateComment.mockReset();
        permissions = ["todo.edit"];
    });

    it("lists comments and adds a trimmed one", async () => {
        const user = userEvent.setup();
        renderComments();

        expect(screen.getByText("Entwurf liegt vor.")).toBeInTheDocument();
        expect(screen.getByText(/anna · bearbeitet/)).toBeInTheDocument();

        const add = screen.getByRole("button", { name: "Kommentieren" });
        expect(add).toBeDisabled();
        await user.type(screen.getByLabelText("Neuer Kommentar"), "  Stand: fertig  ");
        await user.click(add);

        expect(createComment).toHaveBeenCalledWith({ todoId: 5, body: "Stand: fertig" });
    });

    it("lets only the author edit, and todo.delete delete others", () => {
        renderComments();
        expect(screen.getAllByLabelText("Kommentar bearbeiten")).toHaveLength(1);
        expect(screen.getAllByLabelText("Kommentar löschen")).toHaveLength(1);
    });

    it("shows delete on foreign comments with todo.delete", () => {
        permissions = ["todo.edit", "todo.delete"];
        renderComments();
        expect(screen.getAllByLabelText("Kommentar löschen")).toHaveLength(2);
    });

    it("is read-only without todo.edit", () => {
        permissions = [];
        renderComments();
        expect(screen.queryByLabelText("Neuer Kommentar")).not.toBeInTheDocument();
        expect(screen.queryByLabelText("Kommentar bearbeiten")).not.toBeInTheDocument();
    });
});
