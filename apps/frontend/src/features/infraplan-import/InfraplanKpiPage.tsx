import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
    ActionIcon,
    Alert,
    Anchor,
    Badge,
    Button,
    Container,
    Group,
    Image,
    Loader,
    NumberInput,
    Select,
    SimpleGrid,
    Stack,
    Table,
    Tabs,
    Text,
    TextInput,
} from "@mantine/core";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import { Plus, Trash2 } from "lucide-react";
import { ChronicleCard, ChronicleHeadline } from "../../components/chronicle";
import RequirePermission from "../../components/RequirePermission";
import { API_BASE } from "../../shared/api/client";
import {
    infraplanPageImageUrl,
    useApproveInfraplanKpiValues,
    useInfraplanKpis,
    useInfraplanKpiValues,
    useInfraplanReports,
    useSaveInfraplanKpiValues,
    type InfraplanKpi,
    type InfraplanKpiValue,
} from "../../shared/api/queries";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { KPI_KIND_LABEL } from "../infraplan/infraplanFormat";
import { buildKpiPayload, invalidRows, newUid, slotKey, toFormRows, type KpiFormRow } from "./kpiForm";

const KIND_DATA = [
    { value: "IST", label: "Ist" },
    { value: "ZIEL", label: "Ziel" },
];

function errorDetail(error: unknown, fallback: string): string {
    const detail = (error as { details?: { detail?: unknown } } | undefined)?.details?.detail;
    return typeof detail === "string" ? detail : fallback;
}

function formatValue(value: number, unit?: string | null): string {
    return `${value.toLocaleString("de-DE", { maximumFractionDigits: 3 })}${unit ? ` ${unit}` : ""}`;
}

// ---------------------------------------------------------------------------
// Manual entry: one KPI at a time
// ---------------------------------------------------------------------------

