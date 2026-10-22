import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import {
    Alert,
    Badge,
    Box,
    Button,
    Container,
    Group,
    Paper,
    ScrollArea,
    Stack,
    Table,
    Text,
    Title,
    Tooltip,
} from "@mantine/core";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import RequirePermission from "../../components/RequirePermission";
import {
    useVibParseResult,
    type VibEntryProposed,
} from "../../shared/api/queries";
import { LoadingState } from "../../shared/ui/LoadingState";

// Sub-sections we look for in raw_text
const SUBSECTIONS: { key: string; label: string; pattern: RegExp }[] = [
    { key: "vz", label: "Verk. Zielsetzung", pattern: /Verkehrliche\s+Zielsetzung/i },
    { key: "dm", label: "Durchgef. Maßnahmen", pattern: /Durchgef[üu]hrte/i },
    { key: "nm", label: "Noch umzusetzende", pattern: /Noch\s+umzusetzende/i },
    { key: "ba", label: "Bauaktivitäten", pattern: /Bauaktivit[äa]ten/i },
    { key: "ti", label: "Teilinbetriebnahmen", pattern: /Teilinbetriebnahmen/i },
    { key: "pk", label: "Projektkenndaten", pattern: /Projektkenndaten/i },
];

function RawTextCell({
    entry,
    expanded,
    onToggle,
}: {
    entry: VibEntryProposed;
    expanded: boolean;
    onToggle: () => void;
}) {
    const raw = entry.raw_text ?? "";
    const len = raw.length;

    const detected = SUBSECTIONS.filter((s) => s.pattern.test(raw));
    const missing = SUBSECTIONS.filter((s) => !s.pattern.test(raw));

    return (
        <Stack gap={4} style={{ cursor: "pointer" }} onClick={onToggle}>
            <Group gap={6} wrap="nowrap">
                <Tooltip label={`${len} Zeichen`} withArrow>
                    <Badge variant="outline" color="var(--text-strong)" tt="none">
                        {len > 0 ? `${(len / 1000).toFixed(1)}k` : "leer"}
                    </Badge>
                </Tooltip>
                {entry.pfa_entries.length > 0 ? (
                    <Badge variant="outline" color="var(--text-strong)" tt="none">
                        {entry.pfa_entries.length} PFA
                    </Badge>
                ) : (
                    <Badge variant="outline" color="var(--text-strong)" tt="none">
                        0 PFA
                    </Badge>
                )}
            </Group>
            <Group gap={4} wrap="wrap">
                {detected.map((s) => (
                    <Badge variant="outline" color="var(--text-strong)" tt="none" key={s.key}>
                        {s.label}
                    </Badge>
                ))}
                {missing.map((s) => (
                    <Badge variant="outline" color="var(--text-strong)" tt="none" key={s.key}>
                        {s.label}
                    </Badge>
                ))}
            </Group>
            <Text size="xs" c="blue" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                {expanded ? <ChevronUp size={16} aria-hidden /> : <ChevronDown size={16} aria-hidden />}
                {expanded ? "einklappen" : "Rohtext anzeigen"}
            </Text>
        </Stack>
    );
}

function ExpandedRawText({ entry }: { entry: VibEntryProposed }) {
    const raw = entry.raw_text ?? "";
    const detected = SUBSECTIONS.filter((s) => s.pattern.test(raw));
    const missing = SUBSECTIONS.filter((s) => !s.pattern.test(raw));

    return (
        <Box p="md" style={{ background: "var(--surface-alt)", borderTop: "1px solid var(--border)" }}>
            <Stack gap="xs">
                <Group gap="xl">
                    <div>
                        <Text size="xs" c="dimmed">Zeichen</Text>
                        <Text fw={600} size="sm">{raw.length.toLocaleString("de-DE")}</Text>
                    </div>
                    <div>
                        <Text size="xs" c="dimmed">PFA-Zeilen</Text>
                        <Text fw={entry.pfa_entries.length === 0 ? 700 : 600} size="sm">
                            {entry.pfa_entries.length}
                        </Text>
                    </div>
                    {entry.strecklaenge_km != null && (
                        <div>
                            <Text size="xs" c="dimmed">Streckenlänge</Text>
                            <Text fw={600} size="sm">{entry.strecklaenge_km} km</Text>
                        </div>
                    )}
                    {entry.gesamtkosten_mio_eur != null && (
                        <div>
                            <Text size="xs" c="dimmed">Gesamtkosten</Text>
                            <Text fw={600} size="sm">{entry.gesamtkosten_mio_eur} Mio. €</Text>
                        </div>
                    )}
                </Group>

                <Group gap={6}>
                    <Text size="xs" c="dimmed">Erkannt:</Text>
                    {detected.length > 0
                        ? detected.map((s) => (
                              <Badge variant="outline" color="var(--text-strong)" tt="none" key={s.key}>
                                  ✓ {s.label}
                              </Badge>
                          ))
                        : <Text size="xs" c="dimmed">–</Text>}
                </Group>
                {missing.length > 0 && (
                    <Group gap={6}>
                        <Text size="xs" c="dimmed">Nicht gefunden:</Text>
                        {missing.map((s) => (
                            <Badge variant="outline" color="var(--text-strong)" tt="none" key={s.key}>
                                ✗ {s.label}
                            </Badge>
                        ))}
                    </Group>
                )}

                <Box>
                    <Text size="xs" c="dimmed" mb={4}>Rohtext</Text>
                    <ScrollArea h={340} type="auto">
                        <Box
                            p="xs"
                            style={{
                                fontSize: 12,
                                lineHeight: 1.5,
                                fontVariantNumeric: "tabular-nums",
                                background: "var(--surface-alt)",
                            }}
                            className="vib-raw-markdown"
                        >
                            {raw
                                ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{raw}</ReactMarkdown>
                                : <Text size="xs" c="dimmed">– kein Rohtext –</Text>
                            }
                        </Box>
                    </ScrollArea>
                </Box>
            </Stack>
        </Box>
    );
}

