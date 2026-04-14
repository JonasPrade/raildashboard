import { useState } from "react";
import {
    Box,
    Button,
    Checkbox,
    Group,
    MultiSelect,
    NumberInput,
    Stack,
    Table,
    Text,
    Textarea,
    TextInput,
    Tooltip,
} from "@mantine/core";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChronicleCard, ChronicleDataChip } from "../../components/chronicle";
import { filterProjectOption } from "../../lib/filterProjectOption";
import type { VibEntryProposed } from "../../shared/api/queries";

type Props = {
    entry: VibEntryProposed;
    projectOptions: { value: string; label: string }[];
    onChange: (patch: Partial<VibEntryProposed>) => void;
    onRetryAi?: () => void;
    isRetryingAi?: boolean;
};

export default function VibEntryEditForm({
    entry,
    projectOptions,
    onChange,
    onRetryAi,
    isRetryingAi,
}: Props) {
    const [showRawPfa, setShowRawPfa] = useState(false);

    const hasSuggestion =
        entry.project_ids.length > 0 ||
        (entry.suggested_project_ids && entry.suggested_project_ids.length > 0);
    const confidence =
        entry.project_ids.length > 0 &&
        entry.suggested_project_ids.some((id) => entry.project_ids.includes(id))
            ? "high"
            : entry.project_ids.length > 0
              ? "manual"
              : "none";

    function handlePfaChange(pfaIdx: number, field: string, value: string) {
        const newPfa = entry.pfa_entries.map((p, pi) =>
            pi === pfaIdx ? { ...p, [field]: value || null } : p
        );
        onChange({ pfa_entries: newPfa });
    }

    function handlePfaAdd() {
        onChange({
            pfa_entries: [
                ...entry.pfa_entries,
                {
                    nr_pfa: null,
                    oertlichkeit: null,
                    entwurfsplanung: null,
                    abschluss_finve: null,
                    datum_pfb: null,
                    baubeginn: null,
                    inbetriebnahme: null,
                    abschnitt_label: null,
                },
            ],
        });
    }

    function handlePfaRemove(pfaIdx: number) {
        onChange({ pfa_entries: entry.pfa_entries.filter((_, pi) => pi !== pfaIdx) });
    }

    return (
        <ChronicleCard>
            <Stack gap="md">
                {/* Section label + AI status badges */}
                <Group gap="xs" align="center">
                    {entry.vib_section && (
                        <Text size="xs" c="dimmed" ff="monospace">
                            {entry.vib_section}
                        </Text>
                    )}
                    {entry.ai_extracted && (
                        <ChronicleDataChip>KI</ChronicleDataChip>
                    )}
                    {entry.ai_extraction_failed && (
                        <Tooltip label={entry.ai_extraction_error ?? "KI-Extraktion fehlgeschlagen"} withArrow>
                            <ChronicleDataChip>KI fehlgeschlagen</ChronicleDataChip>
                        </Tooltip>
                    )}
                    {onRetryAi && (
                        <Button
                            size="xs"
                            variant="light"
                            color={entry.ai_extraction_failed ? "orange" : "violet"}
                            loading={isRetryingAi}
                            onClick={onRetryAi}
                        >
                            {entry.ai_extracted || entry.ai_extraction_failed
                                ? "KI wiederholen"
                                : "KI extrahieren"}
                        </Button>
                    )}
                </Group>

                {/* Überschrift */}
                <TextInput
                    label="Überschrift"
                    size="sm"
                    value={entry.vib_name_raw}
                    onChange={(e) => onChange({ vib_name_raw: e.currentTarget.value })}
                />

                {/* Projektkenndaten */}
                <Group gap="md" align="flex-end">
                    <NumberInput
                        label="Länge (km)"
                        size="sm"
                        value={entry.strecklaenge_km ?? ""}
                        onChange={(v) => onChange({ strecklaenge_km: v === "" ? null : Number(v) })}
                        decimalSeparator=","
                        w={120}
                    />
                    <NumberInput
                        label="Gesamtkosten (Mio. €)"
                        size="sm"
                        value={entry.gesamtkosten_mio_eur ?? ""}
                        onChange={(v) => onChange({ gesamtkosten_mio_eur: v === "" ? null : Number(v) })}
                        decimalSeparator=","
                        w={160}
                    />
                    <TextInput
                        label="Vmax (km/h)"
                        size="sm"
                        value={entry.entwurfsgeschwindigkeit ?? ""}
                        onChange={(e) => onChange({ entwurfsgeschwindigkeit: e.currentTarget.value || null })}
                        w={100}
                    />
                </Group>

                {/* Project mapping */}
                <Group gap="sm" align="flex-end" wrap="wrap">
                    <MultiSelect
                        label="Projekte zuordnen"
                        size="sm"
                        clearable
                        searchable
                        filter={filterProjectOption}
                        placeholder="Projekte zuordnen…"
                        data={projectOptions}
                        value={entry.project_ids.map(String)}
                        onChange={(vs) => onChange({ project_ids: vs.map(Number) })}
                        style={{ flex: 1, minWidth: 200 }}
                    />
                    {hasSuggestion && (
                        <Tooltip label={`KI-Vorschlag: ${entry.suggested_project_ids.map(id => projectOptions.find(o => o.value === String(id))?.label ?? String(id)).join(", ")}`}>
                            <ChronicleDataChip style={{ cursor: "default", marginBottom: 6 }}>
                                {confidence === "high" ? "✓" : confidence === "manual" ? "~" : "?"}
                            </ChronicleDataChip>
                        </Tooltip>
                    )}
                </Group>

                {/* Projektstatus */}
                <Group gap="lg">
                    <Text size="sm" fw={500} style={{ minWidth: 100 }}>Projektstatus</Text>
                    <Checkbox
                        label="Planung"
                        checked={entry.status_planung}
                        onChange={(e) => onChange({ status_planung: e.currentTarget.checked })}
                    />
                    <Checkbox
                        label="Bau"
                        checked={entry.status_bau}
                        onChange={(e) => onChange({ status_bau: e.currentTarget.checked })}
                    />
                    <Checkbox
                        label="Abgeschlossen"
                        checked={entry.status_abgeschlossen}
                        onChange={(e) => onChange({ status_abgeschlossen: e.currentTarget.checked })}
                    />
                </Group>

                {/* Bauaktivitäten */}
                <Textarea
                    label="Bauaktivitäten"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.bauaktivitaeten ?? ""}
                    onChange={(e) => onChange({ bauaktivitaeten: e.currentTarget.value || null })}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

                {/* Teilinbetriebnahmen */}
                <Textarea
                    label="Teilinbetriebnahmen"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.teilinbetriebnahmen ?? ""}
                    onChange={(e) => onChange({ teilinbetriebnahmen: e.currentTarget.value || null })}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

                {/* Verkehrliche Zielsetzung */}
                <Textarea
                    label="Verkehrliche Zielsetzung"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.verkehrliche_zielsetzung ?? ""}
                    onChange={(e) => onChange({ verkehrliche_zielsetzung: e.currentTarget.value || null })}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

                {/* Durchgeführte Maßnahmen */}
                <Textarea
                    label="Durchgeführte Maßnahmen"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.durchgefuehrte_massnahmen ?? ""}
                    onChange={(e) => onChange({ durchgefuehrte_massnahmen: e.currentTarget.value || null })}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

                {/* Noch umzusetzende Maßnahmen */}
                <Textarea
                    label="Noch umzusetzende Maßnahmen"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.noch_umzusetzende_massnahmen ?? ""}
                    onChange={(e) => onChange({ noch_umzusetzende_massnahmen: e.currentTarget.value || null })}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

                {/* PFA-Tabelle */}
                <div>
                    <Group justify="space-between" mb={6}>
                        <Text size="sm" fw={600}>
                            PFA-Tabelle ({entry.pfa_entries.length} Einträge)
                        </Text>
                        <Button size="xs" variant="light" onClick={handlePfaAdd}>
                            + Zeile
                        </Button>
                    </Group>
                    {entry.pfa_entries.length > 0 ? (
                        <ChronicleCard style={{ overflow: "auto", padding: 0 }}>
                            <Table withTableBorder withColumnBorders fz="xs" style={{ fontSize: 11 }}>
                                <Table.Thead>
                                    <Table.Tr>
                                        <Table.Th>Nr.</Table.Th>
                                        <Table.Th>Örtlichkeit</Table.Th>
                                        <Table.Th>Entwurfspl.</Table.Th>
                                        <Table.Th>Abschluss FinVe</Table.Th>
                                        <Table.Th>PFB</Table.Th>
                                        <Table.Th>Baubeginn</Table.Th>
                                        <Table.Th>IBM</Table.Th>
                                        <Table.Th />
                                    </Table.Tr>
                                </Table.Thead>
                                <Table.Tbody>
                                    {entry.pfa_entries.map((pfa, pi) => (
                                        <Table.Tr key={pi}>
                                            {(["nr_pfa", "oertlichkeit", "entwurfsplanung", "abschluss_finve", "datum_pfb", "baubeginn", "inbetriebnahme"] as const).map((field) => (
                                                <Table.Td key={field}>
                                                    <input
                                                        style={{
                                                            width: field === "oertlichkeit" ? 140 : 80,
                                                            border: "none",
                                                            background: "transparent",
                                                            fontSize: 11,
                                                            fontFamily: "inherit",
                                                        }}
                                                        value={(pfa as Record<string, string | null>)[field] ?? ""}
                                                        onChange={(e) => handlePfaChange(pi, field, e.currentTarget.value)}
                                                    />
                                                </Table.Td>
                                            ))}
                                            <Table.Td>
                                                <button
                                                    style={{ cursor: "pointer", background: "none", border: "none", color: "red" }}
                                                    onClick={() => handlePfaRemove(pi)}
                                                    title="Zeile löschen"
                                                >×</button>
                                            </Table.Td>
                                        </Table.Tr>
                                    ))}
                                </Table.Tbody>
                            </Table>
                        </ChronicleCard>
                    ) : (
                        <Text size="xs" c="dimmed">Keine PFA-Einträge.</Text>
                    )}
                </div>

                {/* PFA raw-markdown toggle */}
                {entry.pfa_raw_markdown && (
                    <div>
                        <Button
                            size="xs"
                            variant="subtle"
                            onClick={() => setShowRawPfa((v) => !v)}
                            mb={4}
                        >
                            {showRawPfa ? "Roh-Markdown ausblenden" : "PFA Roh-Markdown anzeigen"}
                        </Button>
                        {showRawPfa && (
                            <Box
                                p="xs"
                                style={{
                                    fontSize: 12,
                                    fontFamily: "var(--mantine-font-family-monospace)",
                                    background: "var(--mantine-color-gray-0)",
                                    borderRadius: 4,
                                    overflowX: "auto",
                                }}
                                className="vib-raw-markdown"
                            >
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {entry.pfa_raw_markdown}
                                </ReactMarkdown>
                            </Box>
                        )}
                    </div>
                )}

                {/* Sonstiges */}
                <Textarea
                    label="Sonstiger Text (nicht zugeordnet)"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.sonstiges ?? ""}
                    onChange={(e) => onChange({ sonstiges: e.currentTarget.value || null })}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

                {/* Volltext */}
                {entry.raw_text !== null && entry.raw_text !== undefined && (
                    <Textarea
                        label="Volltext"
                        autosize
                        minRows={6}
                        maxRows={24}
                        value={entry.raw_text}
                        onChange={(e) => onChange({ raw_text: e.currentTarget.value })}
                        styles={{
                            input: {
                                fontFamily: "monospace",
                                fontSize: 12,
                                lineHeight: 1.6,
                            },
                        }}
                    />
                )}
            </Stack>
        </ChronicleCard>
    );
}
