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

function toProposed(entry: VibEntrySchema): VibEntryProposed {
    return {
        vib_section: entry.vib_section,
        vib_lfd_nr: entry.vib_lfd_nr,
        vib_name_raw: entry.vib_name_raw,
        category: entry.category as VibEntryProposed["category"],
        verkehrliche_zielsetzung: entry.verkehrliche_zielsetzung,
        durchgefuehrte_massnahmen: entry.durchgefuehrte_massnahmen,
        noch_umzusetzende_massnahmen: entry.noch_umzusetzende_massnahmen,
        bauaktivitaeten: entry.bauaktivitaeten,
        teilinbetriebnahmen: entry.teilinbetriebnahmen,
        raw_text: entry.raw_text,
        strecklaenge_km: entry.strecklaenge_km,
        gesamtkosten_mio_eur: entry.gesamtkosten_mio_eur,
        entwurfsgeschwindigkeit: entry.entwurfsgeschwindigkeit,
        planungsstand: entry.planungsstand,
        pfa_entries: entry.pfa_entries.map(({ abschnitt_label, nr_pfa, oertlichkeit, entwurfsplanung, abschluss_finve, datum_pfb, baubeginn, inbetriebnahme }) => ({
            abschnitt_label,
            nr_pfa,
            oertlichkeit,
            entwurfsplanung,
            abschluss_finve,
            datum_pfb,
            baubeginn,
            inbetriebnahme,
        })),
        pfa_raw_markdown: null,
        sonstiges: entry.sonstiges,
        project_ids: entry.project_ids,
        suggested_project_ids: [],
        status_planung: entry.status_planung,
        status_bau: entry.status_bau,
        status_abgeschlossen: entry.status_abgeschlossen,
        ai_extracted: entry.ai_extracted,
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