function VibStructurePreviewPageContent() {
    const { taskId } = useParams<{ taskId: string }>();
    const navigate = useNavigate();

    const { data: parseResult, isLoading, isError } = useVibParseResult(taskId ?? null);
    const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

    const toggleRow = (idx: number) =>
        setExpandedRows((prev) => {
            const next = new Set(prev);
            if (next.has(idx)) next.delete(idx);
            else next.add(idx);
            return next;
        });

    if (isLoading) {
        return (
            <Container py="xl">
                <LoadingState rows={6} />
            </Container>
        );
    }

    if (isError || !parseResult) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Fehler">
                    Parse-Ergebnis konnte nicht geladen werden.
                </Alert>
            </Container>
        );
    }

    const entries = parseResult.entries;
    const withoutPfa = entries.filter((e) => e.pfa_entries.length === 0);

    return (
        <Container size="lg" py="xl">
            <Stack gap="xl">
                <div>
                    <Title order={1}>VIB-Import — Strukturvorschau</Title>
                    <Text c="dimmed" size="sm" mt={4}>
                        Struktur erkannt. Prüfen Sie die Vorhaben und wechseln Sie zum Review.
                        KI-Extraktion ist pro Vorhaben im Review verfügbar.
                    </Text>
                </div>

                <Paper withBorder p="var(--card-pad)">
                    <Group gap="xl">
                        <div>
                            <Text size="xs" c="dimmed">Projekte erkannt</Text>
                            <Text fw={700} size="xl">{entries.length}</Text>
                        </div>
                        <div>
                            <Text size="xs" c="dimmed">Berichtsjahr</Text>
                            <Text fw={700} size="xl">{parseResult.year}</Text>
                        </div>
                        <div>
                            <Text size="xs" c="dimmed">Drucksache</Text>
                            <Text fw={700} size="xl">{parseResult.drucksache_nr ?? "–"}</Text>
                        </div>
                        <div>
                            <Text size="xs" c="dimmed">Ohne PFA</Text>
                            <Text fw={700} size="xl">
                                {withoutPfa.length}
                            </Text>
                        </div>
                    </Group>
                </Paper>

                <Paper withBorder p={0}>
                    <ResponsiveTable minWidth={720} withTableBorder>
                        <Table.Thead>
                            <Table.Tr>
                                <Table.Th style={{ width: 90 }}>Sektion</Table.Th>
                                <Table.Th>Projektname</Table.Th>
                                <Table.Th style={{ width: 90 }}>Kategorie</Table.Th>
                                <Table.Th>Rohtext-Qualität &amp; Abschnitte</Table.Th>
                            </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                            {entries.map((e, idx) => (
                                <>
                                    <Table.Tr
                                        key={`row-${idx}`}
                                        style={{
                                            backgroundColor: expandedRows.has(idx)
                                                ? "var(--surface-alt)"
                                                : undefined,
                                        }}
                                    >
                                        <Table.Td>
                                            <Text size="xs" className="idt-tnum">{e.vib_section ?? "–"}</Text>
                                        </Table.Td>
                                        <Table.Td>
                                            <Text size="sm" lineClamp={2}>{e.vib_name_raw}</Text>
                                        </Table.Td>
                                        <Table.Td>
                                            <Badge variant="outline" color="var(--text-strong)" tt="none">
                                                {e.category}
                                            </Badge>
                                        </Table.Td>
                                        <Table.Td>
                                            <RawTextCell
                                                entry={e}
                                                expanded={expandedRows.has(idx)}
                                                onToggle={() => toggleRow(idx)}
                                            />
                                        </Table.Td>
                                    </Table.Tr>
                                    {expandedRows.has(idx) && (
                                        <Table.Tr key={`expanded-${idx}`}>
                                            <Table.Td colSpan={4} p={0}>
                                                <ExpandedRawText entry={e} />
                                            </Table.Td>
                                        </Table.Tr>
                                    )}
                                </>
                            ))}
                        </Table.Tbody>
                    </ResponsiveTable>
                </Paper>

                <Group justify="flex-end" gap="sm">
                    <Button variant="subtle" onClick={() => navigate("/admin/vib-import")}>
                        Abbrechen
                    </Button>
                    <Button onClick={() => navigate(`/admin/vib-import/review/${taskId}`)}>
                        Weiter zum Review →
                    </Button>
                </Group>
            </Stack>
        </Container>
    );
}

export default function VibStructurePreviewPage() {
    return (
        <RequirePermission perm="vib.import">
            <VibStructurePreviewPageContent />
        </RequirePermission>
    );
}
