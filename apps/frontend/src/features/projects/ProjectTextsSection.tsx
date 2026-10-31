import { lazy, Suspense, useEffect, useRef, useState } from "react";
import {
    ActionIcon,
    Anchor,
    Badge,
    Button,
    Group,
    Modal,
    Paper,
    Radio,
    Select,
    Stack,
    Switch,
    Text,
    Textarea,
    TextInput,
    Title,
    Tooltip,
} from "@mantine/core";
import { Check, Eye, FileImage, FileSpreadsheet, FileText, Lock, Paperclip } from "lucide-react";
import { openConfirmModal } from "../../shared/ui/confirmModal";
import { ExternalLinkButton } from "../../shared/ui/ExternalLinkButton";
import { notifications } from "@mantine/notifications";

import {
    type ProjectText,
    type ProjectTextCategory,
    type ProjectTextCreate,
    type ProjectTextUpdate,
    type TextAttachment,
    useCreateProjectText,
    useCreateTextCategory,
    useCreateTextType,
    useDeleteProjectText,
    useDeleteTextAttachment,
    useProjectTexts,
    useTextCategories,
    useTextTypes,
    useUpdateProjectText,
    useUploadTextAttachment,
} from "../../shared/api/queries";
import { exceedsUploadLimit, tooLargeMessage } from "../../shared/api/uploads";
import { FileDropZone } from "../../shared/ui/FileDropZone";
import { API_BASE } from "../../shared/api/client";
import {
    TEXT_CATEGORY_STYLE_ORDER,
    TEXT_CATEGORY_STYLES,
    textCardStyle,
    type TextCategoryStyle,
    categoryOf,
    defaultCategory,
} from "./textCategoryStyles";
import { LoadingState } from "../../shared/ui/LoadingState";
import { ErrorState } from "../../shared/ui/ErrorState";

// Lazy: pulls in react-pdf/pdfjs (~400 KB) only when a preview is opened.
const PdfPreviewModal = lazy(() => import("./PdfPreviewModal"));

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Lucide icon for an attachment's file type (no emoji, DESIGN.md). */
function FileTypeIcon({ mimeType }: { mimeType: string }) {
    const props = { size: 16, "aria-hidden": true, style: { flex: "none" } } as const;
    if (mimeType === "application/pdf") return <FileText {...props} />;
    if (mimeType.startsWith("image/")) return <FileImage {...props} />;
    if (mimeType.includes("word") || mimeType.includes("msword")) return <FileText {...props} />;
    if (mimeType.includes("excel") || mimeType.includes("spreadsheet")) return <FileSpreadsheet {...props} />;
    return <Paperclip {...props} />;
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
                <div className="idt-modal-footer">
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
                </div>
            </Stack>
        </Modal>
    );
}

// ── Create text category modal ────────────────────────────────────────────────

type CreateTextCategoryModalProps = {
    opened: boolean;
    onClose: () => void;
    onCreated: (newCategoryId: string) => void;
};