function KpiEditor({
    year,
    kpi,
    values,
}: {
    year: number;
    kpi: InfraplanKpi;
    values: InfraplanKpiValue[];
}) {
    const save = useSaveInfraplanKpiValues(year);
    const original = useMemo(() => values.filter((v) => v.kpi_key === kpi.key), [values, kpi.key]);
    const [rows, setRows] = useState<KpiFormRow[] | null>(null);
    const initialRows = useMemo(() => toFormRows(original), [original]);
    const current = rows ?? initialRows;
    const statusBySlot = useMemo(() => new Map(original.map((v) => [slotKey(v), v.status])), [original]);
    const invalid = invalidRows(current);
    const payload = buildKpiPayload(original, current);

    const update = (uid: string, patch: Partial<KpiFormRow>) =>
        setRows(current.map((r) => (r.uid === uid ? { ...r, ...patch } : r)));
    const add = () => {
        const last = current.at(-1);
        setRows([
            ...current,
            {
                uid: newUid(),
                kpi_key: kpi.key,
                year: last?.year != null ? last.year + 1 : year - 1,
                value_kind: last?.value_kind ?? "IST",
                series: last?.series ?? "",
                value: null,
                source_page: last?.source_page ?? null,
            },
        ]);
    };

    const handleSave = async () => {
        try {
            const result = await save.mutateAsync({ values: payload });
            setRows(null);
            notifications.show({
                color: "green",
                message: `${result.written} Werte gespeichert, ${result.removed} entfernt.`,
            });
        } catch (error) {
            notifications.show({ color: "red", message: errorDetail(error, "Speichern fehlgeschlagen.") });
        }
    };

    const num = (v: string | number): number | null => (v === "" || v === null ? null : Number(v));

    return (
        <Stack gap="sm">
            <Text size="sm" c="dimmed">
                {kpi.description ?? KPI_KIND_LABEL[kpi.kind] ?? kpi.kind}
                {kpi.unit ? ` · Einheit: ${kpi.unit}` : ""}
            </Text>
            <ResponsiveTable minWidth={680} withTableBorder verticalSpacing={4}>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Jahr</Table.Th>
                        <Table.Th>Art</Table.Th>
                        <Table.Th>Teilreihe</Table.Th>
                        <Table.Th>Wert{kpi.unit ? ` (${kpi.unit})` : ""}</Table.Th>
                        <Table.Th>Quellseite</Table.Th>
                        <Table.Th>Status</Table.Th>
                        <Table.Th />
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {current.map((r) => {
                        const status = statusBySlot.get(slotKey(r));
                        const bad = invalid.has(r.uid);
                        return (
                            <Table.Tr key={r.uid}>
                                <Table.Td>
                                    <NumberInput
                                        size="xs"
                                        w={90}
                                        value={r.year ?? ""}
                                        onChange={(v) => update(r.uid, { year: num(v) })}
                                        allowDecimal={false}
                                        error={bad && r.year === null}
                                        aria-label="Jahr"
                                    />
                                </Table.Td>
                                <Table.Td>
                                    <Select
                                        size="xs"
                                        w={90}
                                        data={KIND_DATA}
                                        value={r.value_kind}
                                        onChange={(v) => update(r.uid, { value_kind: (v as "IST" | "ZIEL") ?? "IST" })}
                                        allowDeselect={false}
                                        aria-label="Ist oder Ziel"
                                    />
                                </Table.Td>
                                <Table.Td>
                                    <TextInput
                                        size="xs"
                                        w={140}
                                        placeholder="gesamt"
                                        value={r.series}
                                        onChange={(e) => update(r.uid, { series: e.currentTarget.value })}
                                        aria-label="Teilreihe"
                                    />
                                </Table.Td>
                                <Table.Td>
                                    <NumberInput
                                        size="xs"
                                        w={120}
                                        value={r.value ?? ""}
                                        onChange={(v) => update(r.uid, { value: num(v) })}
                                        decimalSeparator=","
                                        thousandSeparator="."
                                        error={bad}
                                        aria-label="Wert"
                                    />
                                </Table.Td>
                                <Table.Td>
                                    <NumberInput
                                        size="xs"
                                        w={80}
                                        value={r.source_page ?? ""}
                                        onChange={(v) => update(r.uid, { source_page: num(v) })}
                                        allowDecimal={false}
                                        min={1}
                                        aria-label="Quellseite"
                                    />
                                </Table.Td>
                                <Table.Td>
                                    {status === "UNGEPRUEFT" ? (
                                        <Badge size="xs" color="orange" variant="light">ungeprüft</Badge>
                                    ) : status === "GEPRUEFT" ? (
                                        <Badge size="xs" color="green" variant="light">geprüft</Badge>
                                    ) : (
                                        <Badge size="xs" color="gray" variant="light">neu</Badge>
                                    )}
                                </Table.Td>
                                <Table.Td>
                                    <ActionIcon
                                        variant="subtle"
                                        color="red"
                                        aria-label="Zeile entfernen"
                                        onClick={() => setRows(current.filter((x) => x.uid !== r.uid))}
                                    >
                                        <Trash2 size={16} />
                                    </ActionIcon>
                                </Table.Td>
                            </Table.Tr>
                        );
                    })}
                </Table.Tbody>
            </ResponsiveTable>
            {current.length === 0 && <Text size="sm" c="dimmed">Noch keine Werte für diese Kennzahl.</Text>}
            {invalid.size > 0 && (
                <Text size="xs" c="red">
                    Jede Zeile braucht Jahr und Wert; Jahr × Art × Teilreihe darf nur einmal vorkommen.
                </Text>
            )}
            <Group gap="sm" wrap="wrap">
                <Button variant="light" leftSection={<Plus size={16} />} onClick={add}>
                    Zeile hinzufügen
                </Button>
                <Button onClick={handleSave} loading={save.isPending} disabled={payload.length === 0 || invalid.size > 0}>
                    Speichern{payload.length > 0 ? ` (${payload.length})` : ""}
                </Button>
                {rows !== null && (
                    <Button variant="subtle" onClick={() => setRows(null)}>
                        Verwerfen
                    </Button>
                )}
            </Group>
            <Text size="xs" c="dimmed">
                Von Hand eingetragene Werte gelten als geprüft. Geänderte Werte eines KI-Eintrags werden dabei
                ebenfalls als geprüft gespeichert.
            </Text>
        </Stack>
    );
}

// ---------------------------------------------------------------------------
// Approval: unchecked values next to the page they were read from
// ---------------------------------------------------------------------------

