import { useEffect, useRef, useState } from "react";
import {
    ActionIcon,
    Alert,
    Anchor,
    Badge,
    Button,
    Card,
    Group,
    Loader,
    Modal,
    Select,
    Stack,
    Text,
    Textarea,
    TextInput,
    Title,
    Tooltip,
} from "@mantine/core";
import { IconEye } from "@tabler/icons-react";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";

import {
    type ProjectText,
    type ProjectTextCreate,
    type ProjectTextUpdate,
    type TextAttachment,
    useCreateProjectText,
    useCreateTextType,
    useDeleteProjectText,
    useDeleteTextAttachment,
    useProjectTexts,
    useTextTypes,
    useUpdateProjectText,
    useUploadTextAttachment,
} from "../../shared/api/queries";
import { API_BASE } from "../../shared/api/client";
import PdfPreviewModal from "./PdfPreviewModal";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileTypeIcon(mimeType: string): string {
    if (mimeType === "application/pdf") return "📄";
    if (mimeType.startsWith("image/")) return "🖼️";
    if (mimeType.includes("word") || mimeType.includes("msword")) return "📝";
    if (mimeType.includes("excel") || mimeType.includes("spreadsheet")) return "📊";
    return "📎";
}

const ACCEPTED_MIME = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "image/jpeg",
    "image/png",
].join(",");

const MAX_FILE_BYTES = 50 * 1024 * 1024;

// ── Create text type modal ────────────────────────────────────────────────────

type CreateTextTypeModalProps = {
    opened: boolean;
    onClose: () => void;
    onCreated: (newTypeId: string) => void;
};

function CreateTextTypeModal({ opened, onClose, onCreated }: CreateTextTypeModalProps) {
    const [name, setName] = useState("");
    const createTypeMutation = useCreateTextType();

    function handleSubmit() {
        const trimmed = name.trim();
        if (!trimmed) return;
        createTypeMutation.mutate(trimmed, {
            onSuccess: (newType) => {
                notifications.show({
                    color: "green",
                    title: "Typ erstellt",
                    message: `Der Typ „${newType.name}" wurde angelegt.`,
                });
                onCreated(String(newType.id));
            },
            onError: () => {
                notifications.show({
                    color: "red",
                    title: "Erstellen fehlgeschlagen",
                    message: "Der Typ konnte nicht erstellt werden.",
                });
            },
        });
    }

    return (
        <Modal opened={opened} onClose={onClose} title="Neuen Typ erstellen" size="sm">
            <Stack gap="md">
                <TextInput
                    label="Typname"
                    required
                    value={name}
                    onChange={(event) => setName(event.currentTarget.value)}
                    placeholder="z. B. Pressemitteilung"
                />
                <Group justify="flex-end">
                    <Button variant="default" onClick={onClose} disabled={createTypeMutation.isPending}>
                        Abbrechen
                    </Button>
                    <Button
                        onClick={handleSubmit}
                        loading={createTypeMutation.isPending}
                        disabled={name.trim() === ""}
                    >
                        Erstellen
                    </Button>
                </Group>
            </Stack>
        </Modal>
    );
}

// ── Text form (shared for create + edit) ─────────────────────────────────────

type TextFormValues = {
    header: string;
    text: string;
    weblink: string;
    logo_url: string;
    type: string | null;
};

function emptyForm(): TextFormValues {
    return { header: "", text: "", weblink: "", logo_url: "", type: null };
}

function fromText(t: ProjectText): TextFormValues {
    return {
        header: t.header,
        text: t.text ?? "",
        weblink: t.weblink ?? "",
        logo_url: t.logo_url ?? "",
        type: String(t.type),
    };
}

type TextFormModalProps = {
    opened: boolean;
    onClose: () => void;
    onSubmit: (values: TextFormValues, files: File[]) => void;
    isSubmitting: boolean;
    initialValues: TextFormValues;
    title: string;
    showFileUpload?: boolean;
};