function CreateTextCategoryModal({ opened, onClose, onCreated }: CreateTextCategoryModalProps) {
    const [name, setName] = useState("");
    const [style, setStyle] = useState<TextCategoryStyle>("info");
    const createCategoryMutation = useCreateTextCategory();

    useEffect(() => {
        if (opened) {
            setName("");
            setStyle("info");
        }
    }, [opened]);

    function handleSubmit() {
        const trimmed = name.trim();
        if (!trimmed) return;
        createCategoryMutation.mutate({ name: trimmed, style }, {
            onSuccess: (newCategory) => {
                notifications.show({
                    color: "green",
                    title: "Kategorie erstellt",
                    message: `Die Kategorie „${newCategory.name}" wurde angelegt.`,
                });
                onCreated(String(newCategory.id));
            },
            onError: (err) => {
                const status = (err as { status?: number })?.status;
                notifications.show({
                    color: "red",
                    title: "Erstellen fehlgeschlagen",
                    message: status === 409
                        ? "Diese Kategorie gibt es schon."
                        : "Die Kategorie konnte nicht erstellt werden.",
                });
            },
        });
    }

    return (
        <Modal opened={opened} onClose={onClose} title="Neue Kategorie erstellen" size="sm">
            <Stack gap="md">
                <TextInput
                    label="Name"
                    required
                    value={name}
                    onChange={(event) => setName(event.currentTarget.value)}
                    placeholder="z. B. Hinweis"
                />
                <Radio.Group
                    label="Darstellung"
                    value={style}
                    onChange={(value) => setStyle(value as TextCategoryStyle)}
                >
                    <Stack gap="xs" mt={4}>
                        {TEXT_CATEGORY_STYLE_ORDER.map((key) => {
                            const display = TEXT_CATEGORY_STYLES[key];
                            const StyleIcon = display.icon;
                            return (
                                <Radio
                                    key={key}
                                    value={key}
                                    label={
                                        <Group gap={6} wrap="nowrap">
                                            <span
                                                aria-hidden
                                                style={{ width: 8, height: 16, background: display.edge ?? "transparent" }}
                                            />
                                            <StyleIcon size={16} color={display.iconColor} aria-hidden />
                                            <span>{display.label}</span>
                                        </Group>
                                    }
                                />
                            );
                        })}
                    </Stack>
                </Radio.Group>
                <div className="idt-modal-footer">
                    <Button variant="default" onClick={onClose} disabled={createCategoryMutation.isPending}>
                        Abbrechen
                    </Button>
                    <Button
                        onClick={handleSubmit}
                        loading={createCategoryMutation.isPending}
                        disabled={name.trim() === ""}
                    >
                        Erstellen
                    </Button>
                </div>
            </Stack>
        </Modal>
    );
}

// ── Category label (icon + name, colour from the style) ─────────────────────

function CategoryLabel({ category }: { category: ProjectTextCategory }) {
    const display = TEXT_CATEGORY_STYLES[category.style];
    const StyleIcon = display.icon;
    return (
        <Group gap={4} wrap="nowrap">
            {/* Icon in ink (critical red); amber and cyan only on the card edge (W5). */}
            <StyleIcon size={14} color={display.iconColor} aria-hidden />
            <Text span size="xs" fw={600} style={{ color: "var(--text-body)" }}>
                {category.name}
            </Text>
        </Group>
    );
}

// ── Text form (shared for create + edit) ─────────────────────────────────────

type TextFormValues = {
    header: string;
    text: string;
    weblink: string;
    logo_url: string;
    type: string | null;
    /** null in the create form until the categories have loaded → default. */
    category: string | null;
    is_public: boolean;
};

function emptyForm(): TextFormValues {
    return { header: "", text: "", weblink: "", logo_url: "", type: null, category: null, is_public: true };
}