function Approval({
    year,
    values,
    kpis,
    parseResultId,
}: {
    year: number;
    values: InfraplanKpiValue[];
    kpis: Map<string, InfraplanKpi>;
    parseResultId: number | null;
}) {
    const approve = useApproveInfraplanKpiValues(year);
    const unchecked = values.filter((v) => v.status === "UNGEPRUEFT");
    const byPage = useMemo(() => {
        const groups = new Map<number | null, InfraplanKpiValue[]>();
        for (const v of unchecked) {
            const p = v.source_page ?? null;
            groups.set(p, [...(groups.get(p) ?? []), v]);
        }
        return [...groups.entries()].sort(([a], [b]) => (a ?? 1e9) - (b ?? 1e9));
    }, [unchecked]);

    const handleApprove = () =>
        modals.openConfirmModal({
            title: `Kennzahlen ${year} freigeben?`,
            children: (
                <Text size="sm">
                    {unchecked.length} ungeprüfte Werte werden als geprüft markiert und erscheinen auf der
                    öffentlichen Infraplan-Seite.
                </Text>
            ),
            labels: { confirm: "Freigeben", cancel: "Abbrechen" },
            onConfirm: async () => {
                try {
                    const result = await approve.mutateAsync();
                    notifications.show({ color: "green", message: `${result.approved} Werte freigegeben.` });
                } catch (error) {
                    notifications.show({ color: "red", message: errorDetail(error, "Freigabe fehlgeschlagen.") });
                }
            },
        });

    if (unchecked.length === 0) {
        return (
            <Alert color="green" variant="light">
                Alle Kennzahlwerte dieses Jahrgangs sind geprüft.
            </Alert>
        );
    }

    return (
        <Stack gap="md">
            <Group justify="space-between" wrap="wrap">
                <Text size="sm">
                    {unchecked.length} Werte wurden per KI aus den Diagrammen gelesen und sind noch nicht öffentlich.
                    Vergleiche sie mit dem Seitenbild; korrigieren kannst du sie unter „Erfassen“.
                </Text>
                <Button onClick={handleApprove} loading={approve.isPending}>
                    Jahrgang freigeben
                </Button>
            </Group>
            {byPage.map(([page, list]) => (
                <ChronicleCard key={page ?? "none"}>
                    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                        <Stack gap={4}>
                            <Text fw={600} size="sm">{page != null ? `Seite ${page}` : "Ohne Quellseite"}</Text>
                            {page != null && parseResultId != null ? (
                                <Anchor
                                    href={infraplanPageImageUrl(parseResultId, page, API_BASE)}
                                    target="_blank"
                                    rel="noreferrer"
                                >
                                    <Image
                                        src={infraplanPageImageUrl(parseResultId, page, API_BASE)}
                                        alt={`Infraplan ${year}, Seite ${page}`}
                                        fit="contain"
                                        radius="sm"
                                        style={{ border: "1px solid var(--mantine-color-default-border)" }}
                                    />
                                </Anchor>
                            ) : (
                                <Text size="xs" c="dimmed">Kein Seitenbild verfügbar.</Text>
                            )}
                        </Stack>
                        <ResponsiveTable minWidth={360} striped verticalSpacing={4} fz="sm">
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Kennzahl</Table.Th>
                                    <Table.Th>Jahr</Table.Th>
                                    <Table.Th>Art</Table.Th>
                                    <Table.Th ta="right">Wert</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {[...list]
                                    .sort((a, b) => a.kpi_key.localeCompare(b.kpi_key) || a.year - b.year)
                                    .map((v) => {
                                        const kpi = kpis.get(v.kpi_key);
                                        return (
                                            <Table.Tr key={v.id}>
                                                <Table.Td>
                                                    {kpi?.name ?? v.kpi_key}
                                                    {v.series && <Text span size="xs" c="dimmed"> · {v.series}</Text>}
                                                </Table.Td>
                                                <Table.Td>{v.year}</Table.Td>
                                                <Table.Td>{v.value_kind === "IST" ? "Ist" : "Ziel"}</Table.Td>
                                                <Table.Td ta="right" style={{ whiteSpace: "nowrap" }}>
                                                    {formatValue(v.value, kpi?.unit)}
                                                </Table.Td>
                                            </Table.Tr>
                                        );
                                    })}
                            </Table.Tbody>
                        </ResponsiveTable>
                    </SimpleGrid>
                </ChronicleCard>
            ))}
        </Stack>
    );
}

