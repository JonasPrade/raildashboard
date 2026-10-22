import { Badge, Card, Group, Select, Stack, Text, Tooltip, ActionIcon, Avatar } from "@mantine/core";
import { Pencil, Trash2, Calendar, Check } from "lucide-react";
import { Link } from "react-router-dom";
import type { Todo, TodoStatus } from "../../shared/api/queries";
import {
    PRIORITY_LABELS,
    PRIORITY_WEIGHT,
    STATUS_LABELS,
    STATUS_ORDER,
    displayStatus,
    formatDate,
    hasCheck,
    initials,
    todoStatusTextStyle,
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
    const status = displayStatus(todo.status, todo.due_date);
    const overdue = status === "OVERDUE";
    const done = todo.status === "DONE";

    return (
        <Card withBorder padding="sm" radius="md">
            <Stack gap={8}>
                <Group justify="space-between" align="flex-start" wrap="nowrap">
                    <Group gap={6} wrap="nowrap" align="flex-start" style={{ minWidth: 0 }}>
                        {done && <Check size={16} aria-label="Erledigt" style={{ flexShrink: 0, marginTop: 4, color: "var(--text-muted)" }} />}
                        <Text fw={600} lineClamp={2} style={done ? { color: "var(--text-muted)" } : undefined}>
                            {todo.title}
                        </Text>
                    </Group>
                    {/* Priority through weight, never colour (Anwendungsebene). */}
                    <Text size="xs" fw={PRIORITY_WEIGHT[todo.priority]} style={{ flexShrink: 0, color: "var(--text-strong)" }}>
                        {PRIORITY_LABELS[todo.priority]}
                    </Text>
                </Group>

                {todo.description && (
                    <Text size="sm" c="dimmed" lineClamp={3}>
                        {todo.description}
                    </Text>
                )}

                {(todo.tags ?? []).length > 0 && (
                    <Group gap={4} wrap="wrap">
                        {(todo.tags ?? []).map((tag) => (
                            <Badge
                                key={tag.id}
                                size="sm"
                                variant="outline"
                                radius={0}
                                color="var(--text-strong)"
                                title={tag.description ?? undefined}
                            >
                                {tag.name}
                            </Badge>
                        ))}
                    </Group>
                )}

                <Group gap="xs" wrap="wrap">
                    {todo.due_date && (
                        <Group gap={4} wrap="nowrap">
                            <Calendar size={16} />
                            <Text size="xs" c={overdue ? undefined : "dimmed"} style={overdue ? todoStatusTextStyle("OVERDUE") : undefined}>
                                {formatDate(todo.due_date)}
                                {overdue ? " · überfällig" : ""}
                            </Text>
                        </Group>
                    )}
                    {showProject && todo.project && (
                        <Text size="xs" c="dimmed">
                            <Text component={Link} to={`/projects/${todo.project.id}`} size="xs" c="var(--accent-primary)" inherit>
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
                            <Group gap={4} wrap="nowrap">
                                {hasCheck(todo.status) && <Check size={14} aria-hidden style={{ color: "var(--text-muted)" }} />}
                                <Text size="sm" style={todoStatusTextStyle(todo.status)}>
                                    {STATUS_LABELS[todo.status]}
                                </Text>
                            </Group>
                        )}
                        <Avatar.Group spacing="xs">
                            {todo.assignees.map((a) => (
                                <Tooltip key={a.id} label={a.username} withArrow>
                                    <Avatar size={24} radius="xl" color="teal">
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
                                        <Pencil size={16} />
                                    </ActionIcon>
                                </Tooltip>
                            )}
                            {canDelete && (
                                <Tooltip label="Löschen" withArrow>
                                    <ActionIcon variant="subtle" color="red" onClick={() => onDelete(todo)} aria-label="Löschen">
                                        <Trash2 size={16} />
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
