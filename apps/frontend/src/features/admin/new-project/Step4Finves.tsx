import { Alert, Button, Group, MultiSelect, Stack, Text } from "@mantine/core";
import { useMemo, useState } from "react";

import { useFinves, useLinkFinvesToProject } from "../../../shared/api/queries";

type Props = {
    projectId: number;
    onDone: () => void;
};

export default function Step4Finves({ projectId, onDone }: Props) {
    const { data: finves = [] } = useFinves();
    const linkFinves = useLinkFinvesToProject(projectId);
    const [selected, setSelected] = useState<string[]>([]);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const options = useMemo(
        () =>
            finves.map((f) => {
                const label = f.name ?? `FinVe ${f.id}`;
                const year = f.starting_year != null ? ` · ${f.starting_year}` : "";
                return { value: String(f.id), label: `${label}${year}` };
            }),
        [finves],
    );

    const handleSave = async () => {
        if (selected.length === 0) {
            onDone();
            return;
        }
        setErrorMessage(null);
        try {
            await linkFinves.mutateAsync(selected.map(Number));
            onDone();
        } catch (err) {
            setErrorMessage((err as Error)?.message ?? "Unbekannter Fehler");
        }
    };

    return (
        <Stack gap="md">
            <Text c="dimmed" size="sm">
                Wähle bestehende FinVes aus, die diesem Projekt zugeordnet werden sollen.
            </Text>
            <MultiSelect
                label="FinVes"
                data={options}
                value={selected}
                onChange={setSelected}
                searchable
                clearable
                hidePickedOptions
                placeholder="FinVes suchen…"
            />
            {errorMessage && (
                <Alert color="red" variant="light" title="Verknüpfen fehlgeschlagen">
                    {errorMessage}
                </Alert>
            )}
            <Group justify="flex-end">
                <Button variant="subtle" onClick={onDone} disabled={linkFinves.isPending}>
                    Überspringen
                </Button>
                <Button onClick={handleSave} loading={linkFinves.isPending} disabled={selected.length === 0}>
                    Verknüpfen & Weiter
                </Button>
            </Group>
        </Stack>
    );
}
