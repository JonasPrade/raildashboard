import { Alert, Button, Group, MultiSelect, Stack, Text } from "@mantine/core";
import { useMemo, useState } from "react";

import { useConfirmedVibEntries, useUpdateVibEntry } from "../../../shared/api/queries";

type Props = {
    projectId: number;
    onDone: () => void;
};

export default function Step5Vib({ projectId, onDone }: Props) {
    const { data: entries = [] } = useConfirmedVibEntries();
    const updateVib = useUpdateVibEntry();
    const [selected, setSelected] = useState<string[]>([]);
    const [saving, setSaving] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const options = useMemo(
        () =>
            entries.map((e) => ({
                value: String(e.id),
                label: `[${e.report_year}] ${e.vib_name_raw ?? "(ohne Name)"}`,
            })),
        [entries],
    );

    const handleSave = async () => {
        if (selected.length === 0) {
            onDone();
            return;
        }
        setSaving(true);
        setErrorMessage(null);
        try {
            await Promise.all(
                selected.map((idStr) => {
                    const id = Number(idStr);
                    const entry = entries.find((e) => e.id === id);
                    if (!entry) return Promise.resolve();
                    const nextProjectIds = Array.from(new Set([...entry.project_ids, projectId]));
                    return updateVib.mutateAsync({
                        entryId: id,
                        data: { project_ids: nextProjectIds },
                    });
                }),
            );
            onDone();
        } catch (err) {
            setErrorMessage((err as Error)?.message ?? "Unbekannter Fehler");
        } finally {
            setSaving(false);
        }
    };

    return (
        <Stack gap="md">
            <Text c="dimmed" size="sm">
                Ordne diesem neuen Projekt bestehende VIB-Einträge zu.
            </Text>
            <MultiSelect
                label="VIB-Einträge"
                data={options}
                value={selected}
                onChange={setSelected}
                searchable
                clearable
                hidePickedOptions
                placeholder="VIB-Einträge suchen…"
            />
            {errorMessage && (
                <Alert color="red" variant="light" title="Verknüpfen fehlgeschlagen">
                    {errorMessage}
                </Alert>
            )}
            <Group justify="flex-end">
                <Button variant="subtle" onClick={onDone} disabled={saving}>
                    Überspringen
                </Button>
                <Button onClick={handleSave} loading={saving} disabled={selected.length === 0}>
                    Verknüpfen & Fertig
                </Button>
            </Group>
        </Stack>
    );
}
