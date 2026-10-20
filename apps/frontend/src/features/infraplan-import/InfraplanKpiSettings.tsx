import { useMemo, useState } from "react";
import {
    Autocomplete,
    Badge,
    Button,
    Group,
    Loader,
    Modal,
    NumberInput,
    Select,
    Stack,
    Switch,
    Table,
    Text,
    TextInput,
    Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
    useInfraplanKpis,
    useInfraplanPublicKpis,
    useUpdateInfraplanKpi,
    type InfraplanKpi,
    type InfraplanKpiUpdate,
} from "../../shared/api/queries";
import { useIsMobile } from "../../shared/hooks/useBreakpoint";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { KPI_CATEGORY_LABEL, KPI_KIND_LABEL } from "../infraplan/infraplanFormat";

const LAYOUT_OPTIONS = [
    { value: "", label: "Automatisch" },
    { value: "split", label: "Ein Diagramm je Teilreihe" },
    { value: "grouped", label: "Balken nebeneinander" },
    { value: "flow", label: "Herkunft/Einsatz (ein Jahr)" },
];
const LAYOUT_LABEL = Object.fromEntries(LAYOUT_OPTIONS.map((o) => [o.value, o.label]));

const CATEGORY_OPTIONS = [
    { value: "", label: "Keine" },
    ...Object.entries(KPI_CATEGORY_LABEL).map(([value, label]) => ({ value, label })),
];

type Form = {
    name: string;
    unit: string;
    description: string;
    category: string;
    sort_order: number;
    chart_layout: string;
    total_series: string;
    companion_key: string;
    companion_label: string;
    zoomed_axis: boolean;
};

function toForm(k: InfraplanKpi): Form {
    return {
        name: k.name,
        unit: k.unit ?? "",
        description: k.description ?? "",
        category: k.category ?? "",
        sort_order: k.sort_order ?? 0,
        chart_layout: k.chart_layout ?? "",
        total_series: k.total_series ?? "",
        companion_key: k.companion_key ?? "",
        companion_label: k.companion_label ?? "",
        zoomed_axis: k.zoomed_axis ?? false,
    };
}

function toBody(f: Form): InfraplanKpiUpdate {
    const orNull = (v: string) => v.trim() || null;
    return {
        name: f.name.trim(),
        unit: orNull(f.unit),
        description: orNull(f.description),
        category: (orNull(f.category) as InfraplanKpiUpdate["category"]) ?? null,
        sort_order: f.sort_order,
        chart_layout: (orNull(f.chart_layout) as InfraplanKpiUpdate["chart_layout"]) ?? null,
        total_series: orNull(f.total_series),
        companion_key: orNull(f.companion_key),
        companion_label: orNull(f.companion_label),
        zoomed_axis: f.zoomed_axis,
    };
}

/** Short summary of the display settings for the table. */
function displaySummary(k: InfraplanKpi, names: Map<string, string>): string[] {
    const out: string[] = [];
    if (k.chart_layout) out.push(LAYOUT_LABEL[k.chart_layout] ?? k.chart_layout);
    if (k.total_series) out.push(`Übersicht: ${k.total_series}`);
    if (k.companion_key) out.push(`+ ${k.companion_label || names.get(k.companion_key) || k.companion_key} (rechte Skala)`);
    if (k.zoomed_axis) out.push("Skala ab Werten");
    return out;
}

