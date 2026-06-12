import { type FormEvent, useEffect, useState } from "react";
import {
    Alert,
    Button,
    ColorInput,
    Group,
    Modal,
    Stack,
    Switch,
    Textarea,
    TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
    useCreateProjectGroup,
    useUpdateProjectGroup,
    type ProjectGroup,
} from "../../shared/api/queries";

type Props = {
    opened: boolean;
    onClose: () => void;
    /** Existing group to edit, or null to create a new one. */
    group: ProjectGroup | null;
};

const DEFAULT_COLOR = "#FF0000";

type FormState = {
    name: string;
    short_name: string;
    description: string;
    color: string;
    public: boolean;
    plot_only_superior_projects: boolean;
    is_visible: boolean;
    is_default_selected: boolean;
};

function initialState(group: ProjectGroup | null): FormState {
    return {
        name: group?.name ?? "",
        short_name: group?.short_name ?? "",
        description: group?.description ?? "",
        color: group?.color ?? DEFAULT_COLOR,
        public: group?.public ?? false,
        plot_only_superior_projects: group?.plot_only_superior_projects ?? true,
        is_visible: group?.is_visible ?? true,
        is_default_selected: group?.is_default_selected ?? false,
    };
}

export function ProjectGroupFormModal({ opened, onClose, group }: Props) {
    const isEdit = group !== null;
    const [form, setForm] = useState<FormState>(() => initialState(group));
    const [error, setError] = useState<string | null>(null);

    const createGroup = useCreateProjectGroup();
    const updateGroup = useUpdateProjectGroup();

    // Re-seed the form whenever a different group (or create mode) is opened.
    useEffect(() => {
        if (opened) {
            setForm(initialState(group));
            setError(null);
        }
    }, [opened, group]);

    const set = <K extends keyof FormState,>(key: K, value: FormState[K]) =>
        setForm((prev) => ({ ...prev, [key]: value }));

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!form.name.trim() || !form.short_name.trim()) {
            setError("Name und Kürzel sind Pflichtfelder.");
            return;
        }

        const payload = {
            name: form.name.trim(),
            short_name: form.short_name.trim(),
            description: form.description.trim() || null,
            color: form.color,
            public: form.public,
            plot_only_superior_projects: form.plot_only_superior_projects,
            is_visible: form.is_visible,
            is_default_selected: form.is_default_selected,
        };

        try {
            if (isEdit) {
                await updateGroup.mutateAsync({ groupId: group.id!, ...payload });
                notifications.show({
                    color: "green",
                    title: "Gruppe gespeichert",
                    message: `Die Projektgruppe „${payload.name}" wurde aktualisiert.`,
                });
            } else {
                await createGroup.mutateAsync(payload);
                notifications.show({
                    color: "green",
                    title: "Gruppe angelegt",
                    message: `Die Projektgruppe „${payload.name}" wurde erstellt.`,
                });
            }
            onClose();
        } catch (err) {
            const status = (err as { status?: number }).status;
            if (status === 409) {
                setError("Kürzel bereits vergeben. Bitte ein anderes Kürzel wählen.");
            } else {
                setError("Die Gruppe konnte nicht gespeichert werden.");
            }
        }
    };

    const isPending = createGroup.isPending || updateGroup.isPending;

    return (
        <Modal
            opened={opened}
            onClose={onClose}
            title={isEdit ? "Projektgruppe bearbeiten" : "Neue Projektgruppe anlegen"}
            size="md"
        >
            <form onSubmit={handleSubmit}>
                <Stack gap="sm">
                    {error && (
                        <Alert color="red" variant="light">
                            {error}
                        </Alert>
                    )}
                    <TextInput
                        label="Name"
                        value={form.name}
                        onChange={(e) => set("name", e.target.value)}
                        maxLength={100}
                        required
                    />
                    <TextInput
                        label="Kürzel"
                        description="Eindeutiges Kürzel, max. 20 Zeichen (z. B. NBS)."
                        value={form.short_name}
                        onChange={(e) => set("short_name", e.target.value)}
                        maxLength={20}
                        required
                    />
                    <Textarea
                        label="Beschreibung"
                        value={form.description}
                        onChange={(e) => set("description", e.target.value)}
                        autosize
                        minRows={2}
                    />
                    <ColorInput
                        label="Farbe"
                        value={form.color}
                        onChange={(value) => set("color", value)}
                        format="hex"
                    />
                    <Switch
                        label="Öffentlich sichtbar"
                        description="Gruppe ist auch für nicht angemeldete Nutzer sichtbar."
                        checked={form.public}
                        onChange={(e) => set("public", e.currentTarget.checked)}
                    />
                    <Switch
                        label="Nur übergeordnete Projekte anzeigen"
                        description="Blendet untergeordnete Projekte in der Kartenansicht aus."
                        checked={form.plot_only_superior_projects}
                        onChange={(e) => set("plot_only_superior_projects", e.currentTarget.checked)}
                    />
                    <Switch
                        label="Auf der Karte anzeigen"
                        checked={form.is_visible}
                        onChange={(e) => set("is_visible", e.currentTarget.checked)}
                    />
                    <Switch
                        label="Standardmäßig vorausgewählt"
                        checked={form.is_default_selected}
                        onChange={(e) => set("is_default_selected", e.currentTarget.checked)}
                    />
                    <Group justify="flex-end" mt="sm">
                        <Button variant="default" onClick={onClose} disabled={isPending}>
                            Abbrechen
                        </Button>
                        <Button type="submit" loading={isPending}>
                            {isEdit ? "Speichern" : "Anlegen"}
                        </Button>
                    </Group>
                </Stack>
            </form>
        </Modal>
    );
}
