import { useState } from "react";
import { Button, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { Plus } from "lucide-react";
import { useAuth } from "../../lib/auth";
import { useTodos, type Todo } from "../../shared/api/queries";
import TodoCard from "./TodoCard";
import TodoEditDrawer from "./TodoEditDrawer";
import { useTodoActions } from "./useTodoActions";
import { LoadingState } from "../../shared/ui/LoadingState";
import { ErrorState } from "../../shared/ui/ErrorState";

/** Compact task list for a single project (project detail page). */
export default function TasksSection({ projectId }: { projectId: number }) {
    const { can } = useAuth();
    const canCreate = can("todo.create");
    const canEdit = can("todo.edit");
    const canDelete = can("todo.delete");

    const { data: todos, isLoading, isError, refetch } = useTodos({ project_id: projectId });
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
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="sm">
                <Group justify="space-between" align="center">
                    <Title order={2}>Aufgaben</Title>
                    {canCreate && (
                        <Button size="xs" variant="light" leftSection={<Plus size={16} />} onClick={openCreate}>
                            Aufgabe
                        </Button>
                    )}
                </Group>

                {isLoading && (
                    <LoadingState rows={3} />
                )}
                {isError && <ErrorState onRetry={() => void refetch()}>Aufgaben konnten nicht geladen werden.</ErrorState>}

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
        </Paper>
    );
}