function EditModal({ kpi, kpis, series, onClose }: {
    kpi: InfraplanKpi;
    kpis: InfraplanKpi[];
    series: string[];
    onClose: () => void;
}) {
    const isMobile = useIsMobile();
    const [form, setForm] = useState<Form>(() => toForm(kpi));
    const update = useUpdateInfraplanKpi();
    const set = <K extends keyof Form>(field: K, value: Form[K]) => setForm((f) => ({ ...f, [field]: value }));

    const companionOptions = [
        { value: "", label: "Keine" },
        ...kpis.filter((k) => k.key !== kpi.key).map((k) => ({ value: k.key, label: k.name })),
    ];

    const save = async () => {
        try {
            await update.mutateAsync({ key: kpi.key, body: toBody(form) });
            notifications.show({ color: "green", message: `${form.name} gespeichert.` });
            onClose();
        } catch (error) {
            notifications.show({ color: "red", message: error instanceof Error ? error.message : "Speichern fehlgeschlagen." });
        }
    };

    return (
        <Modal opened onClose={onClose} title={kpi.name} size="lg" fullScreen={isMobile}>
            <Stack gap="sm">
                <Text size="xs" c="dimmed">Schlüssel: {kpi.key}</Text>
                <TextInput label="Name" value={form.name} onChange={(e) => set("name", e.currentTarget.value)} required />
                <Group grow align="flex-start">
                    <TextInput
                        label="Einheit"
                        description="km und % stehen an der Achse, längere unter dem Titel"
                        value={form.unit}
                        onChange={(e) => set("unit", e.currentTarget.value)}
                    />
                    <Select
                        label="Kategorie"
                        data={CATEGORY_OPTIONS}
                        value={form.category}
                        onChange={(v) => set("category", v ?? "")}
                        allowDeselect={false}
                    />
                </Group>
                <Textarea
                    label="Beschreibung"
                    description="Kurze Erklärung der Kennzahl; auf /infraplan als Tooltip hinter dem Info-Symbol neben dem Namen"
                    autosize
                    minRows={2}
                    value={form.description}
                    onChange={(e) => set("description", e.currentTarget.value)}
                />
                <NumberInput
                    label="Reihenfolge"
                    value={form.sort_order}
                    onChange={(v) => set("sort_order", typeof v === "number" ? v : 0)}
                    allowDecimal={false}
                    w={160}
                />

                <Text fw={600} size="sm" mt="sm">Darstellung auf /infraplan</Text>
                <Select
                    label="Diagrammart"
                    description="Automatisch: gestapelt; mit Zielwerten je Teilreihe die Summe und „Details“ je Teilreihe"
                    data={LAYOUT_OPTIONS}
                    value={form.chart_layout}
                    onChange={(v) => set("chart_layout", v ?? "")}
                    allowDeselect={false}
                />
                <Autocomplete
                    label="Teilreihe für die Übersicht"
                    description="Wenn eine Teilreihe schon das Ganze ist (z. B. „Gesamtnetz“); die übrigen gehen in „Details“"
                    data={series}
                    value={form.total_series}
                    onChange={(v) => set("total_series", v)}
                />
                <Group grow align="flex-start">
                    <Select
                        label="Begleitkennzahl"
                        description="Zweiter Balken auf eigener Skala rechts; sie bekommt keine eigene Karte"
                        data={companionOptions}
                        value={form.companion_key}
                        onChange={(v) => set("companion_key", v ?? "")}
                        searchable
                        allowDeselect={false}
                    />
                    <TextInput
                        label="Bezeichnung der Begleitkennzahl"
                        description="Leer: Name der Begleitkennzahl"
                        value={form.companion_label}
                        onChange={(e) => set("companion_label", e.currentTarget.value)}
                        disabled={!form.companion_key}
                    />
                </Group>
                <Switch
                    label="Skala beginnt knapp unter den Werten statt bei 0"
                    description="Für Werte in einem schmalen Band, z. B. Quoten nahe 100 %"
                    checked={form.zoomed_axis}
                    onChange={(e) => set("zoomed_axis", e.currentTarget.checked)}
                />
                <Group justify="flex-end" mt="md">
                    <Button variant="default" onClick={onClose}>Abbrechen</Button>
                    <Button onClick={save} loading={update.isPending} disabled={!form.name.trim()}>
                        Speichern
                    </Button>
                </Group>
            </Stack>
        </Modal>
    );
}

/** Admin → Infraplan → Allgemeines: KPI definitions and how /infraplan draws them. */
export default function InfraplanKpiSettings() {
    const { data: kpis, isLoading } = useInfraplanKpis();
    const { data: publicKpis } = useInfraplanPublicKpis();
    const [editing, setEditing] = useState<string | null>(null);

    const names = useMemo(() => new Map((kpis ?? []).map((k) => [k.key, k.name])), [kpis]);
    const seriesByKey = useMemo(() => {
        const out = new Map<string, string[]>();
        for (const k of publicKpis ?? []) {
            out.set(k.key, [...new Set((k.values ?? []).map((v) => v.series).filter((s): s is string => !!s))]);
        }
        return out;
    }, [publicKpis]);

    if (isLoading) return <Group justify="center"><Loader /></Group>;
    const list = kpis ?? [];
    const current = list.find((k) => k.key === editing);

    return (
        <Stack gap="sm">
            <Text size="sm" c="dimmed">
                Name, Einheit und Darstellung der Kennzahlen auf der öffentlichen Seite Infraplan. Änderungen gelten sofort
                für alle Jahrgänge.
            </Text>
            <ResponsiveTable minWidth={760} striped withTableBorder verticalSpacing="xs" fz="sm">
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Kennzahl</Table.Th>
                        <Table.Th>Einheit</Table.Th>
                        <Table.Th>Darstellung</Table.Th>
                        <Table.Th />
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {list.map((k) => (
                        <Table.Tr key={k.key}>
                            <Table.Td style={{ maxWidth: 340 }}>
                                {k.name}
                                <Text size="xs" c="dimmed">
                                    {KPI_KIND_LABEL[k.kind] ?? k.kind}
                                    {k.category ? ` · ${KPI_CATEGORY_LABEL[k.category] ?? k.category}` : ""}
                                </Text>
                            </Table.Td>
                            <Table.Td>{k.unit ?? <Text span size="sm" c="dimmed">–</Text>}</Table.Td>
                            <Table.Td>
                                <Group gap={4}>
                                    {displaySummary(k, names).map((d) => (
                                        <Badge key={d} variant="light" size="sm" tt="none">{d}</Badge>
                                    ))}
                                    {displaySummary(k, names).length === 0 && <Text size="xs" c="dimmed">Automatisch</Text>}
                                </Group>
                            </Table.Td>
                            <Table.Td ta="right">
                                <Button size="compact-xs" variant="light" onClick={() => setEditing(k.key)}>
                                    Bearbeiten
                                </Button>
                            </Table.Td>
                        </Table.Tr>
                    ))}
                </Table.Tbody>
            </ResponsiveTable>
            {current && (
                <EditModal
                    key={current.key}
                    kpi={current}
                    kpis={list}
                    series={seriesByKey.get(current.key) ?? []}
                    onClose={() => setEditing(null)}
                />
            )}
        </Stack>
    );
}
