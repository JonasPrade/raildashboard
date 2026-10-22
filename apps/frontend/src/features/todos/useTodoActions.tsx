import { Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useDeleteTodo, useUpdateTodo, type Todo, type TodoStatus } from "../../shared/api/queries";
import { openConfirmModal } from "../../shared/ui/confirmModal";

/** Shared status-change and delete handlers for the to-do cards. */
export function useTodoActions() {
    const updateTodo = useUpdateTodo();
    const deleteTodo = useDeleteTodo();

    const changeStatus = async (todo: Todo, status: TodoStatus) => {
        try {
            await updateTodo.mutateAsync({ id: todo.id, payload: { status } });
        } catch {
            notifications.show({ color: "red", message: "Status konnte nicht geändert werden." });
        }
    };

    const confirmDelete = (todo: Todo) => {
        openConfirmModal({
            title: "Aufgabe löschen?",
            children: (
                <Text size="sm" mb="md">
                    „{todo.title}" wird dauerhaft entfernt.
                </Text>
            ),
            labels: { confirm: "Löschen", cancel: "Abbrechen" },
            danger: true,
            onConfirm: async () => {
                try {
                    await deleteTodo.mutateAsync(todo.id);
                    notifications.show({ color: "teal", message: "Aufgabe gelöscht." });
                } catch {
                    notifications.show({ color: "red", message: "Löschen fehlgeschlagen." });
                }
            },
        });
    };

    return { changeStatus, confirmDelete };
}
