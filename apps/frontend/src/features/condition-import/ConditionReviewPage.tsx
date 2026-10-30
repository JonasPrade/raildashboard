import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
    Alert,
    Anchor,
    Badge,
    Button,
    Container,
    Group,
    List,
    NumberInput,
    Paper,
    Select,
    Stack,
    Table,
    Text,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import RequirePermission from "../../components/RequirePermission";
import { API_BASE } from "../../shared/api/client";
import {
    conditionPageImageUrl,
    useConditionImportCheck,
    useConditionImportClasses,
    useConditionImportReports,
    useConditionImportValues,
    useCorrectConditionValue,
    useDeleteConditionReport,
    useReleaseConditionReport,
    type ConditionValue,
} from "../../shared/api/queries";
import { openConfirmModal } from "../../shared/ui/confirmModal";
import { LoadingState } from "../../shared/ui/LoadingState";
import { ErrorState } from "../../shared/ui/ErrorState";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { STATUS_TONE } from "../../shared/theme/semanticColors";
import { LAENDER, SCOPE_LABEL, type Scope } from "../condition/conditionFormat";

const METRIC_LABEL: Record<string, string> = {
    WBW: "WBW",
    WBW_BEWERTET: "Bewerteter WBW",
    WBW_ANTEIL: "Anteil WBW %",
    NOTE: "Note",
    VERTEILUNG_WBW: "Verteilung %",
    VERTEILUNG_MENGE: "Verteilung Menge",
    MENGE_BEWERTET: "Menge bewertet",
    MENGE_GESAMT: "Menge Bestand",
    ERNEUERUNGSBEDARF_MENGE: "Erneuerungsbedarf Menge",
    ERNEUERUNGSBEDARF_MRD: "Erneuerungsbedarf Mrd. €",
    NACHHOLBEDARF_MRD: "Nachholbedarf Mrd. €",
};

function errorDetail(error: unknown, fallback: string): string {
    return (error as { details?: { detail?: string } } | undefined)?.details?.detail ?? fallback;
}

const tableKey = (v: ConditionValue) => `${v.domain}|${v.scope}|${v.region ?? ""}`;
const tableLabel = (key: string) => {
    const [domain, scope, region] = key.split("|");
    const area = domain === "FAHRWEG" ? "Fahrweg" : "Personenbahnhöfe";
    return region ? `${area} · ${LAENDER[region] ?? region}` : `${area} · ${SCOPE_LABEL[scope as Scope] ?? scope}`;
};

function ValueCell({ value, year }: { value: ConditionValue; year: number }) {
    const correct = useCorrectConditionValue();
    const [draft, setDraft] = useState<number | string>(value.value);
    const save = async () => {
        if (Number(draft) === value.value) return;
        try {
            const result = await correct.mutateAsync({ id: value.id, year, value: Number(draft) });
            if (result.warnings.length > 0) {
                notifications.show({ color: "red", title: "Summen passen nicht", message: result.warnings.join(" ") });
            }
        } catch (error) {
            notifications.show({ color: "red", message: errorDetail(error, "Speichern fehlgeschlagen.") });
        }
    };
    return (
        <NumberInput
            aria-label="Wert"
            value={draft}
            onChange={setDraft}
            onBlur={() => void save()}
            decimalSeparator=","
            thousandSeparator="."
            hideControls
            size="xs"
            w={110}
        />
    );
}

