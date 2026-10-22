import { type FormEvent, useEffect, useState } from "react";
import {
    Alert,
    Button,
    ColorInput,
    Modal,
    MultiSelect,
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
import {
    MAIN_PHASE_LABEL,
    SKIPPABLE_PHASES,
} from "../projects/components/progress/phaseMeta";
import { GROUP_COLOR_SWATCHES, MAP_COLOR } from "../../shared/theme/semanticColors";

type SkippablePhase = NonNullable<ProjectGroup["skipped_phases"]>[number];

const SKIPPABLE_PHASE_OPTIONS = SKIPPABLE_PHASES.map((p) => ({ value: p, label: MAIN_PHASE_LABEL[p] }));

type Props = {
    opened: boolean;
    onClose: () => void;
    /** Existing group to edit, or null to create a new one. */
    group: ProjectGroup | null;
};

// Q12: the colour stays free; new groups start in the map default (violet).
const DEFAULT_COLOR: string = MAP_COLOR.default;

type FormState = {
    name: string;
    short_name: string;
    description: string;
    color: string;
    public: boolean;
    plot_only_superior_projects: boolean;
    is_visible: boolean;
    is_default_selected: boolean;
    skipped_phases: SkippablePhase[];
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
        skipped_phases: group?.skipped_phases ?? [],
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
            skipped_phases: form.skipped_phases,
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
                        swatches={[...GROUP_COLOR_SWATCHES]}
                        swatchesPerRow={6}
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
                    <MultiSelect
                        label="Übersprungene Planungsphasen"
                        description="Für Projekte dieser Gruppe ausblenden – etwa bei Sanierungen ohne Planfeststellung. Gilt nur, wenn alle Gruppen eines Projekts die Phase überspringen; liegen Daten zu der Phase vor, bleibt sie sichtbar."
                        placeholder={form.skipped_phases.length ? undefined : "Keine"}
                        data={SKIPPABLE_PHASE_OPTIONS}
                        value={form.skipped_phases}
                        onChange={(value) =>
                            set(
                                "skipped_phases",
                                SKIPPABLE_PHASES.filter((p) => value.includes(p)) as SkippablePhase[],
                            )
                        }
                        clearable
                    />
                    <div className="idt-modal-footer">
                        <Button variant="default" onClick={onClose} disabled={isPending}>
                            Abbrechen
                        </Button>
                        <Button type="submit" loading={isPending}>
                            {isEdit ? "Speichern" : "Anlegen"}
                        </Button>
                    </div>
                </Stack>
            </form>
        </Modal>
    );
}
