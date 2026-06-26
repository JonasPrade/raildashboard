import { useState } from "react";
import { Alert, Button, Group, Loader, Stack, Text } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { useAuth } from "../../lib/auth";
import { useTodos, type Todo } from "../../shared/api/queries";
import { ChronicleCard, ChronicleHeadline } from "../../components/chronicle";
import TodoCard from "./TodoCard";
import TodoEditDrawer from "./TodoEditDrawer";
import { useTodoActions } from "./useTodoActions";

/** Compact task list for a single project (project detail page). */
export default function TasksSection({ projectId }: { projectId: number }) {
    const { can } = useAuth();
    const canCreate = can("todo.create");
    const canEdit = can("todo.edit");
    const canDelete = can("todo.delete");

    const { data: todos, isLoading, isError } = useTodos({ project_id: projectId });
    const { changeStatus, confirmDelete } = useTodoActions();

    const [drawerOpen, setDrawerOpen] = useState(false);
    const [editing, setEditing] = useState<Todo | null>(null);

    const openCreate = () => {
        setEditing(null);
        setDrawerOpen(true);
    };
    const openEdit = (todo: Todo) => {
        setEditing(todo);
        setDrawerOpen(true);
    };

    return (
        <ChronicleCard>
            <Stack gap="sm">
                <Group justify="space-between" align="center">
                    <ChronicleHeadline as="h2">Aufgaben</ChronicleHeadline>
                    {canCreate && (
                        <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} onClick={openCreate}>
                            Aufgabe
                        </Button>
                    )}
                </Group>

                {isLoading && (
                    <Group justify="center" py="md">
                        <Loader size="sm" />
                    </Group>
                )}
                {isError && <Alert color="red">Aufgaben konnten nicht geladen werden.</Alert>}

                {!isLoading && !isError && (todos?.length ?? 0) === 0 && (
                    <Text c="dimmed" size="sm">
                        Keine Aufgaben für dieses Projekt.
                    </Text>
                )}

                {!isLoading &&
                    !isError &&
                    (todos ?? []).map((todo) => (
                        <TodoCard
                            key={todo.id}
                            todo={todo}
                            canEdit={canEdit}
                            canDelete={canDelete}
                            showProject={false}
                            onEdit={openEdit}
                            onChangeStatus={changeStatus}
                            onDelete={confirmDelete}
                        />
                    ))}
            </Stack>

            <TodoEditDrawer
                opened={drawerOpen}
                onClose={() => setDrawerOpen(false)}
                todo={editing}
                defaultProjectId={projectId}
                lockProject
            />
        </ChronicleCard>
    );
}
