import { useState } from "react";
import { Link } from "react-router-dom";
import { Anchor, Badge, Button, Container, FileInput, Group, NumberInput, Paper, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import RequirePermission from "../../components/RequirePermission";
import {
    useConditionImportReports,
    useCreateConditionReport,
    useUploadConditionPdf,
    type ConditionReport,
} from "../../shared/api/queries";
import { exceedsUploadLimit, tooLargeMessage, uploadErrorMessage } from "../../shared/api/uploads";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { LoadingState } from "../../shared/ui/LoadingState";
import { ErrorState } from "../../shared/ui/ErrorState";
import { STATUS_TONE } from "../../shared/theme/semanticColors";

function errorDetail(error: unknown, fallback: string): string {
    return (error as { details?: { detail?: string } } | undefined)?.details?.detail ?? fallback;
}

function PdfUpload({ report }: { report: ConditionReport }) {
    const upload = useUploadConditionPdf();
    const onFile = async (file: File | null) => {
        if (!file) return;
        if (exceedsUploadLimit(file)) {
            notifications.show({ color: "red", message: tooLargeMessage(file) });
            return;
        }
        try {
            await upload.mutateAsync({ year: report.year, pdf: file });
            notifications.show({ message: `PDF zum Bericht ${report.year} gespeichert.` });
        } catch (error) {
            notifications.show({ color: "red", message: uploadErrorMessage(error, "Hochladen fehlgeschlagen.") });
        }
    };
    return (
        <FileInput
            aria-label={`PDF für ${report.year}`}
            placeholder={report.has_pdf ? "PDF ersetzen" : "PDF hochladen"}
            accept="application/pdf"
            size="xs"
            w={170}
            clearable={false}
            disabled={upload.isPending}
            onChange={(file) => void onFile(file)}
        />
    );
}

function NewReport() {
    const create = useCreateConditionReport();
    const [year, setYear] = useState<number | string>(new Date().getFullYear());
    const [sourceUrl, setSourceUrl] = useState("");
    const submit = async () => {
        try {
            await create.mutateAsync({ year: Number(year), source_url: sourceUrl.trim() || null });
            setSourceUrl("");
            notifications.show({ message: `Zustandsbericht ${year} angelegt.` });
        } catch (error) {
            notifications.show({ color: "red", message: errorDetail(error, "Anlegen fehlgeschlagen.") });
        }
    };
    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="sm">
                <Text fw={600}>Jahrgang anlegen</Text>
                <Group align="flex-end" wrap="wrap">
                    <NumberInput label="Berichtsjahr" value={year} onChange={setYear} min={2015} max={2100} w={140} />
                    <TextInput
                        label="Quelle (URL des PDF)"
                        value={sourceUrl}
                        onChange={(e) => setSourceUrl(e.currentTarget.value)}
                        flex="1 1 280px"
                    />
                    <Button onClick={() => void submit()} loading={create.isPending}>Anlegen</Button>
                </Group>
                <Text size="sm" c="dimmed">
                    Danach das PDF hochladen und Claude mit dem Skill „zustandsbericht-import“ einlesen lassen. Die Werte
                    bleiben ungeprüft, bis der Jahrgang hier freigegeben ist.
                </Text>
            </Stack>
        </Paper>
    );
}

function ConditionImportPageContent() {
    const { data: reports, isLoading, isError, refetch } = useConditionImportReports();
    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Group justify="space-between" align="baseline">
                    <Title order={1}>Zustandsbericht</Title>
                    <Anchor component={Link} to="/netzzustand" size="sm">Öffentliche Seite →</Anchor>
                </Group>
                <NewReport />
                {isLoading ? (
                    <LoadingState rows={3} />
                ) : isError ? (
                    <ErrorState onRetry={() => void refetch()}>Die Jahrgänge konnten nicht geladen werden.</ErrorState>
                ) : !reports || reports.length === 0 ? (
                    <Text c="dimmed">Noch kein Jahrgang angelegt.</Text>
                ) : (
                    <ResponsiveTable>
                        <Table.Thead>
                            <Table.Tr>
                                <Table.Th>Jahrgang</Table.Th>
                                <Table.Th>Status</Table.Th>
                                <Table.Th>Werte</Table.Th>
                                <Table.Th>PDF</Table.Th>
                                <Table.Th />
                            </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                            {reports.map((r) => (
                                <Table.Tr key={r.year}>
                                    <Table.Td data-label="Jahrgang">
                                        <Text fw={600}>{r.year}</Text>
                                        <Text size="xs" c="dimmed">{r.title}</Text>
                                    </Table.Td>
                                    <Table.Td data-label="Status">
                                        <Badge
                                            variant="light"
                                            color={r.status === "FREIGEGEBEN" ? STATUS_TONE.done : STATUS_TONE.active}
                                        >
                                            {r.status === "FREIGEGEBEN" ? "freigegeben" : "Entwurf"}
                                        </Badge>
                                    </Table.Td>
                                    <Table.Td data-label="Werte">
                                        {r.values_total}
                                        {r.values_unchecked > 0 && <Text span size="sm" c="dimmed"> · {r.values_unchecked} ungeprüft</Text>}
                                    </Table.Td>
                                    <Table.Td data-label="PDF">
                                        <PdfUpload report={r} />
                                    </Table.Td>
                                    <Table.Td>
                                        <Button component={Link} to={`/admin/zustandsbericht/${r.year}`} variant="light" size="xs">
                                            Prüfen
                                        </Button>
                                    </Table.Td>
                                </Table.Tr>
                            ))}
                        </Table.Tbody>
                    </ResponsiveTable>
                )}
            </Stack>
        </Container>
    );
}

export default function ConditionImportPage() {
    return (
        <RequirePermission perm="condition.import">
            <ConditionImportPageContent />
        </RequirePermission>
    );
}
