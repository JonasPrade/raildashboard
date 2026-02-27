import { useEffect, useState } from "react";
import {
    ActionIcon,
    Alert,
    Anchor,
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
import { notifications } from "@mantine/notifications";

import {
    type ProjectText,
    type ProjectTextCreate,
    type ProjectTextUpdate,
    useCreateProjectText,
    useCreateTextType,
    useDeleteProjectText,
    useProjectTexts,
    useTextTypes,
    useUpdateProjectText,
} from "../../shared/api/queries";

// ── Create text type modal ────────────────────────────────────────────────────

type CreateTextTypeModalProps = {
    opened: boolean;
    onClose: () => void;
    onCreated: (newTypeId: string) => void;
};

function CreateTextTypeModal({ opened, onClose, onCreated }: CreateTextTypeModalProps) {
    const [name, setName] = useState("");
    const createTypeMutation = useCreateTextType();

    useEffect(() => {
        if (opened) setName("");
    }, [opened]);

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
                    onChange={(event) => {
                        const value = event.currentTarget.value;
                        setName(value);
                    }}
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
    onSubmit: (values: TextFormValues) => void;
    isSubmitting: boolean;
    initialValues: TextFormValues;
    title: string;
};

function TextFormModal({ opened, onClose, onSubmit, isSubmitting, initialValues, title }: TextFormModalProps) {
    const [values, setValues] = useState<TextFormValues>(initialValues);
    const [createTypeOpened, setCreateTypeOpened] = useState(false);
    const { data: textTypes } = useTextTypes();

    // Reset form whenever the modal opens
    useEffect(() => {
        if (opened) {
            setValues(initialValues);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [opened]);

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
                        onChange={(event) => {
                            const value = event.currentTarget.value;
                            setValues((prev) => ({ ...prev, header: value }));
                        }}
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
                        onChange={(event) => {
                            const value = event.currentTarget.value;
                            setValues((prev) => ({ ...prev, text: value }));
                        }}
                    />

                    <TextInput
                        label="Weblink"
                        placeholder="https://…"
                        value={values.weblink}
                        onChange={(event) => {
                            const value = event.currentTarget.value;
                            setValues((prev) => ({ ...prev, weblink: value }));
                        }}
                    />

                    <TextInput
                        label="Logo-URL"
                        placeholder="https://…"
                        value={values.logo_url}
                        onChange={(event) => {
                            const value = event.currentTarget.value;
                            setValues((prev) => ({ ...prev, logo_url: value }));
                        }}
                    />

                    <Group justify="flex-end">
                        <Button variant="default" onClick={onClose} disabled={isSubmitting}>
                            Abbrechen
                        </Button>
                        <Button
                            onClick={() => onSubmit(values)}
                            loading={isSubmitting}
                            disabled={!isValid}
                        >
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

    function handleEdit(values: TextFormValues) {
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

    function handleCreate(values: TextFormValues) {
        if (!values.type) return;
        const payload: ProjectTextCreate = {
            header: values.header.trim(),
            text: values.text.trim() || null,
            weblink: values.weblink.trim() || null,
            logo_url: values.logo_url.trim() || null,
            type: Number(values.type),
        };
        createMutation.mutate(payload, {
            onSuccess: () => {
                setCreateOpened(false);
                notifications.show({
                    color: "green",
                    title: "Text erstellt",
                    message: "Der neue Text wurde gespeichert.",
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
            />
        </>
    );
}