function TextFormModal({ opened, onClose, onSubmit, isSubmitting, initialValues, title, showFileUpload }: TextFormModalProps) {
    const [values, setValues] = useState<TextFormValues>(initialValues);
    const [pendingFiles, setPendingFiles] = useState<File[]>([]);
    const [createTypeOpened, setCreateTypeOpened] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const { data: textTypes } = useTextTypes();

    // Reset form whenever the modal opens
    useEffect(() => {
        if (opened) {
            setValues(initialValues);
            setPendingFiles([]);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [opened]);

    function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
        const selected = Array.from(e.currentTarget.files ?? []);
        const valid = selected.filter((f) => {
            if (f.size > MAX_FILE_BYTES) {
                notifications.show({ color: "red", title: "Datei zu groß", message: `„${f.name}" überschreitet 50 MB.` });
                return false;
            }
            return true;
        });
        setPendingFiles((prev) => [...prev, ...valid]);
        if (fileInputRef.current) fileInputRef.current.value = "";
    }

    const typeOptions = (textTypes ?? []).map((t) => ({
        value: String(t.id),
        label: t.name,
    }));

    const isValid = values.header.trim() !== "" && values.type !== null;

    function handleTypeCreated(newTypeId: string) {
        setCreateTypeOpened(false);
        setValues((prev) => ({ ...prev, type: newTypeId }));
    }

    return (
        <>
            <Modal opened={opened} onClose={onClose} title={title} size="lg">
                <Stack gap="md">
                    <TextInput
                        label="Überschrift"
                        required
                        value={values.header}
                        onChange={(event) => { const v = event.currentTarget.value; setValues((prev) => ({ ...prev, header: v })); }}
                    />

                    <Group gap="xs" align="flex-end">
                        <Select
                            label="Typ"
                            required
                            data={typeOptions}
                            value={values.type}
                            onChange={(value) => setValues((prev) => ({ ...prev, type: value }))}
                            placeholder="Typ auswählen"
                            style={{ flex: 1 }}
                        />
                        <Tooltip label="Neuen Typ erstellen">
                            <ActionIcon
                                variant="light"
                                size="lg"
                                onClick={() => setCreateTypeOpened(true)}
                                aria-label="Neuen Typ erstellen"
                            >
                                +
                            </ActionIcon>
                        </Tooltip>
                    </Group>

                    <Textarea
                        label="Text"
                        minRows={4}
                        autosize
                        value={values.text}
                        onChange={(event) => { const v = event.currentTarget.value; setValues((prev) => ({ ...prev, text: v })); }}
                    />

                    <TextInput
                        label="Weblink"
                        placeholder="https://…"
                        value={values.weblink}
                        onChange={(event) => { const v = event.currentTarget.value; setValues((prev) => ({ ...prev, weblink: v })); }}
                    />

                    <TextInput
                        label="Logo-URL"
                        placeholder="https://…"
                        value={values.logo_url}
                        onChange={(event) => { const v = event.currentTarget.value; setValues((prev) => ({ ...prev, logo_url: v })); }}
                    />

                    {showFileUpload && (
                        <Stack gap={4}>
                            <Text size="sm" fw={500}>Anhänge</Text>
                            <input
                                ref={fileInputRef}
                                type="file"
                                multiple
                                accept={ACCEPTED_MIME}
                                style={{ display: "none" }}
                                onChange={handleFileSelect}
                            />
                            <Button
                                size="xs"
                                variant="subtle"
                                leftSection="📎"
                                onClick={() => fileInputRef.current?.click()}
                            >
                                Dateien auswählen
                            </Button>
                            {pendingFiles.map((f) => (
                                <Group key={f.name} justify="space-between" align="center" wrap="nowrap">
                                    <Text size="xs" c="dimmed" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                        📎 {f.name} ({formatBytes(f.size)})
                                    </Text>
                                    <ActionIcon
                                        size="xs"
                                        variant="subtle"
                                        color="red"
                                        onClick={() => setPendingFiles((prev) => prev.filter((x) => x.name !== f.name))}
                                        aria-label={`${f.name} entfernen`}
                                    >
                                        ×
                                    </ActionIcon>
                                </Group>
                            ))}
                        </Stack>
                    )}

                    <Group justify="flex-end">
                        <Button variant="default" onClick={onClose} disabled={isSubmitting}>
                            Abbrechen
                        </Button>
                        <Button onClick={() => onSubmit(values, pendingFiles)} loading={isSubmitting} disabled={!isValid}>
                            Speichern
                        </Button>
                    </Group>
                </Stack>
            </Modal>

            <CreateTextTypeModal
                opened={createTypeOpened}
                onClose={() => setCreateTypeOpened(false)}
                onCreated={handleTypeCreated}
            />
        </>
    );
}

// ── Attachment list ───────────────────────────────────────────────────────────

type AttachmentListProps = {
    attachments: TextAttachment[];
    textId: number;
    projectId: number;
    canEdit: boolean;
};

function AttachmentList({ attachments, textId, projectId, canEdit }: AttachmentListProps) {
    const deleteMutation = useDeleteTextAttachment(projectId);
    const [previewAttachment, setPreviewAttachment] = useState<TextAttachment | null>(null);

    if (attachments.length === 0) return null;

    function handleDelete(attachment: TextAttachment) {
        modals.openConfirmModal({
            title: "Anhang löschen",
            children: (
                <Text size="sm">
                    Soll „{attachment.filename}" wirklich gelöscht werden?
                </Text>
            ),
            labels: { confirm: "Löschen", cancel: "Abbrechen" },
            confirmProps: { color: "red" },
            onConfirm: () => {
                deleteMutation.mutate(
                    { textId, attachmentId: attachment.id },
                    {
                        onError: () => {
                            notifications.show({
                                color: "red",
                                title: "Löschen fehlgeschlagen",
                                message: "Der Anhang konnte nicht gelöscht werden.",
                            });
                        },
                    },
                );
            },
        });
    }

    return (
        <>
            <Stack gap={4}>
                {attachments.map((a) => (
                    <Group key={a.id} justify="space-between" align="center" wrap="nowrap">
                        <Group gap="xs" align="center" style={{ minWidth: 0 }}>
                            <Text size="sm">{fileTypeIcon(a.mime_type)}</Text>
                            <Anchor
                                href={`${API_BASE}/api/v1/projects/texts/${textId}/attachments/${a.id}/download`}
                                size="sm"
                                style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                            >
                                {a.filename}
                            </Anchor>
                            <Badge size="xs" variant="outline" color="gray">
                                {formatBytes(a.file_size)}
                            </Badge>
                        </Group>
                        <Group gap={4} wrap="nowrap">
                            {a.mime_type === "application/pdf" && (
                                <Tooltip label="Vorschau">
                                    <ActionIcon
                                        size="xs"
                                        variant="subtle"
                                        color="blue"
                                        onClick={() => setPreviewAttachment(a)}
                                        aria-label={`PDF-Vorschau ${a.filename}`}
                                    >
                                        <IconEye size={12} />
                                    </ActionIcon>
                                </Tooltip>
                            )}
                            {canEdit && (
                                <ActionIcon
                                    size="xs"
                                    variant="subtle"
                                    color="red"
                                    loading={deleteMutation.isPending}
                                    onClick={() => handleDelete(a)}
                                    aria-label={`Anhang ${a.filename} löschen`}
                                >
                                    ×
                                </ActionIcon>
                            )}
                        </Group>
                    </Group>
                ))}
            </Stack>

            {previewAttachment && (
                <PdfPreviewModal
                    opened={previewAttachment !== null}
                    onClose={() => setPreviewAttachment(null)}
                    attachmentUrl={`${API_BASE}/api/v1/projects/texts/${textId}/attachments/${previewAttachment.id}/download?inline=true`}
                    filename={previewAttachment.filename}
                />
            )}
        </>
    );
}

// ── Attachment upload area ────────────────────────────────────────────────────

type AttachmentUploadAreaProps = {
    textId: number;
    projectId: number;
};

type UploadState = { filename: string; status: "uploading" | "done" | "error"; error?: string };

function AttachmentUploadArea({ textId, projectId }: AttachmentUploadAreaProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [uploads, setUploads] = useState<UploadState[]>([]);
    const uploadMutation = useUploadTextAttachment(projectId);

    function handleFiles(files: FileList | null) {
        if (!files || files.length === 0) return;

        Array.from(files).forEach((file) => {
            if (file.size > MAX_FILE_BYTES) {
                notifications.show({
                    color: "red",
                    title: "Datei zu groß",
                    message: `„${file.name}" überschreitet das Limit von 50 MB.`,
                });
                return;
            }

            setUploads((prev) => [...prev, { filename: file.name, status: "uploading" }]);

            uploadMutation.mutate({ textId, file }, {
                onSuccess: () => {
                    setUploads((prev) =>
                        prev.map((u) => (u.filename === file.name ? { ...u, status: "done" } : u)),
                    );
                    // Clear done entries after a short delay
                    setTimeout(() => {
                        setUploads((prev) => prev.filter((u) => u.filename !== file.name));
                    }, 2000);
                },
                onError: (err) => {
                    const message =
                        (err as { details?: { detail?: string } })?.details?.detail ??
                        "Upload fehlgeschlagen";
                    setUploads((prev) =>
                        prev.map((u) =>
                            u.filename === file.name ? { ...u, status: "error", error: message } : u,
                        ),
                    );
                },
            });
        });

        // Reset input so the same file can be selected again
        if (fileInputRef.current) fileInputRef.current.value = "";
    }

    return (
        <Stack gap={4}>
            <input
                ref={fileInputRef}
                type="file"
                multiple
                accept={ACCEPTED_MIME}
                style={{ display: "none" }}
                onChange={(e) => handleFiles(e.currentTarget.files)}
            />
            <Button
                size="xs"
                variant="subtle"
                leftSection="📎"
                onClick={() => fileInputRef.current?.click()}
            >
                Anhang hinzufügen
            </Button>
            {uploads.map((u) => (
                <Group key={u.filename} gap="xs" align="center">
                    {u.status === "uploading" && <Loader size="xs" />}
                    {u.status === "done" && <Text size="xs" c="green">✓</Text>}
                    {u.status === "error" && <Text size="xs" c="red">✗</Text>}
                    <Text size="xs" c={u.status === "error" ? "red" : "dimmed"}>
                        {u.filename}{u.status === "error" ? ` — ${u.error}` : ""}
                    </Text>
                </Group>
            ))}
        </Stack>
    );
}

// ── Single text card ──────────────────────────────────────────────────────────

type TextCardProps = {
    projectText: ProjectText;
    canEdit: boolean;
    projectId: number;
};

function TextCard({ projectText, canEdit, projectId }: TextCardProps) {
    const [editOpened, setEditOpened] = useState(false);
    const updateMutation = useUpdateProjectText(projectId);
    const deleteMutation = useDeleteProjectText(projectId);

    function handleEdit(values: TextFormValues, _files: File[]) {
        if (!values.type) return;
        const payload: ProjectTextUpdate = {
            header: values.header.trim(),
            text: values.text.trim() || null,
            weblink: values.weblink.trim() || null,
            logo_url: values.logo_url.trim() || null,
            type: Number(values.type),
        };
        updateMutation.mutate(
            { textId: projectText.id, payload },
            {
                onSuccess: () => {
                    setEditOpened(false);
                    notifications.show({
                        color: "green",
                        title: "Text aktualisiert",
                        message: "Der Text wurde erfolgreich gespeichert.",
                    });
                },
                onError: () => {
                    notifications.show({
                        color: "red",
                        title: "Speichern fehlgeschlagen",
                        message: "Der Text konnte nicht gespeichert werden.",
                    });
                },
            },
        );
    }

    function handleDelete() {
        deleteMutation.mutate(projectText.id, {
            onSuccess: () => {
                notifications.show({
                    color: "green",
                    title: "Text gelöscht",
                    message: "Der Text wurde entfernt.",
                });
            },
            onError: () => {
                notifications.show({
                    color: "red",
                    title: "Löschen fehlgeschlagen",
                    message: "Der Text konnte nicht gelöscht werden.",
                });
            },
        });
    }

    return (
        <>
            <Card withBorder radius="sm" padding="md">
                <Stack gap="xs">
                    <Group justify="space-between" align="flex-start">
                        <Stack gap={2}>
                            <Text fw={600}>{projectText.header}</Text>
                            <Text size="xs" c="dimmed">
                                {projectText.text_type.name}
                            </Text>
                        </Stack>
                        {canEdit && (
                            <Group gap="xs">
                                <Button size="xs" variant="subtle" onClick={() => setEditOpened(true)}>
                                    Bearbeiten
                                </Button>
                                <Button
                                    size="xs"
                                    variant="subtle"
                                    color="red"
                                    loading={deleteMutation.isPending}
                                    onClick={handleDelete}
                                >
                                    Löschen
                                </Button>
                            </Group>
                        )}
                    </Group>
                    {projectText.text && (
                        <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                            {projectText.text}
                        </Text>
                    )}
                    {projectText.weblink && (
                        <Anchor href={projectText.weblink} target="_blank" size="sm">
                            {projectText.weblink}
                        </Anchor>
                    )}
                    <AttachmentList
                        attachments={projectText.attachments}
                        textId={projectText.id}
                        projectId={projectId}
                        canEdit={canEdit}
                    />
                    {canEdit && (
                        <AttachmentUploadArea textId={projectText.id} projectId={projectId} />
                    )}
                </Stack>
            </Card>

            <TextFormModal
                opened={editOpened}
                onClose={() => setEditOpened(false)}
                onSubmit={handleEdit}
                isSubmitting={updateMutation.isPending}
                initialValues={fromText(projectText)}
                title="Text bearbeiten"
            />
        </>
    );
}

// ── Section ───────────────────────────────────────────────────────────────────

type ProjectTextsSectionProps = {
    projectId: number;
    canEdit: boolean;
};

export default function ProjectTextsSection({ projectId, canEdit }: ProjectTextsSectionProps) {
    const [createOpened, setCreateOpened] = useState(false);
    const { data, isLoading, isError } = useProjectTexts(projectId);
    const createMutation = useCreateProjectText(projectId);
    const uploadMutation = useUploadTextAttachment(projectId);

    function handleCreate(values: TextFormValues, files: File[]) {
        if (!values.type) return;
        const payload: ProjectTextCreate = {
            header: values.header.trim(),
            text: values.text.trim() || null,
            weblink: values.weblink.trim() || null,
            logo_url: values.logo_url.trim() || null,
            type: Number(values.type),
        };
        createMutation.mutate(payload, {
            onSuccess: (createdText) => {
                setCreateOpened(false);
                notifications.show({
                    color: "green",
                    title: "Text erstellt",
                    message: "Der neue Text wurde gespeichert.",
                });
                // Upload any files that were selected during creation
                files.forEach((file) => {
                    uploadMutation.mutate(
                        { textId: createdText.id, file },
                        {
                            onError: () => {
                                notifications.show({
                                    color: "red",
                                    title: "Upload fehlgeschlagen",
                                    message: `„${file.name}" konnte nicht hochgeladen werden.`,
                                });
                            },
                        },
                    );
                });
            },
            onError: () => {
                notifications.show({
                    color: "red",
                    title: "Erstellen fehlgeschlagen",
                    message: "Der Text konnte nicht erstellt werden.",
                });
            },
        });
    }

    if (isLoading) {
        return (
            <Card withBorder radius="md" padding="lg" shadow="xs">
                <Loader size="sm" />
            </Card>
        );
    }

    if (isError) {
        return (
            <Card withBorder radius="md" padding="lg" shadow="xs">
                <Alert color="red" variant="light">
                    Texte konnten nicht geladen werden.
                </Alert>
            </Card>
        );
    }

    const hasTexts = data && data.length > 0;

    if (!hasTexts && !canEdit) {
        return null;
    }

    return (
        <>
            <Card withBorder radius="md" padding="lg" shadow="xs">
                <Stack gap="sm">
                    <Group justify="space-between" align="center">
                        <Title order={4}>Texte</Title>
                        {canEdit && (
                            <Button size="xs" variant="light" onClick={() => setCreateOpened(true)}>
                                Text hinzufügen
                            </Button>
                        )}
                    </Group>
                    {hasTexts ? (
                        <Stack gap="sm">
                            {data.map((t) => (
                                <TextCard key={t.id} projectText={t} canEdit={canEdit} projectId={projectId} />
                            ))}
                        </Stack>
                    ) : (
                        <Text size="sm" c="dimmed">
                            Noch keine Texte vorhanden.
                        </Text>
                    )}
                </Stack>
            </Card>

            <TextFormModal
                opened={createOpened}
                onClose={() => setCreateOpened(false)}
                onSubmit={handleCreate}
                isSubmitting={createMutation.isPending}
                initialValues={emptyForm()}
                title="Text hinzufügen"
                showFileUpload
            />
        </>
    );
}