function ConditionReviewContent() {
    const year = Number(useParams().year);
    const navigate = useNavigate();
    const { data: reports } = useConditionImportReports();
    const report = reports?.find((r) => r.year === year);
    const values = useConditionImportValues(year);
    const check = useConditionImportCheck(year);
    const { data: classes } = useConditionImportClasses();
    const release = useReleaseConditionReport();
    const remove = useDeleteConditionReport();
    const [table, setTable] = useState<string | null>(null);
    const [page, setPage] = useState<number | null>(null);

    const names = useMemo(() => new Map((classes ?? []).map((c) => [c.key, c.name])), [classes]);
    const tables = useMemo(() => {
        const keys = [...new Set((values.data ?? []).map(tableKey))];
        return keys.map((k) => ({ value: k, label: tableLabel(k) }));
    }, [values.data]);
    const currentTable = table ?? tables[0]?.value ?? null;
    const rows = (values.data ?? []).filter((v) => tableKey(v) === currentTable);
    const mismatches = check.data?.accepted_mismatches ?? [];
    const pages = [...new Set(rows.map((v) => v.source_page).filter((p): p is number => p !== null && p !== undefined))];
    const shownPage = page ?? pages[0] ?? null;

    if (values.isLoading || check.isLoading) return <Container py="xl"><LoadingState rows={6} /></Container>;
    if (values.isError) {
        return (
            <Container py="xl">
                <ErrorState onRetry={() => void values.refetch()}>Der Zustandsbericht {year} konnte nicht geladen werden.</ErrorState>
            </Container>
        );
    }

    const doRelease = () =>
        openConfirmModal({
            title: `Zustandsbericht ${year} freigeben?`,
            children: (
                <Text size="sm">
                    Alle {check.data?.values ?? 0} Werte gelten danach als geprüft und erscheinen auf /netzzustand.
                    {mismatches.length > 0 &&
                        ` ${mismatches.length} angenommene Abweichung(en) des Berichts bleiben vermerkt.`}
                </Text>
            ),
            labels: { confirm: "Freigeben", cancel: "Abbrechen" },
            onConfirm: async () => {
                try {
                    await release.mutateAsync(year);
                    notifications.show({ message: `Zustandsbericht ${year} freigegeben.` });
                } catch (error) {
                    notifications.show({ color: "red", message: errorDetail(error, "Freigabe fehlgeschlagen.") });
                }
            },
        });

    const doDelete = () =>
        openConfirmModal({
            title: `Zustandsbericht ${year} löschen?`,
            children: <Text size="sm">Alle Werte und das gespeicherte PDF dieses Jahrgangs werden gelöscht.</Text>,
            labels: { confirm: "Löschen", cancel: "Abbrechen" },
            danger: true,
            onConfirm: async () => {
                try {
                    await remove.mutateAsync(year);
                    navigate("/admin/zustandsbericht");
                } catch (error) {
                    notifications.show({ color: "red", message: errorDetail(error, "Löschen fehlgeschlagen.") });
                }
            },
        });

    return (
        <Container size="xl" py="xl">
            <Stack gap="lg">
                <Anchor component={Link} to="/admin/zustandsbericht" size="sm">← Zustandsbericht</Anchor>
                <Group justify="space-between" align="center" wrap="wrap">
                    <Group gap="sm">
                        <Title order={1}>Zustandsbericht {year}</Title>
                        {report && (
                            <Badge variant="light" color={report.status === "FREIGEGEBEN" ? STATUS_TONE.done : STATUS_TONE.active}>
                                {report.status === "FREIGEGEBEN" ? "freigegeben" : "Entwurf"}
                            </Badge>
                        )}
                    </Group>
                    <Group gap="sm">
                        <Button variant="default" color="red" onClick={doDelete}>Löschen</Button>
                        <Button onClick={doRelease} disabled={!check.data || check.data.values === 0} loading={release.isPending}>
                            {report?.status === "FREIGEGEBEN" ? "Erneut freigeben" : "Freigeben"}
                        </Button>
                    </Group>
                </Group>

                {check.data && (
                    <Stack gap="sm">
                        <Text size="sm">
                            {check.data.values} Werte, davon {check.data.unchecked} ungeprüft.
                        </Text>
                        {mismatches.length > 0 && (
                            <Alert color="gray" variant="light" title="Vom Agenten angenommene Abweichungen des Berichts">
                                <List size="sm">
                                    {mismatches.map((m, i) => (
                                        <List.Item key={i}>
                                            <b>{String(m.table)}</b>: {String(m.reason)} ({(m.errors as string[]).join(" ")})
                                        </List.Item>
                                    ))}
                                </List>
                            </Alert>
                        )}
                        {check.data.errors.length > 0 && (
                            <Alert color="red" variant="light" title="Prüfung">
                                <List size="sm">
                                    {check.data.errors.flatMap((t) =>
                                        t.errors.map((e) => <List.Item key={`${t.table}${e}`}><b>{t.table}</b>: {e}</List.Item>),
                                    )}
                                </List>
                            </Alert>
                        )}
                        {check.data.gaps.length > 0 && (
                            <Alert color="gray" variant="light" title="Lücken">
                                <List size="sm">
                                    {check.data.gaps.map((g) => <List.Item key={g}>{g}</List.Item>)}
                                </List>
                            </Alert>
                        )}
                    </Stack>
                )}

                {tables.length === 0 ? (
                    <Text c="dimmed">Noch keine Werte — Claude liest den Bericht mit dem Skill „zustandsbericht-import“ ein.</Text>
                ) : (
                    <Group align="flex-start" wrap="wrap" gap="lg">
                        <Stack gap="sm" style={{ flex: "1 1 520px", minWidth: 0 }}>
                            <Select
                                label="Tabelle"
                                data={tables}
                                value={currentTable}
                                onChange={(v) => {
                                    setTable(v);
                                    setPage(null);
                                }}
                                allowDeselect={false}
                                searchable
                                w={{ base: "100%", sm: 360 }}
                            />
                            <ResponsiveTable minWidth={560}>
                                <Table.Thead>
                                    <Table.Tr>
                                        <Table.Th>Anlagenklasse</Table.Th>
                                        <Table.Th>Kennzahl</Table.Th>
                                        <Table.Th>Note</Table.Th>
                                        <Table.Th>Jahr</Table.Th>
                                        <Table.Th>Wert</Table.Th>
                                        <Table.Th>Quelle</Table.Th>
                                    </Table.Tr>
                                </Table.Thead>
                                <Table.Tbody>
                                    {rows.map((v) => (
                                        <Table.Tr key={v.id}>
                                            <Table.Td data-label="Anlagenklasse">{v.class_key ? (names.get(v.class_key) ?? v.class_key) : "Summe"}</Table.Td>
                                            <Table.Td data-label="Kennzahl">{METRIC_LABEL[v.metric] ?? v.metric}</Table.Td>
                                            <Table.Td data-label="Note">{v.grade ?? ""}</Table.Td>
                                            <Table.Td data-label="Jahr">{v.reference_year}</Table.Td>
                                            <Table.Td data-label="Wert">
                                                <Group gap={6} wrap="nowrap">
                                                    <ValueCell key={`${v.id}-${v.value}`} value={v} year={year} />
                                                    {v.status === "UNGEPRUEFT" && <Text size="xs" c="dimmed">ungeprüft</Text>}
                                                </Group>
                                            </Table.Td>
                                            <Table.Td data-label="Quelle">
                                                {v.source_page ? (
                                                    <Anchor component="button" size="sm" onClick={() => setPage(v.source_page ?? null)}>
                                                        S. {v.source_page}
                                                    </Anchor>
                                                ) : null}
                                                {v.source_ref ? ` · ${v.source_ref}` : ""}
                                            </Table.Td>
                                        </Table.Tr>
                                    ))}
                                </Table.Tbody>
                            </ResponsiveTable>
                        </Stack>
                        <Paper withBorder p="sm" style={{ flex: "1 1 420px", minWidth: 0 }}>
                            {shownPage && report?.has_pdf ? (
                                <Stack gap={6}>
                                    <Text size="sm" fw={600}>PDF-Seite {shownPage}</Text>
                                    <a href={conditionPageImageUrl(year, shownPage, API_BASE)} target="_blank" rel="noreferrer">
                                        <img
                                            src={conditionPageImageUrl(year, shownPage, API_BASE)}
                                            alt={`Seite ${shownPage} des Zustandsberichts ${year}`}
                                            style={{ width: "100%", height: "auto", display: "block" }}
                                        />
                                    </a>
                                </Stack>
                            ) : (
                                <Text size="sm" c="dimmed">
                                    {report?.has_pdf ? "Keine Seitenangabe an diesen Werten." : "Kein PDF gespeichert — in der Übersicht hochladen."}
                                </Text>
                            )}
                        </Paper>
                    </Group>
                )}
            </Stack>
        </Container>
    );
}

export default function ConditionReviewPage() {
    return (
        <RequirePermission perm="condition.import">
            <ConditionReviewContent />
        </RequirePermission>
    );
}
