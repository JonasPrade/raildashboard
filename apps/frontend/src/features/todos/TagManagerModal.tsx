import { useEffect, useState } from "react";
import { ActionIcon, Button, Group, Modal, Paper, Stack, Text, TextInput, Tooltip } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Trash2 } from "lucide-react";
import {
    useDeleteTodoTag,
    useTodoTags,
    useUpdateTodoTag,
    type TodoTag,
} from "../../shared/api/queries";
import { useIsMobile } from "../../shared/hooks/useBreakpoint";
import { openConfirmModal } from "../../shared/ui/confirmModal";

type Props = {
    opened: boolean;
    onClose: () => void;
    canDelete: boolean;
};

/** Rename tags, edit their description and delete them (Tags verwalten). */
export default function TagManagerModal({ opened, onClose, canDelete }: Props) {
    const isMobile = useIsMobile();
    const { data: tags } = useTodoTags(opened);

    return (
        <Modal opened={opened} onClose={onClose} title="Tags verwalten" size="lg" fullScreen={isMobile}>
            <Stack gap="sm">
                <Text size="sm" c="dimmed">
                    Umbenennen und Löschen wirken auf alle Aufgaben mit dem Tag und stehen in deren Verlauf.
                </Text>
                {(tags ?? []).length === 0 && <Text c="dimmed">Noch keine Tags.</Text>}
                {(tags ?? []).map((tag) => (
                    <TagRow key={tag.id} tag={tag} canDelete={canDelete} />
                ))}
            </Stack>
        </Modal>
    );
}

function TagRow({ tag, canDelete }: { tag: TodoTag; canDelete: boolean }) {
    const updateTag = useUpdateTodoTag();
    const deleteTag = useDeleteTodoTag();
    const [name, setName] = useState(tag.name);
    const [description, setDescription] = useState(tag.description ?? "");
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setName(tag.name);
        setDescription(tag.description ?? "");
    }, [tag.name, tag.description]);

    const trimmedName = name.trim();
    const trimmedDescription = description.trim();
    const dirty = trimmedName !== tag.name || trimmedDescription !== (tag.description ?? "");

    const handleSave = async () => {
        if (!trimmedName) {
            setError("Der Name darf nicht leer sein.");
            return;
        }
        setError(null);
        try {
            await updateTag.mutateAsync({
                id: tag.id,
                payload: {
                    name: trimmedName,
                    ...(trimmedDescription ? { description: trimmedDescription } : { clear_description: true }),
                },
            });
            notifications.show({ color: "teal", message: "Tag gespeichert." });
        } catch (err) {
            const status = (err as { status?: number }).status;
            setError(status === 409 ? `Es gibt schon ein Tag „${trimmedName}“.` : "Speichern fehlgeschlagen.");
        }
    };

    const confirmDelete = () => {
        openConfirmModal({
            title: "Tag löschen?",
            children: (
                <Text size="sm" mb="md">
                    „{tag.name}“ wird von {tag.todo_count} {tag.todo_count === 1 ? "Aufgabe" : "Aufgaben"} entfernt und
                    gelöscht.
                </Text>
            ),
            labels: { confirm: "Löschen", cancel: "Abbrechen" },
            danger: true,
            onConfirm: async () => {
                try {
                    await deleteTag.mutateAsync(tag.id);
                    notifications.show({ color: "teal", message: "Tag gelöscht." });
                } catch {
                    notifications.show({ color: "red", message: "Löschen fehlgeschlagen." });
                }
            },
        });
    };

    return (
        <Paper withBorder p="sm">
            <Stack gap="xs">
                <Group gap="xs" align="flex-end" wrap="wrap">
                    <TextInput
                        label="Name"
                        value={name}
                        onChange={(e) => setName(e.currentTarget.value)}
                        maxLength={50}
                        error={error}
                        flex="1 1 160px"
                    />
                    <TextInput
                        label="Beschreibung"
                        value={description}
                        onChange={(e) => setDescription(e.currentTarget.value)}
                        maxLength={1000}
                        flex="2 1 220px"
                    />
                </Group>
                <Group justify="space-between" align="center">
                    <Text size="xs" c="dimmed">
                        {tag.todo_count} {tag.todo_count === 1 ? "Aufgabe" : "Aufgaben"}
                    </Text>
                    <Group gap="xs">
                        {canDelete && (
                            <Tooltip label="Tag löschen" withArrow>
                                <ActionIcon variant="subtle" color="red" onClick={confirmDelete} aria-label="Tag löschen">
                                    <Trash2 size={16} />
                                </ActionIcon>
                            </Tooltip>
                        )}
                        <Button size="xs" onClick={handleSave} disabled={!dirty} loading={updateTag.isPending}>
                            Speichern
                        </Button>
                    </Group>
                </Group>
            </Stack>
        </Paper>
    );
}