function InfraplanKpiPageContent() {
    const params = useParams<{ year: string }>();
    const year = Number(params.year);
    const { data: kpis, isLoading: kpisLoading } = useInfraplanKpis();
    const { data: values, isLoading: valuesLoading, isError } = useInfraplanKpiValues(year);
    const { data: reports } = useInfraplanReports();
    const report = reports?.find((r) => r.year === year);
    const [kpiKey, setKpiKey] = useState<string | null>(null);
    const [tab, setTab] = useState<string | null>(null);

    const kpiMap = useMemo(() => new Map((kpis ?? []).map((k) => [k.key, k])), [kpis]);
    const counts = useMemo(() => {
        const out = new Map<string, number>();
        for (const v of values ?? []) out.set(v.kpi_key, (out.get(v.kpi_key) ?? 0) + 1);
        return out;
    }, [values]);
    const selectData = useMemo(() => {
        const groups = new Map<string, { value: string; label: string }[]>();
        for (const k of [...(kpis ?? [])].sort((a, b) => a.sort_order - b.sort_order)) {
            const group = KPI_KIND_LABEL[k.kind] ?? k.kind;
            const n = counts.get(k.key) ?? 0;
            groups.set(group, [...(groups.get(group) ?? []), { value: k.key, label: `${k.name}${n ? ` (${n})` : ""}` }]);
        }
        return [...groups.entries()].map(([group, items]) => ({ group, items }));
    }, [kpis, counts]);

    if (kpisLoading || valuesLoading) return <Container py="xl"><Group justify="center"><Loader /></Group></Container>;
    if (isError || !values) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Fehler">
                    Den Infraplan {params.year} gibt es nicht oder die Kennzahlen konnten nicht geladen werden.
                </Alert>
            </Container>
        );
    }

    const unchecked = values.filter((v) => v.status === "UNGEPRUEFT").length;
    const activeTab = tab ?? (unchecked > 0 ? "approve" : "edit");
    const selected = kpiKey ? kpiMap.get(kpiKey) : undefined;

    return (
        <Container size="xl" py="xl">
            <Stack gap="lg">
                <Stack gap={2}>
                    <Anchor component={Link} to="/admin/infraplan-import" size="sm">← Infraplan-Import</Anchor>
                    <ChronicleHeadline as="h1">Kennzahlen Infraplan {year}</ChronicleHeadline>
                    <Text size="sm" c="dimmed">
                        {values.length} Werte · {unchecked} ungeprüft · öffentlich auf{" "}
                        <Anchor component={Link} to="/infraplan" size="sm">/infraplan</Anchor> erscheinen nur geprüfte
                        Werte.
                    </Text>
                </Stack>

                <Tabs value={activeTab} onChange={setTab}>
                    <Tabs.List>
                        <Tabs.Tab value="approve">
                            Freigabe{unchecked > 0 ? ` (${unchecked})` : ""}
                        </Tabs.Tab>
                        <Tabs.Tab value="edit">Erfassen</Tabs.Tab>
                    </Tabs.List>
                    <Tabs.Panel value="approve" pt="md">
                        <Approval
                            year={year}
                            values={values}
                            kpis={kpiMap}
                            parseResultId={report?.parse_result_id ?? null}
                        />
                    </Tabs.Panel>
                    <Tabs.Panel value="edit" pt="md">
                        <ChronicleCard>
                            <Stack gap="md">
                                <Select
                                    label="Kennzahl"
                                    placeholder="Kennzahl wählen…"
                                    data={selectData}
                                    value={kpiKey}
                                    onChange={setKpiKey}
                                    searchable
                                    w={{ base: "100%", sm: 480 }}
                                />
                                {selected ? (
                                    <KpiEditor key={selected.key} year={year} kpi={selected} values={values} />
                                ) : (
                                    <Text size="sm" c="dimmed">
                                        Wähle eine Kennzahl, um ihre Ist- und Zielwerte aus dem Infraplan {year}{" "}
                                        einzutragen (Jahr × Ist/Ziel × Teilreihe).
                                    </Text>
                                )}
                            </Stack>
                        </ChronicleCard>
                    </Tabs.Panel>
                </Tabs>
            </Stack>
        </Container>
    );
}

export default function InfraplanKpiPage() {
    return (
        <RequirePermission perm="infraplan.import">
            <InfraplanKpiPageContent />
        </RequirePermission>
    );
}
