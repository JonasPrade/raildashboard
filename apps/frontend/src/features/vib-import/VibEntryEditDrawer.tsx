import { useState } from "react";
import { Button, Drawer, Group, ScrollArea, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
    useUpdateVibEntry,
    useProjects,
    type VibEntrySchema,
    type VibEntryProposed,
} from "../../shared/api/queries";
import VibEntryEditForm from "./VibEntryEditForm";

type Props = {
    entry: VibEntrySchema | null;
    opened: boolean;
    onClose: () => void;
};

// VibEntrySchema and VibEntryProposed share the same generated field set
// (VibEntryFieldsBase); only the id/report keys are stripped and the
// proposed-only bookkeeping fields defaulted.
function toProposed(entry: VibEntrySchema): VibEntryProposed {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { id: _id, vib_report_id: _reportId, report_year: _year, pfa_entries, ...fields } = entry;
    return {
        ...fields,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        pfa_entries: pfa_entries.map(({ id: _pfaId, ...pfa }) => pfa),
        pfa_raw_markdown: null,
        suggested_project_ids: [],
        ai_extraction_failed: false,
        ai_extraction_error: null,
    };
}

export default function VibEntryEditDrawer({ entry, opened, onClose }: Props) {
    const { data: projects } = useProjects();
    const updateEntry = useUpdateVibEntry();

    const [draft, setDraft] = useState<VibEntryProposed | null>(null);

    // Reset draft whenever a new entry is opened
    const activeDraft = draft ?? (entry ? toProposed(entry) : null);

    const projectOptions = (projects ?? []).map((p) => ({
        value: String(p.id),
        label: `${p.project_number ?? "–"} ${p.name}`,
    }));

    function handleChange(patch: Partial<VibEntryProposed>) {
        setDraft((prev) => ({ ...(prev ?? toProposed(entry!)), ...patch }));
    }

    async function handleSave() {
        if (!entry || !activeDraft) return;
        try {
            await updateEntry.mutateAsync({ entryId: entry.id, data: activeDraft });
            notifications.show({ color: "green", message: "Eintrag gespeichert." });
            setDraft(null);
            onClose();
        } catch {
            notifications.show({ color: "red", message: "Speichern fehlgeschlagen." });
        }
    }

    function handleClose() {
        setDraft(null);
        onClose();
    }

    return (
        <Drawer
            opened={opened}
            onClose={handleClose}
            title={
                <Stack gap={2}>
                    <Text fw={600} size="sm">VIB-Eintrag bearbeiten</Text>
                    {entry && (
                        <Text size="xs" c="dimmed">
                            {entry.report_year}
                            {entry.vib_section ? ` · ${entry.vib_section}` : ""}
                        </Text>
                    )}
                </Stack>
            }
            position="right"
            size="xl"
            scrollAreaComponent={ScrollArea.Autosize}
        >
            {activeDraft && (
                <Stack gap="md">
                    <VibEntryEditForm
                        entry={activeDraft}
                        projectOptions={projectOptions}
                        onChange={handleChange}
                    />
                    <Group justify="flex-end" gap="sm">
                        <Button variant="default" onClick={handleClose}>
                            Abbrechen
                        </Button>
                        <Button onClick={handleSave} loading={updateEntry.isPending}>
                            Speichern
                        </Button>
                    </Group>
                </Stack>
            )}
        </Drawer>
    );
}
