import { Divider, Stack, Text, Title } from "@mantine/core";
import { useTodoHistory } from "../../shared/api/queries";
import { formatDateTimeShort } from "../../shared/format";

const FIELD_LABELS: Record<string, string> = {
    title: "Titel",
    description: "Beschreibung",
    status: "Status",
    priority: "Priorität",
    due_date: "Fällig am",
    project_id: "Projekt",
    assignees: "Zugewiesen an",
    tags: "Tags",
};

const ACTION_LABELS: Record<string, string> = {
    CREATE: "angelegt",
    PATCH: "geändert",
    DELETE: "gelöscht",
    MIGRATION: "Datenübernahme",
};

/** Change history of one task (newest first), shown under the edit form. */
export default function TodoHistory({ todoId }: { todoId: number }) {
    const { data: history } = useTodoHistory(todoId);
    if (!history || history.length === 0) return null;

    return (
        <Stack gap="xs" mt="md">
            <Divider />
            <Title order={4}>Verlauf</Title>
            {history.map((log) => (
                <Stack key={log.id} gap={2}>
                    <Text size="xs" c="dimmed">
                        {formatDateTimeShort(log.timestamp)} · {log.username_snapshot ?? "System"} ·{" "}
                        {ACTION_LABELS[log.action] ?? log.action}
                    </Text>
                    {log.action !== "CREATE" &&
                        log.entries.map((entry) => (
                            <Text key={entry.field_name} size="sm">
                                {FIELD_LABELS[entry.field_name] ?? entry.field_name}: {entry.old_value ?? "–"} →{" "}
                                {entry.new_value ?? "–"}
                            </Text>
                        ))}
                </Stack>
            ))}
        </Stack>
    );
}
