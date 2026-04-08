import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
    Alert,
    Badge,
    Box,
    Button,
    Container,
    Group,
    Loader,
    Paper,
    ScrollArea,
    Stack,
    Table,
    Text,
    Title,
    Tooltip,
} from "@mantine/core";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth } from "../../lib/auth";
import {
    useVibParseResult,
    type VibEntryProposed,
} from "../../shared/api/queries";

const CATEGORY_COLORS: Record<string, string> = {
    laufend: "blue",
    neu: "green",
    potentiell: "yellow",
    abgeschlossen: "gray",
};

// Sub-sections we look for in raw_text
const SUBSECTIONS: { key: string; label: string; pattern: RegExp }[] = [
    { key: "vz", label: "Verk. Zielsetzung", pattern: /Verkehrliche\s+Zielsetzung/i },
    { key: "dm", label: "Durchgef. Maßnahmen", pattern: /Durchgef[üu]hrte/i },
    { key: "nm", label: "Noch umzusetzende", pattern: /Noch\s+umzusetzende/i },
    { key: "ba", label: "Bauaktivitäten", pattern: /Bauaktivit[äa]ten/i },
    { key: "ti", label: "Teilinbetriebnahmen", pattern: /Teilinbetriebnahmen/i },
    { key: "pk", label: "Projektkenndaten", pattern: /Projektkenndaten/i },
];

function rawTextQualityColor(len: number): string {
    if (len === 0) return "red";
    if (len < 200) return "orange";
    if (len < 800) return "yellow";
    return "green";
}

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
    const qualityColor = rawTextQualityColor(len);

    const detected = SUBSECTIONS.filter((s) => s.pattern.test(raw));
    const missing = SUBSECTIONS.filter((s) => !s.pattern.test(raw));

    return (
        <Stack gap={4} style={{ cursor: "pointer" }} onClick={onToggle}>
            <Group gap={6} wrap="nowrap">
                <Tooltip label={`${len} Zeichen`} withArrow>
                    <Badge size="xs" color={qualityColor} variant="filled">
                        {len > 0 ? `${(len / 1000).toFixed(1)}k` : "leer"}
                    </Badge>
                </Tooltip>
                {entry.pfa_entries.length > 0 ? (
                    <Badge size="xs" color="teal" variant="light">
                        {entry.pfa_entries.length} PFA
                    </Badge>
                ) : (
                    <Badge size="xs" color="orange" variant="light">
                        0 PFA
                    </Badge>
                )}
            </Group>
            <Group gap={4} wrap="wrap">
                {detected.map((s) => (
                    <Badge key={s.key} size="xs" color="blue" variant="dot">
                        {s.label}
                    </Badge>
                ))}
                {missing.map((s) => (
                    <Badge key={s.key} size="xs" color="gray" variant="outline">
                        {s.label}
                    </Badge>
                ))}
            </Group>
            <Text size="xs" c="blue">
                {expanded ? "▲ einklappen" : "▼ Rohtext anzeigen"}
            </Text>
        </Stack>
    );
}

function ExpandedRawText({ entry }: { entry: VibEntryProposed }) {
    const raw = entry.raw_text ?? "";
    const detected = SUBSECTIONS.filter((s) => s.pattern.test(raw));
    const missing = SUBSECTIONS.filter((s) => !s.pattern.test(raw));

    return (
        <Box p="md" bg="gray.0" style={{ borderTop: "1px solid var(--mantine-color-gray-2)" }}>
            <Stack gap="xs">
                <Group gap="xl">
                    <div>
                        <Text size="xs" c="dimmed">Zeichen</Text>
                        <Text fw={600} size="sm">{raw.length.toLocaleString("de-DE")}</Text>
                    </div>
                    <div>
                        <Text size="xs" c="dimmed">PFA-Zeilen</Text>
                        <Text fw={600} size="sm" c={entry.pfa_entries.length === 0 ? "orange" : undefined}>
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
                              <Badge key={s.key} size="xs" color="blue">
                                  ✓ {s.label}
                              </Badge>
                          ))
                        : <Text size="xs" c="dimmed">–</Text>}
                </Group>
                {missing.length > 0 && (
                    <Group gap={6}>
                        <Text size="xs" c="dimmed">Nicht gefunden:</Text>
                        {missing.map((s) => (
                            <Badge key={s.key} size="xs" color="gray" variant="outline">
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
                                fontFamily: "var(--mantine-font-family-monospace)",
                                background: "var(--mantine-color-gray-0)",
                                borderRadius: 4,
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

export default function VibStructurePreviewPage() {
    const { taskId } = useParams<{ taskId: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();

    const { data: parseResult, isLoading, isError } = useVibParseResult(taskId ?? null);
    const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

    const toggleRow = (idx: number) =>
        setExpandedRows((prev) => {
            const next = new Set(prev);
            next.has(idx) ? next.delete(idx) : next.add(idx);
            return next;
        });

    if (user?.role !== "editor" && user?.role !== "admin") {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    if (isLoading) {
        return (
            <Container py="xl">
                <Group justify="center"><Loader /></Group>
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
                    <Title order={2}>VIB-Import — Strukturvorschau</Title>
                    <Text c="dimmed" size="sm" mt={4}>
                        Struktur erkannt. Prüfen Sie die Vorhaben und wechseln Sie zum Review.
                        KI-Extraktion ist pro Vorhaben im Review verfügbar.
                    </Text>
                </div>

                <Paper withBorder p="md">
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
                            <Text fw={700} size="xl" c={withoutPfa.length > 0 ? "orange" : "green"}>
                                {withoutPfa.length}
                            </Text>
                        </div>
                    </Group>
                </Paper>


                <Paper withBorder p={0}>
                    <Table withTableBorder>
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
                                                ? "var(--mantine-color-blue-0)"
                                                : undefined,
                                        }}
                                    >
                                        <Table.Td>
                                            <Text size="xs" ff="monospace">{e.vib_section ?? "–"}</Text>
                                        </Table.Td>
                                        <Table.Td>
                                            <Text size="sm" lineClamp={2}>{e.vib_name_raw}</Text>
                                        </Table.Td>
                                        <Table.Td>
                                            <Badge size="xs" color={CATEGORY_COLORS[e.category] ?? "gray"}>
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
                    </Table>
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
