import { useState } from "react";
import { Alert, Badge, Box, Button, Collapse, Group, Stack, Table, Text } from "@mantine/core";
import type {
    HaushaltsColumnMapping,
    HaushaltsTableSection,
} from "../../../shared/api/queries";

const SOURCE_LABEL: Record<HaushaltsColumnMapping["source"], string> = {
    header: "aus der Tabellenüberschrift",
    llm: "per KI zugeordnet",
    fallback: "Standard-Layout (2026)",
};

const SOURCE_COLOR: Record<HaushaltsColumnMapping["source"], string> = {
    header: "green",
    llm: "yellow",
    fallback: "orange",
};

/**
 * Shows how the parser read the PDF before any value is imported: which table
 * of Teil B was used, and which PDF column each target field was taken from.
 * The values themselves are transferred verbatim through this mapping — if the
 * mapping is right, the numbers are right, so it is the one thing worth
 * checking up front.
 */
export function ColumnMappingPanel({
    columnMap,
    sections,
}: {
    columnMap?: HaushaltsColumnMapping | null;
    sections?: HaushaltsTableSection[];
}) {
    const [open, setOpen] = useState(false);

    if (!columnMap && !sections?.length) return null;

    const imported = sections?.filter((s) => s.imported) ?? [];
    const skipped = sections?.filter((s) => !s.imported) ?? [];
    const unmapped = columnMap?.columns.filter((c) => c.index === null) ?? [];

    return (
        <Stack gap="xs">
            <Group gap="sm" wrap="wrap">
                <Text size="sm" fw={500}>
                    Spaltenzuordnung
                </Text>
                {columnMap && (
                    <Badge color={SOURCE_COLOR[columnMap.source]} variant="light" size="sm">
                        {SOURCE_LABEL[columnMap.source]}
                    </Badge>
                )}
                <Button variant="subtle" size="compact-xs" onClick={() => setOpen((v) => !v)}>
                    {open ? "Details ausblenden" : "Details anzeigen"}
                </Button>
            </Group>

            {imported.length > 0 && (
                <Text size="xs" c="dimmed">
                    Eingelesen:{" "}
                    {imported
                        .map((s) => `Tabelle ${s.number ?? "?"} – ${s.title} (S. ${s.page_from}–${s.page_to})`)
                        .join(", ")}
                    {skipped.length > 0 && (
                        <>
                            {" · Übersprungen: "}
                            {skipped.map((s) => `Tabelle ${s.number ?? "?"} – ${s.title}`).join(", ")}
                        </>
                    )}
                </Text>
            )}

            {columnMap?.source === "fallback" && (
                <Alert color="orange" variant="light" title="Spalten nicht aus dem PDF erkannt">
                    Die Kopfzeile der Tabelle konnte nicht gelesen werden. Der Import verwendet das
                    Spalten-Layout des Berichts 2026. Bitte die Werte unten stichprobenartig gegen das
                    PDF prüfen, bevor importiert wird.
                </Alert>
            )}

            {unmapped.length > 0 && (
                <Alert color="yellow" variant="light" title="Spalten ohne Zuordnung">
                    Für diese Felder gibt es im PDF keine erkannte Spalte – sie bleiben leer:{" "}
                    {unmapped.map((c) => c.label).join(", ")}.
                </Alert>
            )}

            <Collapse in={open}>
                <Box style={{ overflowX: "auto" }}>
                    <Table striped highlightOnHover withTableBorder fz="xs">
                        <Table.Thead>
                            <Table.Tr>
                                <Table.Th>Zielfeld</Table.Th>
                                <Table.Th>PDF-Spalte</Table.Th>
                                <Table.Th>Erkannte Überschrift</Table.Th>
                            </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                            {columnMap?.columns.map((entry) => (
                                <Table.Tr key={entry.field}>
                                    <Table.Td>{entry.label}</Table.Td>
                                    <Table.Td>
                                        {entry.index === null ? (
                                            <Text span c="dimmed">
                                                –
                                            </Text>
                                        ) : (
                                            entry.index + 1
                                        )}
                                    </Table.Td>
                                    <Table.Td c={entry.header ? undefined : "dimmed"}>
                                        {entry.header || "–"}
                                    </Table.Td>
                                </Table.Tr>
                            ))}
                        </Table.Tbody>
                    </Table>
                </Box>
            </Collapse>
        </Stack>
    );
}

export default ColumnMappingPanel;
