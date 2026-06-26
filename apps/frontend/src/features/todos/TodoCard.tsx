import { Badge, Card, Group, Select, Stack, Text, Tooltip, ActionIcon, Avatar } from "@mantine/core";
import { IconPencil, IconTrash, IconCalendarEvent } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import type { Todo, TodoStatus } from "../../shared/api/queries";
import {
    PRIORITY_COLORS,
    PRIORITY_LABELS,
    STATUS_COLORS,
    STATUS_LABELS,
    STATUS_ORDER,
    formatDate,
    initials,
    isOverdue,
} from "./todoConstants";

type Props = {
    todo: Todo;
    canEdit: boolean;
    canDelete: boolean;
    /** Show the linked-project line (hidden when rendered inside a project). */
    showProject?: boolean;
    onEdit: (todo: Todo) => void;
    onChangeStatus: (todo: Todo, status: TodoStatus) => void;
    onDelete: (todo: Todo) => void;
};

export default function TodoCard({
    todo,
    canEdit,
    canDelete,
    showProject = true,
    onEdit,
    onChangeStatus,
    onDelete,
}: Props) {
    const overdue = todo.status !== "DONE" && isOverdue(todo.due_date);
    const done = todo.status === "DONE";

    return (
        <Card withBorder padding="sm" radius="md" style={done ? { opacity: 0.7 } : undefined}>
            <Stack gap={8}>
                <Group justify="space-between" align="flex-start" wrap="nowrap">
                    <Text
                        fw={600}
                        style={done ? { textDecoration: "line-through" } : undefined}
                        lineClamp={2}
                    >
                        {todo.title}
                    </Text>
                    <Group gap={4} wrap="nowrap">
                        <Badge color={PRIORITY_COLORS[todo.priority]} variant="light" size="sm">
                            {PRIORITY_LABELS[todo.priority]}
                        </Badge>
                    </Group>
                </Group>

                {todo.description && (
                    <Text size="sm" c="dimmed" lineClamp={3}>
                        {todo.description}
                    </Text>
                )}

                <Group gap="xs" wrap="wrap">
                    {todo.due_date && (
                        <Group gap={4} wrap="nowrap">
                            <IconCalendarEvent size={14} color={overdue ? "var(--mantine-color-red-6)" : undefined} />
                            <Text size="xs" c={overdue ? "red" : "dimmed"} fw={overdue ? 700 : 400}>
                                {formatDate(todo.due_date)}
                                {overdue ? " · überfällig" : ""}
                            </Text>
                        </Group>
                    )}
                    {showProject && todo.project && (
                        <Text size="xs" c="dimmed">
                            ▸{" "}
                            <Text component={Link} to={`/projects/${todo.project.id}`} size="xs" c="blue" inherit>
                                {todo.project.project_number
                                    ? `${todo.project.project_number} – ${todo.project.name}`
                                    : todo.project.name}
                            </Text>
                        </Text>
                    )}
                </Group>

                <Group justify="space-between" align="center" wrap="nowrap">
                    <Group gap={6} wrap="nowrap">
                        {canEdit ? (
                            <Select
                                size="xs"
                                w={130}
                                data={STATUS_ORDER.map((s) => ({ value: s, label: STATUS_LABELS[s] }))}
                                value={todo.status}
                                onChange={(v) => v && v !== todo.status && onChangeStatus(todo, v as TodoStatus)}
                                allowDeselect={false}
                                aria-label="Status ändern"
                            />
                        ) : (
                            <Badge color={STATUS_COLORS[todo.status]} variant="light" size="sm">
                                {STATUS_LABELS[todo.status]}
                            </Badge>
                        )}
                        <Avatar.Group spacing="xs">
                            {todo.assignees.map((a) => (
                                <Tooltip key={a.id} label={a.username} withArrow>
                                    <Avatar size={24} radius="xl" color="blue">
                                        {initials(a.username)}
                                    </Avatar>
                                </Tooltip>
                            ))}
                        </Avatar.Group>
                    </Group>

                    {(canEdit || canDelete) && (
                        <Group gap={2} wrap="nowrap">
                            {canEdit && (
                                <Tooltip label="Bearbeiten" withArrow>
                                    <ActionIcon variant="subtle" color="gray" onClick={() => onEdit(todo)} aria-label="Bearbeiten">
                                        <IconPencil size={16} />
                                    </ActionIcon>
                                </Tooltip>
                            )}
                            {canDelete && (
                                <Tooltip label="Löschen" withArrow>
                                    <ActionIcon variant="subtle" color="red" onClick={() => onDelete(todo)} aria-label="Löschen">
                                        <IconTrash size={16} />
                                    </ActionIcon>
                                </Tooltip>
                            )}
                        </Group>
                    )}
                </Group>
            </Stack>
        </Card>
    );
}
