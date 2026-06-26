import { useMemo, useState } from "react";
import {
    Alert,
    Button,
    Checkbox,
    Container,
    Group,
    Loader,
    SegmentedControl,
    Select,
    SimpleGrid,
    Stack,
    Text,
    TextInput,
} from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import {
    useCreateTodo,
    useProjects,
    useTodos,
    useUserOptions,
    type Todo,
    type TodoStatus,
} from "../../shared/api/queries";
import { ChronicleCard, ChronicleHeadline } from "../../components/chronicle";
import TodoCard from "./TodoCard";
import TodoEditDrawer from "./TodoEditDrawer";
import { useTodoActions } from "./useTodoActions";
import { STATUS_LABELS, STATUS_ORDER } from "./todoConstants";

export default function TasksPage() {
    const { user, can } = useAuth();
    const canCreate = can("todo.create");
    const canEdit = can("todo.edit");
    const canDelete = can("todo.delete");

    const [assigneeFilter, setAssigneeFilter] = useState<string | null>(null);
    const [projectFilter, setProjectFilter] = useState<string | null>(null);
    const [onlyMine, setOnlyMine] = useState(false);
    const [includeDone, setIncludeDone] = useState(true);

    const filters = useMemo(
        () => ({
            assignee_id: onlyMine && user ? user.id : assigneeFilter ? Number(assigneeFilter) : undefined,
            project_id: projectFilter ? Number(projectFilter) : undefined,
            include_done: includeDone,
        }),
        [onlyMine, user, assigneeFilter, projectFilter, includeDone],
    );

    const { data: todos, isLoading, isError } = useTodos(filters, user !== null);
    const { data: projects } = useProjects();
    const { data: users } = useUserOptions(user !== null);
    const createTodo = useCreateTodo();
    const { changeStatus, confirmDelete } = useTodoActions();

    const [drawerOpen, setDrawerOpen] = useState(false);
    const [editing, setEditing] = useState<Todo | null>(null);
    const [quickTitle, setQuickTitle] = useState("");

    const grouped = useMemo(() => {
        const by: Record<TodoStatus, Todo[]> = { OPEN: [], IN_PROGRESS: [], DONE: [] };
        (todos ?? []).forEach((t) => by[t.status as TodoStatus]?.push(t));
        return by;
    }, [todos]);

    const openCreate = () => {
        setEditing(null);
        setDrawerOpen(true);
    };
    const openEdit = (todo: Todo) => {
        setEditing(todo);
        setDrawerOpen(true);
    };

    const handleQuickAdd = async () => {
        const title = quickTitle.trim();
        if (!title) return;
        try {
            await createTodo.mutateAsync({ title, status: "OPEN", priority: "MEDIUM" });
            setQuickTitle("");
            notifications.show({ color: "teal", message: "Aufgabe erstellt." });
        } catch {
            notifications.show({ color: "red", message: "Erstellen fehlgeschlagen." });
        }
    };

    if (user === null) {
        return (
            <Container size="md" py="xl">
                <Alert color="gray">Aufgaben sind nur für angemeldete Nutzer sichtbar.</Alert>
            </Container>
        );
    }

    const visibleStatuses = includeDone ? STATUS_ORDER : STATUS_ORDER.filter((s) => s !== "DONE");

    return (
        <Container size="xl" py="lg">
            <Stack gap="lg">
                <Group justify="space-between" align="center">
                    <ChronicleHeadline as="h1">Aufgaben</ChronicleHeadline>
                    {canCreate && (
                        <Button leftSection={<IconPlus size={16} />} onClick={openCreate}>
                            Neue Aufgabe
                        </Button>
                    )}
                </Group>

                {canCreate && (
                    <Group gap="xs">
                        <TextInput
                            flex={1}
                            placeholder="Schnell notieren … (Enter)"
                            value={quickTitle}
                            onChange={(e) => setQuickTitle(e.currentTarget.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") handleQuickAdd();
                            }}
                        />
                        <Button variant="light" onClick={handleQuickAdd} loading={createTodo.isPending}>
                            Hinzufügen
                        </Button>
                    </Group>
                )}

                <Group gap="md" align="flex-end" wrap="wrap">
                    <Select
                        label="Zugewiesen an"
                        placeholder="Alle"
                        data={(users ?? []).map((u) => ({ value: String(u.id), label: u.username }))}
                        value={assigneeFilter}
                        onChange={setAssigneeFilter}
                        disabled={onlyMine}
                        clearable
                        searchable
                        w={200}
                    />
                    <Select
                        label="Projekt"
                        placeholder="Alle"
                        data={(projects ?? []).map((p) => ({
                            value: String(p.id),
                            label: p.project_number ? `${p.project_number} – ${p.name}` : p.name,
                        }))}
                        value={projectFilter}
                        onChange={setProjectFilter}
                        clearable
                        searchable
                        w={260}
                    />
                    <Checkbox
                        label="Nur meine Aufgaben"
                        checked={onlyMine}
                        onChange={(e) => setOnlyMine(e.currentTarget.checked)}
                    />
                    <SegmentedControl
                        value={includeDone ? "all" : "open"}
                        onChange={(v) => setIncludeDone(v === "all")}
                        data={[
                            { value: "open", label: "Offene" },
                            { value: "all", label: "Alle" },
                        ]}
                    />
                </Group>

                {isLoading && (
                    <Group justify="center" py="xl">
                        <Loader />
                    </Group>
                )}
                {isError && <Alert color="red">Aufgaben konnten nicht geladen werden.</Alert>}

                {!isLoading && !isError && (
                    <SimpleGrid cols={{ base: 1, sm: visibleStatuses.length }} spacing="md">
                        {visibleStatuses.map((status) => (
                            <Stack key={status} gap="sm">
                                <Group gap="xs">
                                    <ChronicleHeadline as="h3">{STATUS_LABELS[status]}</ChronicleHeadline>
                                    <Text c="dimmed" size="sm">
                                        ({grouped[status].length})
                                    </Text>
                                </Group>
                                {grouped[status].length === 0 ? (
                                    <Text c="dimmed" size="sm">
                                        Keine Aufgaben.
                                    </Text>
                                ) : (
                                    grouped[status].map((todo) => (
                                        <TodoCard
                                            key={todo.id}
                                            todo={todo}
                                            canEdit={canEdit}
                                            canDelete={canDelete}
                                            onEdit={openEdit}
                                            onChangeStatus={changeStatus}
                                            onDelete={confirmDelete}
                                        />
                                    ))
                                )}
                            </Stack>
                        ))}
                    </SimpleGrid>
                )}

                {(todos?.length ?? 0) === 0 && !isLoading && !isError && (
                    <ChronicleCard>
                        <Text c="dimmed">Noch keine Aufgaben. Lege oben deine erste an.</Text>
                    </ChronicleCard>
                )}
            </Stack>

            <TodoEditDrawer opened={drawerOpen} onClose={() => setDrawerOpen(false)} todo={editing} />
        </Container>
    );
}
