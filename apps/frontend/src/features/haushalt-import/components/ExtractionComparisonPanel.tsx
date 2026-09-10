import { useState } from "react";
import { Alert, Badge, Box, Button, Group, Stack, Table, Text } from "@mantine/core";
import { ResponsiveTable } from "../../../shared/ui/ResponsiveTable";
import type { HaushaltsExtractionComparison } from "../../../shared/api/queries";

const SOURCE_LABEL: Record<string, string> = {
    pdfplumber: "Werte aus pdfplumber",
    ocr: "Werte aus der Texterkennung",
};

/**
 * Only shown when the run read the PDF twice — once with pdfplumber, once with
 * the shared OCR stage. The two paths must produce the same rows and the same
 * numbers before the OCR stage may supply the imported values; this panel is
 * that evidence, and it never changes what gets imported.
 */
export function ExtractionComparisonPanel({
    comparison,
    source,
}: {
    comparison?: HaushaltsExtractionComparison | null;
    source?: string;
}) {
    const [open, setOpen] = useState(false);

    if (!comparison) return null;

    const sourceLabel = SOURCE_LABEL[source ?? "pdfplumber"] ?? `Werte aus ${source}`;
    const rowsDiffer =
        comparison.rows_only_pdfplumber.length > 0 || comparison.rows_only_ocr.length > 0;

    return (
        <Stack gap="xs">
            <Group gap="sm" wrap="wrap">
                <Text size="sm" fw={500}>
                    Texterkennung im Vergleich
                </Text>
                <Badge color={comparison.identical ? "green" : "orange"} variant="light" size="sm">
                    {comparison.identical ? "identisch" : "Abweichungen"}
                </Badge>
                <Badge color="gray" variant="light" size="sm">
                    {sourceLabel}
                </Badge>
                {!comparison.identical && (
                    <Button variant="subtle" size="compact-xs" onClick={() => setOpen((v) => !v)}>
                        {open ? "Abweichungen ausblenden" : "Abweichungen anzeigen"}
                    </Button>
                )}
            </Group>

            {comparison.error ? (
                <Alert color="orange" variant="light" title="Texterkennung nicht gelaufen">
                    {comparison.error} — der Import wurde vollständig über pdfplumber gelesen.
                </Alert>
            ) : (
                <Text size="xs" c="dimmed">
                    pdfplumber {comparison.rows_pdfplumber} Zeilen · Texterkennung (
                    {comparison.ocr_model || "unbekannt"}) {comparison.rows_ocr} Zeilen ·{" "}
                    {comparison.value_differences_total} abweichende Werte
                </Text>
            )}

            {comparison.identical && !comparison.error && (
                <Alert color="green" variant="light" title="Beide Wege liefern dasselbe">
                    Die Texterkennung hat jede Zeile und jeden Wert wie pdfplumber gelesen. Das ist
                    die Voraussetzung dafür, den Import dauerhaft auf die Texterkennung umzustellen.
                </Alert>
            )}

            {rowsDiffer && (
                <Alert color="orange" variant="light" title="Unterschiedliche Zeilen">
                    {comparison.rows_only_pdfplumber.length > 0 && (
                        <Text size="xs">
                            Nur pdfplumber: {comparison.rows_only_pdfplumber.join(", ")}
                        </Text>
                    )}
                    {comparison.rows_only_ocr.length > 0 && (
                        <Text size="xs">
                            Nur Texterkennung: {comparison.rows_only_ocr.join(", ")}
                        </Text>
                    )}
                </Alert>
            )}

            {open && comparison.value_differences.length > 0 && (
                <Box style={{ overflowX: "auto" }}>
                    <ResponsiveTable minWidth={640} striped withTableBorder fz="xs">
                        <Table.Thead>
                            <Table.Tr>
                                <Table.Th>Zeile</Table.Th>
                                <Table.Th>Feld</Table.Th>
                                <Table.Th>pdfplumber</Table.Th>
                                <Table.Th>Texterkennung</Table.Th>
                            </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                            {comparison.value_differences.map((difference, index) => (
                                <Table.Tr key={`${difference.row_key}-${difference.field}-${index}`}>
                                    <Table.Td>{difference.row_key}</Table.Td>
                                    <Table.Td>{difference.field}</Table.Td>
                                    <Table.Td>{difference.pdfplumber ?? "–"}</Table.Td>
                                    <Table.Td>{difference.ocr ?? "–"}</Table.Td>
                                </Table.Tr>
                            ))}
                        </Table.Tbody>
                    </ResponsiveTable>
                    {comparison.value_differences_total > comparison.value_differences.length && (
                        <Text size="xs" c="dimmed" mt={4}>
                            … und{" "}
                            {comparison.value_differences_total - comparison.value_differences.length}{" "}
                            weitere
                        </Text>
                    )}
                </Box>
            )}
        </Stack>
    );
}

export default ExtractionComparisonPanel;
