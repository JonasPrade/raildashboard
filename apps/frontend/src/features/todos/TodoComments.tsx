import { useState } from "react";
import { ActionIcon, Button, Divider, Group, Stack, Text, Textarea, Title, Tooltip } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Pencil, Trash2 } from "lucide-react";
import { useAuth } from "../../lib/auth";
import {
    useCreateTodoComment,
    useDeleteTodoComment,
    useTodoComments,
    useUpdateTodoComment,
    type TodoComment,
} from "../../shared/api/queries";
import { formatDateTimeShort } from "../../shared/format";
import { openConfirmModal } from "../../shared/ui/confirmModal";

const MAX_LENGTH = 10000;

/**
 * Comments on one task (oldest first): the current state of the work,
 * progress notes, open questions. Writing needs ``todo.edit``; only the
 * author edits a comment, the author or a ``todo.delete`` holder deletes it.
 */
export default function TodoComments({ todoId }: { todoId: number }) {
    const { user, can } = useAuth();
    const canComment = can("todo.edit");
    const canDeleteAny = can("todo.delete");
    const { data: comments } = useTodoComments(todoId);
    const createComment = useCreateTodoComment();
    const deleteComment = useDeleteTodoComment();
    const [draft, setDraft] = useState("");

    const handleAdd = async () => {
        const body = draft.trim();
        if (!body) return;
        try {
            await createComment.mutateAsync({ todoId, body });
            setDraft("");
        } catch {
            notifications.show({ color: "red", message: "Kommentar konnte nicht gespeichert werden." });
        }
    };

    const confirmDelete = (comment: TodoComment) => {
        openConfirmModal({
            title: "Kommentar löschen?",
            children: (
                <Text size="sm" mb="md">
                    Der Kommentar wird dauerhaft entfernt.
                </Text>
            ),
            labels: { confirm: "Löschen", cancel: "Abbrechen" },
            danger: true,
            onConfirm: async () => {
                try {
                    await deleteComment.mutateAsync({ todoId, commentId: comment.id });
                } catch {
                    notifications.show({ color: "red", message: "Löschen fehlgeschlagen." });
                }
            },
        });
    };

    return (
        <Stack gap="xs" mt="md">
            <Divider />
            <Title order={4}>Kommentare</Title>
            {(comments ?? []).length === 0 && (
                <Text size="sm" c="dimmed">
                    Noch keine Kommentare.
                </Text>
            )}
            {(comments ?? []).map((comment) => (
                <CommentItem
                    key={comment.id}
                    todoId={todoId}
                    comment={comment}
                    canEdit={canComment && user?.id === comment.user_id}
                    canDelete={canComment && (user?.id === comment.user_id || canDeleteAny)}
                    onDelete={confirmDelete}
                />
            ))}
            {canComment && (
                <Stack gap={6} mt={4}>
                    <Textarea
                        aria-label="Neuer Kommentar"
                        placeholder="Aktueller Stand, Zwischenergebnis, offene Fragen …"
                        autosize
                        minRows={2}
                        maxLength={MAX_LENGTH}
                        value={draft}
                        onChange={(e) => setDraft(e.currentTarget.value)}
                    />
                    <Group justify="flex-end">
                        <Button
                            size="xs"
                            variant="light"
                            onClick={handleAdd}
                            loading={createComment.isPending}
                            disabled={!draft.trim()}
                        >
                            Kommentieren
                        </Button>
                    </Group>
                </Stack>
            )}
        </Stack>
    );
}

type ItemProps = {
    todoId: number;
    comment: TodoComment;
    canEdit: boolean;
    canDelete: boolean;
    onDelete: (comment: TodoComment) => void;
};

function CommentItem({ todoId, comment, canEdit, canDelete, onDelete }: ItemProps) {
    const updateComment = useUpdateTodoComment();
    const [editing, setEditing] = useState(false);
    const [text, setText] = useState(comment.body);

    const handleSave = async () => {
        const body = text.trim();
        if (!body) return;
        try {
            await updateComment.mutateAsync({ todoId, commentId: comment.id, body });
            setEditing(false);
        } catch {
            notifications.show({ color: "red", message: "Kommentar konnte nicht gespeichert werden." });
        }
    };

    return (
        <Stack gap={2}>
            <Group justify="space-between" wrap="nowrap" align="center">
                <Text size="xs" c="dimmed">
                    {formatDateTimeShort(comment.created_at)} · {comment.username_snapshot ?? "Unbekannt"}
                    {comment.edited_at ? " · bearbeitet" : ""}
                </Text>
                {!editing && (canEdit || canDelete) && (
                    <Group gap={2} wrap="nowrap">
                        {canEdit && (
                            <Tooltip label="Bearbeiten" withArrow>
                                <ActionIcon
                                    size="sm"
                                    variant="subtle"
                                    color="gray"
                                    aria-label="Kommentar bearbeiten"
                                    onClick={() => {
                                        setText(comment.body);
                                        setEditing(true);
                                    }}
                                >
                                    <Pencil size={14} />
                                </ActionIcon>
                            </Tooltip>
                        )}
                        {canDelete && (
                            <Tooltip label="Löschen" withArrow>
                                <ActionIcon
                                    size="sm"
                                    variant="subtle"
                                    color="red"
                                    aria-label="Kommentar löschen"
                                    onClick={() => onDelete(comment)}
                                >
                                    <Trash2 size={14} />
                                </ActionIcon>
                            </Tooltip>
                        )}
                    </Group>
                )}
            </Group>
            {editing ? (
                <Stack gap={6}>
                    <Textarea
                        aria-label="Kommentar"
                        autosize
                        minRows={2}
                        maxLength={MAX_LENGTH}
                        value={text}
                        onChange={(e) => setText(e.currentTarget.value)}
                    />
                    <Group justify="flex-end" gap="xs">
                        <Button size="xs" variant="subtle" color="gray" onClick={() => setEditing(false)}>
                            Abbrechen
                        </Button>
                        <Button size="xs" onClick={handleSave} loading={updateComment.isPending} disabled={!text.trim()}>
                            Speichern
                        </Button>
                    </Group>
                </Stack>
            ) : (
                <Text size="sm" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                    {comment.body}
                </Text>
            )}
        </Stack>
    );
}
