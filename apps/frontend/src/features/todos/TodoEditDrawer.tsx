import { useEffect, useMemo, useState } from "react";
import {
    Button,
    Drawer,
    Group,
    MultiSelect,
    Select,
    Stack,
    Textarea,
    TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
    useCreateTodo,
    useProjects,
    useUpdateTodo,
    useUserOptions,
    type Todo,
    type TodoPriority,
    type TodoStatus,
} from "../../shared/api/queries";
import { PRIORITY_LABELS, PRIORITY_ORDER, STATUS_LABELS, STATUS_ORDER } from "./todoConstants";

type Props = {
    opened: boolean;
    onClose: () => void;
    /** Task being edited; null = create mode. */
    todo: Todo | null;
    /** Pre-selected project for new tasks (e.g. opened from a project page). */
    defaultProjectId?: number | null;
    /** Hide the project selector (when scoped to a fixed project). */
    lockProject?: boolean;
};

export default function TodoEditDrawer({ opened, onClose, todo, defaultProjectId = null, lockProject = false }: Props) {
    const isEdit = todo !== null;
    const createTodo = useCreateTodo();
    const updateTodo = useUpdateTodo();
    const { data: projects } = useProjects();
    const { data: users } = useUserOptions(opened);

    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [status, setStatus] = useState<TodoStatus>("OPEN");
    const [priority, setPriority] = useState<TodoPriority>("MEDIUM");
    const [dueDate, setDueDate] = useState<string>("");
    const [projectId, setProjectId] = useState<string | null>(null);
    const [assigneeIds, setAssigneeIds] = useState<string[]>([]);

    // Reset the form whenever the drawer (re)opens for a different task.
    useEffect(() => {
        if (!opened) return;
        setTitle(todo?.title ?? "");
        setDescription(todo?.description ?? "");
        setStatus((todo?.status as TodoStatus) ?? "OPEN");
        setPriority((todo?.priority as TodoPriority) ?? "MEDIUM");
        setDueDate(todo?.due_date ?? "");
        setProjectId(
            todo?.project_id != null
                ? String(todo.project_id)
                : defaultProjectId != null
                  ? String(defaultProjectId)
                  : null,
        );
        setAssigneeIds((todo?.assignees ?? []).map((a) => String(a.id)));
    }, [opened, todo, defaultProjectId]);

    const projectOptions = useMemo(
        () =>
            (projects ?? []).map((p) => ({
                value: String(p.id),
                label: p.project_number ? `${p.project_number} – ${p.name}` : p.name,
            })),
        [projects],
    );

    const userOptions = useMemo(
        () => (users ?? []).map((u) => ({ value: String(u.id), label: u.username })),
        [users],
    );

    const saving = createTodo.isPending || updateTodo.isPending;

    const handleSave = async () => {
        const trimmed = title.trim();
        if (!trimmed) {
            notifications.show({ color: "red", message: "Bitte einen Titel angeben." });
            return;
        }
        const assignee_ids = assigneeIds.map(Number);
        try {
            if (isEdit && todo) {
                await updateTodo.mutateAsync({
                    id: todo.id,
                    payload: {
                        title: trimmed,
                        description: description.trim() || null,
                        status,
                        priority,
                        due_date: dueDate || null,
                        clear_due_date: !dueDate,
                        project_id: projectId ? Number(projectId) : null,
                        clear_project: !projectId,
                        assignee_ids,
                    },
                });
            } else {
                await createTodo.mutateAsync({
                    title: trimmed,
                    description: description.trim() || null,
                    status,
                    priority,
                    due_date: dueDate || null,
                    project_id: projectId ? Number(projectId) : null,
                    assignee_ids,
                });
            }
            notifications.show({ color: "teal", message: isEdit ? "Aufgabe gespeichert." : "Aufgabe erstellt." });
            onClose();
        } catch {
            notifications.show({ color: "red", message: "Speichern fehlgeschlagen." });
        }
    };

    return (
        <Drawer
            opened={opened}
            onClose={onClose}
            position="right"
            size="lg"
            title={isEdit ? "Aufgabe bearbeiten" : "Neue Aufgabe"}
        >
            <Stack gap="md">
                <TextInput
                    label="Titel"
                    placeholder="Was ist zu tun?"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.currentTarget.value)}
                    data-autofocus
                />
                <Textarea
                    label="Beschreibung"
                    placeholder="Optionale Notizen …"
                    autosize
                    minRows={3}
                    value={description}
                    onChange={(e) => setDescription(e.currentTarget.value)}
                />
                <Group grow>
                    <Select
                        label="Status"
                        data={STATUS_ORDER.map((s) => ({ value: s, label: STATUS_LABELS[s] }))}
                        value={status}
                        onChange={(v) => v && setStatus(v as TodoStatus)}
                        allowDeselect={false}
                    />
                    <Select
                        label="Priorität"
                        data={PRIORITY_ORDER.map((p) => ({ value: p, label: PRIORITY_LABELS[p] }))}
                        value={priority}
                        onChange={(v) => v && setPriority(v as TodoPriority)}
                        allowDeselect={false}
                    />
                </Group>
                <TextInput
                    type="date"
                    label="Fällig am"
                    value={dueDate}
                    onChange={(e) => setDueDate(e.currentTarget.value)}
                />
                {!lockProject && (
                    <Select
                        label="Projekt"
                        placeholder="Kein Projekt (freie Notiz)"
                        data={projectOptions}
                        value={projectId}
                        onChange={setProjectId}
                        searchable
                        clearable
                        nothingFoundMessage="Kein Projekt gefunden"
                    />
                )}
                <MultiSelect
                    label="Zugewiesen an"
                    placeholder="Nutzer auswählen"
                    data={userOptions}
                    value={assigneeIds}
                    onChange={setAssigneeIds}
                    searchable
                    clearable
                />
                <Group justify="flex-end" mt="sm">
                    <Button variant="subtle" color="gray" onClick={onClose}>
                        Abbrechen
                    </Button>
                    <Button onClick={handleSave} loading={saving}>
                        {isEdit ? "Speichern" : "Erstellen"}
                    </Button>
                </Group>
            </Stack>
        </Drawer>
    );
}