function fromText(t: ProjectText): TextFormValues {
    return {
        header: t.header,
        text: t.text ?? "",
        weblink: t.weblink ?? "",
        logo_url: t.logo_url ?? "",
        type: String(t.type),
        category: t.category_id != null ? String(t.category_id) : null,
        is_public: t.is_public ?? true,
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
    const [createCategoryOpened, setCreateCategoryOpened] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const { data: textTypes } = useTextTypes();
    const { data: categories } = useTextCategories();

    // Reset form whenever the modal opens
    useEffect(() => {
        if (opened) {
            setValues(initialValues);
            setPendingFiles([]);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [opened]);

    function addFiles(selected: File[]) {
        const valid = selected.filter((f) => {
            if (exceedsUploadLimit(f)) {
                notifications.show({ color: "red", title: "Datei zu groß", message: tooLargeMessage(f) });
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

    const categoryOptions = (categories ?? []).map((c) => ({
        value: String(c.id),
        label: c.name,
    }));
    // Texts without a category (older code) and the fresh create form show the default.
    const fallbackCategory = defaultCategory(categories);
    const categoryValue = values.category ?? (fallbackCategory ? String(fallbackCategory.id) : null);

    const isValid = values.header.trim() !== "" && values.type !== null && categoryValue !== null;

    function handleTypeCreated(newTypeId: string) {
        setCreateTypeOpened(false);
        setValues((prev) => ({ ...prev, type: newTypeId }));
    }

    function handleCategoryCreated(newCategoryId: string) {
        setCreateCategoryOpened(false);
        setValues((prev) => ({ ...prev, category: newCategoryId }));
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

                    <Group gap="xs" align="flex-end">
                        <Select
                            label="Kategorie"
                            required
                            data={categoryOptions}
                            value={categoryValue}
                            onChange={(value) => setValues((prev) => ({ ...prev, category: value }))}
                            placeholder="Kategorie auswählen"
                            style={{ flex: 1 }}
                        />
                        <Tooltip label="Neue Kategorie erstellen">
                            <ActionIcon
                                variant="light"
                                size="lg"
                                onClick={() => setCreateCategoryOpened(true)}
                                aria-label="Neue Kategorie erstellen"
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

                    <Switch
                        label="Nur für Eingeloggte sichtbar"
                        description="Interne Texte und ihre Anhänge sehen Besucher ohne Anmeldung nicht."
                        checked={!values.is_public}
                        onChange={(event) => { const internal = event.currentTarget.checked; setValues((prev) => ({ ...prev, is_public: !internal })); }}
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
                                onChange={(e) => addFiles(Array.from(e.currentTarget.files ?? []))}
                            />
                            <FileDropZone accept={ACCEPTED_MIME} multiple onFiles={addFiles} label="Dateien hier ablegen">
                                <Button
                                    size="xs"
                                    variant="subtle"
                                    leftSection={<Paperclip size={16} aria-hidden />}
                                    fullWidth
                                    onClick={() => fileInputRef.current?.click()}
                                >
                                    Dateien auswählen oder hierher ziehen
                                </Button>
                            </FileDropZone>
                            {pendingFiles.map((f) => (
                                <Group key={f.name} justify="space-between" align="center" wrap="nowrap">
                                    <Text size="xs" c="dimmed" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                        {f.name} ({formatBytes(f.size)})
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

                    <div className="idt-modal-footer">
                        <Button variant="default" onClick={onClose} disabled={isSubmitting}>
                            Abbrechen
                        </Button>
                        <Button onClick={() => onSubmit({ ...values, category: categoryValue }, pendingFiles)} loading={isSubmitting} disabled={!isValid}>
                            Speichern
                        </Button>
                    </div>
                </Stack>
            </Modal>

            <CreateTextTypeModal
                opened={createTypeOpened}
                onClose={() => setCreateTypeOpened(false)}
                onCreated={handleTypeCreated}
            />

            <CreateTextCategoryModal
                opened={createCategoryOpened}
                onClose={() => setCreateCategoryOpened(false)}
                onCreated={handleCategoryCreated}
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
        openConfirmModal({
            title: "Anhang löschen",
            children: (
                <Text size="sm">
                    Soll „{attachment.filename}" wirklich gelöscht werden?
                </Text>
            ),
            labels: { confirm: "Löschen", cancel: "Abbrechen" },
            danger: true,
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
                            <FileTypeIcon mimeType={a.mime_type} />
                            <Anchor
                                href={`${API_BASE}/api/v1/projects/texts/${textId}/attachments/${a.id}/download`}
                                size="sm"
                                style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                            >
                                {a.filename}
                            </Anchor>
                            <Badge variant="outline">{formatBytes(a.file_size)}</Badge>
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
                                        <Eye size={12} />
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
                <Suspense fallback={null}>
                    <PdfPreviewModal
                        opened={previewAttachment !== null}
                        onClose={() => setPreviewAttachment(null)}
                        attachmentUrl={`${API_BASE}/api/v1/projects/texts/${textId}/attachments/${previewAttachment.id}/download?inline=true`}
                        filename={previewAttachment.filename}
                    />
                </Suspense>
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

    function handleFiles(files: File[]) {
        files.forEach((file) => {
            if (exceedsUploadLimit(file)) {
                notifications.show({
                    color: "red",
                    title: "Datei zu groß",
                    message: tooLargeMessage(file),
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
                onChange={(e) => handleFiles(Array.from(e.currentTarget.files ?? []))}
            />
            <FileDropZone accept={ACCEPTED_MIME} multiple onFiles={handleFiles} label="Anhänge hier ablegen">
                <Button
                    size="xs"
                    variant="subtle"
                    leftSection={<Paperclip size={16} aria-hidden />}
                    fullWidth
                    onClick={() => fileInputRef.current?.click()}
                >
                    Anhang hinzufügen oder hierher ziehen
                </Button>
            </FileDropZone>
            {uploads.map((u) => (
                <Group key={u.filename} gap="xs" align="center">
                    {u.status === "uploading" && <Text size="xs" c="dimmed">…</Text>}
                    {u.status === "done" && <Check size={12} aria-label="hochgeladen" />}
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
    const { data: categories } = useTextCategories();
    const category = categoryOf(projectText, categories);
    const display = category ? TEXT_CATEGORY_STYLES[category.style] : null;
    const updateMutation = useUpdateProjectText(projectId);
    const deleteMutation = useDeleteProjectText(projectId);

    function handleEdit(values: TextFormValues) {
        if (!values.type) return;
        const payload: ProjectTextUpdate = {
            header: values.header.trim(),
            text: values.text.trim() || null,
            weblink: values.weblink.trim() || null,
            logo_url: values.logo_url.trim() || null,
            type: Number(values.type),
            category_id: values.category ? Number(values.category) : undefined,
            is_public: values.is_public,
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
        openConfirmModal({
            title: "Text löschen?",
            children: (
                <Text size="sm" mb="md">
                    „{projectText.header}" wird dauerhaft entfernt.
                </Text>
            ),
            labels: { confirm: "Löschen", cancel: "Abbrechen" },
            danger: true,
            onConfirm: () => deleteText(),
        });
    }

    function deleteText() {
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
            {/* DS callout: 8px edge in the category colour, no frame, no fill. */}
            <div style={{ ...textCardStyle(display?.edge ?? null), paddingTop: 4, paddingBottom: 4 }}>
                <Stack gap="xs">
                    <Group justify="space-between" align="flex-start">
                        <Stack gap={2} style={{ minWidth: 0 }}>
                            <Text fw={600}>{projectText.header}</Text>
                            <Group gap={6} wrap="wrap">
                                {category && <CategoryLabel category={category} />}
                                {category && <Text size="xs" c="dimmed" aria-hidden>·</Text>}
                                <Text size="xs" c="dimmed">
                                    {projectText.text_type.name}
                                </Text>
                                {projectText.is_public === false && (
                                    <Group gap={3} wrap="nowrap" c="dimmed">
                                        <Lock size={12} aria-hidden />
                                        <Text size="xs" c="dimmed">Intern</Text>
                                    </Group>
                                )}
                            </Group>
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
                        <ExternalLinkButton url={projectText.weblink} />
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
            </div>

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
    const { data, isLoading, isError, refetch } = useProjectTexts(projectId);
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
            category_id: values.category ? Number(values.category) : null,
            is_public: values.is_public,
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
            <Paper withBorder p="var(--card-pad)">
                <LoadingState rows={3} />
            </Paper>
        );
    }

    if (isError) {
        return (
            <Paper withBorder p="var(--card-pad)">
                <ErrorState onRetry={() => void refetch()}>Texte konnten nicht geladen werden.</ErrorState>
            </Paper>
        );
    }

    const hasTexts = data && data.length > 0;

    if (!hasTexts && !canEdit) {
        return null;
    }

    return (
        <>
            <Paper withBorder p="var(--card-pad)">
                <Stack gap="sm">
                    <Group className="idt-section-head" justify="space-between" align="center">
                        <Title order={2} className="idt-title-plain">Texte</Title>
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
            </Paper>

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
