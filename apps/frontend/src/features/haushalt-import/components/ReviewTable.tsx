import {
    ActionIcon,
    Badge,
    Box,
    Collapse,
    MultiSelect,
    Select,
    Stack,
    Table,
    Text,
    Title,
    Tooltip,
} from "@mantine/core";
import { useState } from "react";
import type { HaushaltsParseRow, Project } from "../../../shared/api/queries";

function fmt(val: number | null) {
    if (val === null) return "–";
    return val.toLocaleString("de-DE");
}

function fmtPct(val: number | null) {
    if (val === null) return "–";
    return val.toFixed(0) + " %";
}

function StatusBadge({ status }: { status: HaushaltsParseRow["status"] }) {
    const map = { new: "green", update: "yellow", unmatched: "red" } as const;
    const label = { new: "Neu", update: "Änd.", unmatched: "Unbek." } as const;
    return <Badge color={map[status]} variant="light" size="xs">{label[status]}</Badge>;
}

function SvBadge() {
    return (
        <Badge color="violet" variant="filled" size="xs" title="Sammelfinanzierungsvereinbarung">
            SV
        </Badge>
    );
}

// Column count for colSpan (main cols + optional Projektzuordnung)
function colCount(readonly: boolean | undefined) {
    // expand | Status | Lfd./FinVe/BP | Bezeichnung | [Projektzuordnung] | Aufn. | Urspr. | Vorjahr | Aktuell | Δabs | Δ% | Verausg. | Bewilligt | Ausgabereste | Veranschl. | Vorhalten
    return readonly ? 15 : 16;
}

type Props = {
    rows: HaushaltsParseRow[];
    projects: Project[];
    onProjectIdsChange: (finveNumber: number, projectIds: number[]) => void;
    readonly?: boolean;
};

function DataRow({
    row,
    projectOptions,
    onProjectIdsChange,
    readonly,
}: {
    row: HaushaltsParseRow;
    projectOptions: { value: string; label: string }[];
    onProjectIdsChange: Props["onProjectIdsChange"];
    readonly?: boolean;
}) {
    const [expanded, setExpanded] = useState(false);
    const b = row.proposed_budget;
    const year = b?.budget_year ?? 0;
    const hasTitel = row.proposed_titel_entries.length > 0;
    const span = colCount(readonly);

    const erlaeuterungProjects = row.erlaeuterung_projects ?? [];
    const hasSvSubrows = (row.is_sammel_finve ?? false) && erlaeuterungProjects.length > 0;

    // Per-subrow project assignment state — pre-filled from parser suggestions
    const suggestions = row.erlaeuterung_suggestions ?? [];
    const [subAssignments, setSubAssignments] = useState<(number | null)[]>(
        () => erlaeuterungProjects.map((_, i) => suggestions[i] ?? null)
    );

    // Extra project IDs added manually (not linked to a specific erlaeuterung subrow)
    const [extraIds, setExtraIds] = useState<number[]>([]);

    function _notifyChange(nextSub: (number | null)[], nextExtra: number[]) {
        const ids = [...new Set([
            ...nextSub.filter((id): id is number => id !== null),
            ...nextExtra,
        ])];
        onProjectIdsChange(row.finve_number, ids);
    }

    function handleSubAssign(idx: number, projectId: number | null) {
        const next = [...subAssignments];
        next[idx] = projectId;
        setSubAssignments(next);
        _notifyChange(next, extraIds);
    }

    function handleExtraChange(vals: string[]) {
        const next = vals.map(Number);
        setExtraIds(next);
        _notifyChange(subAssignments, next);
    }

    const suggestedSet = new Set((row.suggested_project_ids ?? []).map(String));
    const hasSuggestions = suggestedSet.size > 0;
    // Options with "✦" suffix for auto-suggested projects
    const annotatedOptions = projectOptions.map((opt) =>
        suggestedSet.has(opt.value)
            ? { ...opt, label: `${opt.label} ✦` }
            : opt
    );

    const regularTitel = row.proposed_titel_entries.filter((e) => !e.is_nachrichtlich);
    const nachrichtlich = row.proposed_titel_entries.filter((e) => e.is_nachrichtlich);

    return (
        <>
            <Table.Tr>
                {/* Expand toggle */}
                <Table.Td>
                    {hasTitel ? (
                        <ActionIcon
                            size="xs"
                            variant="subtle"
                            color="gray"
                            onClick={() => setExpanded((o) => !o)}
                            title="Mittelverteilung ein-/ausklappen"
                        >
                            {expanded ? "▲" : "▼"}
                        </ActionIcon>
                    ) : null}
                </Table.Td>

                <Table.Td>
                    <Stack gap={2}>
                        <StatusBadge status={row.status} />
                        {row.is_sammel_finve && <SvBadge />}
                    </Stack>
                </Table.Td>

                {/* Lfd. Nr. / FinVe / Bedarfsplan stacked */}
                <Table.Td style={{ whiteSpace: "nowrap" }}>
                    <Text size="xs" fw={600}>{b?.lfd_nr ?? "–"}</Text>
                    <Text size="xs" c="dimmed">{row.finve_number}</Text>
                    <Text size="xs" c="dimmed">{b?.bedarfsplan_number ?? "–"}</Text>
                </Table.Td>

                <Table.Td style={{ minWidth: 200 }}>
                    <Text size="xs">{row.name}</Text>
                </Table.Td>

                {/* Projektzuordnung */}
                {!readonly && (
                    <Table.Td style={{ minWidth: 320 }}>
                        {(row.status === "new" || row.status === "update") ? (
                            hasSvSubrows ? (
                                // SV rows with subrows: show count summary only
                                <Text size="xs" c="dimmed">
                                    {subAssignments.filter(Boolean).length} / {erlaeuterungProjects.length} zugeordnet
                                </Text>
                            ) : (
                                <Stack gap={4}>
                                    <MultiSelect
                                        data={annotatedOptions}
                                        value={row.project_ids.map(String)}
                                        onChange={(vals) =>
                                            onProjectIdsChange(row.finve_number, vals.map(Number))
                                        }
                                        placeholder="Projekte wählen..."
                                        searchable
                                        size="xs"
                                        style={{ width: "100%" }}
                                    />
                                    {hasSuggestions && row.status === "new" && (
                                        <Tooltip label="Automatischer Vorschlag basierend auf Namensähnlichkeit. ✦ markiert Vorschläge in der Liste." withArrow>
                                            <Badge
                                                color="blue"
                                                variant="light"
                                                size="xs"
                                                style={{ cursor: "default", width: "fit-content" }}
                                            >
                                                Auto-Vorschlag
                                            </Badge>
                                        </Tooltip>
                                    )}
                                </Stack>
                            )
                        ) : (
                            <Text size="xs" c="dimmed">
                                {row.project_ids.length > 0
                                    ? `${row.project_ids.length} Proj.`
                                    : "–"}
                            </Text>
                        )}
                    </Table.Td>
                )}

                {/* Aufnahme Jahr */}
                <Table.Td ta="right">
                    <Text size="xs">{row.proposed_finve?.starting_year ?? "–"}</Text>
                </Table.Td>

                {/* Voraussichtliche Gesamtausgaben */}
                <Table.Td ta="right"><Text size="xs">{fmt(b?.cost_estimate_original ?? null)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{fmt(b?.cost_estimate_last_year ?? null)}</Text></Table.Td>
                <Table.Td ta="right" fw={600}><Text size="xs" fw={600}>{fmt(b?.cost_estimate_actual ?? null)}</Text></Table.Td>

                {/* Gesamtausgabenentwicklung */}
                <Table.Td ta="right"><Text size="xs">{fmt(b?.delta_previous_year ?? null)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{fmtPct(b?.delta_previous_year_relativ ?? null)}</Text></Table.Td>

                {/* Ausgaben */}
                <Table.Td ta="right"><Text size="xs">{fmt(b?.spent_two_years_previous ?? null)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{fmt(b?.allowed_previous_year ?? null)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{fmt(b?.spending_residues ?? null)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{fmt(b?.year_planned ?? null)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{fmt(b?.next_years ?? null)}</Text></Table.Td>
            </Table.Tr>

            {/* Collapsible detail row: Haushaltstiteln + nachrichtlich (EVU/Dritte) */}
            {/* SV subrows: one per Erläuterung project name */}
            {hasSvSubrows && !readonly && erlaeuterungProjects.map((projectName, idx) => (
                <Table.Tr
                    key={`sv-sub-${idx}`}
                    style={{ background: "var(--mantine-color-violet-0)" }}
                >
                    <Table.Td />
                    <Table.Td />
                    <Table.Td />
                    <Table.Td style={{ whiteSpace: "normal", paddingLeft: 20 }}>
                        <Text size="xs" c="dimmed" style={{ lineHeight: 1.4 }}>
                            ↳ {projectName}
                        </Text>
                    </Table.Td>
                    <Table.Td style={{ minWidth: 280 }}>
                        <Select
                            data={projectOptions}
                            value={subAssignments[idx] !== null ? String(subAssignments[idx]) : null}
                            onChange={(val) => handleSubAssign(idx, val ? Number(val) : null)}
                            placeholder="Projekt suchen & zuordnen..."
                            searchable
                            clearable
                            size="xs"
                            style={{ width: "100%" }}
                            leftSection={suggestions[idx] != null && subAssignments[idx] === suggestions[idx]
                                ? <Text size="xs" c="blue">✦</Text>
                                : undefined}
                        />
                    </Table.Td>
                    <Table.Td colSpan={11} />
                </Table.Tr>
            ))}

            {/* Extra projects row: allows adding projects not mentioned in Erläuterung */}
            {hasSvSubrows && !readonly && (
                <Table.Tr style={{ background: "var(--mantine-color-violet-0)" }}>
                    <Table.Td />
                    <Table.Td />
                    <Table.Td />
                    <Table.Td style={{ whiteSpace: "normal", paddingLeft: 20 }}>
                        <Text size="xs" c="dimmed" fs="italic">+ weitere Projekte</Text>
                    </Table.Td>
                    <Table.Td style={{ minWidth: 280 }}>
                        <MultiSelect
                            data={projectOptions}
                            value={extraIds.map(String)}
                            onChange={handleExtraChange}
                            placeholder="Weitere Projekte manuell hinzufügen..."
                            searchable
                            clearable
                            size="xs"
                            style={{ width: "100%" }}
                        />
                    </Table.Td>
                    <Table.Td colSpan={11} />
                </Table.Tr>
            )}

            {hasTitel && (
                <Table.Tr>
                    <Table.Td colSpan={span} p={0}>
                        <Collapse in={expanded}>
                            <Box p="xs" style={{ background: "var(--mantine-color-gray-0)" }}>
                                {regularTitel.length > 0 && (
                                    <Stack gap={4} mb={nachrichtlich.length > 0 ? "xs" : 0}>
                                        <Text size="xs" fw={600} c="dimmed">
                                            Mittelverteilung Haushaltstiteln (T€)
                                        </Text>
                                        <Table withColumnBorders fz="xs" style={{ tableLayout: "auto" }}>
                                            <Table.Thead>
                                                <Table.Tr>
                                                    <Table.Th>Kapitel / Titel</Table.Th>
                                                    <Table.Th ta="right">Vorjahr</Table.Th>
                                                    <Table.Th ta="right">Aktuell</Table.Th>
                                                    <Table.Th ta="right">Verausgabt bis {year - 1}</Table.Th>
                                                    <Table.Th ta="right">Bewilligt {year}</Table.Th>
                                                    <Table.Th ta="right">Ausgabereste</Table.Th>
                                                    <Table.Th ta="right">Veranschlagt {year}</Table.Th>
                                                    <Table.Th ta="right">Vorhalten {year + 1} ff.</Table.Th>
                                                </Table.Tr>
                                            </Table.Thead>
                                            <Table.Tbody>
                                                {regularTitel.map((e, i) => (
                                                    <Table.Tr key={i}>
                                                        <Table.Td>
                                                            <Text size="xs">
                                                                {e.kapitel
                                                                    ? `Kap. ${e.kapitel}, Titel ${e.titel_nr}`
                                                                    : e.label}
                                                            </Text>
                                                        </Table.Td>
                                                        <Table.Td ta="right">{fmt(e.cost_estimate_last_year)}</Table.Td>
                                                        <Table.Td ta="right">{fmt(e.cost_estimate_aktuell)}</Table.Td>
                                                        <Table.Td ta="right">{fmt(e.verausgabt_bis)}</Table.Td>
                                                        <Table.Td ta="right">{fmt(e.bewilligt)}</Table.Td>
                                                        <Table.Td ta="right">{fmt(e.ausgabereste_transferred)}</Table.Td>
                                                        <Table.Td ta="right">{fmt(e.veranschlagt)}</Table.Td>
                                                        <Table.Td ta="right">{fmt(e.vorhalten_future)}</Table.Td>
                                                    </Table.Tr>
                                                ))}
                                            </Table.Tbody>
                                        </Table>
                                    </Stack>
                                )}

                                {nachrichtlich.length > 0 && (
                                    <Stack gap={4}>
                                        <Text size="xs" fw={600} c="dimmed">
                                            Nachrichtlich: EVU / Dritte (T€)
                                        </Text>
                                        <Table withColumnBorders fz="xs" style={{ tableLayout: "auto" }}>
                                            <Table.Thead>
                                                <Table.Tr>
                                                    <Table.Th>Bezeichnung</Table.Th>
                                                    <Table.Th ta="right">Vorjahr</Table.Th>
                                                    <Table.Th ta="right">Aktuell</Table.Th>
                                                    <Table.Th ta="right">Verausgabt bis {year - 1}</Table.Th>
                                                    <Table.Th ta="right">Bewilligt {year}</Table.Th>
                                                    <Table.Th ta="right">Ausgabereste</Table.Th>
                                                    <Table.Th ta="right">Veranschlagt {year}</Table.Th>
                                                    <Table.Th ta="right">Vorhalten {year + 1} ff.</Table.Th>
                                                </Table.Tr>
                                            </Table.Thead>
                                            <Table.Tbody>
                                                {nachrichtlich.map((e, i) => (
                                                    <Table.Tr key={i}>
                                                        <Table.Td>
                                                            <Text size="xs">{e.label}</Text>
                                                        </Table.Td>
                                                        <Table.Td ta="right">{fmt(e.cost_estimate_last_year)}</Table.Td>
                                                        <Table.Td ta="right">{fmt(e.cost_estimate_aktuell)}</Table.Td>
                                                        <Table.Td ta="right">{fmt(e.verausgabt_bis)}</Table.Td>
                                                        <Table.Td ta="right">{fmt(e.bewilligt)}</Table.Td>
                                                        <Table.Td ta="right">{fmt(e.ausgabereste_transferred)}</Table.Td>
                                                        <Table.Td ta="right">{fmt(e.veranschlagt)}</Table.Td>
                                                        <Table.Td ta="right">{fmt(e.vorhalten_future)}</Table.Td>
                                                    </Table.Tr>
                                                ))}
                                            </Table.Tbody>
                                        </Table>
                                    </Stack>
                                )}
                            </Box>
                        </Collapse>
                    </Table.Td>
                </Table.Tr>
            )}
        </>
    );
}

function RowGroup({
    title,
    rows,
    projects,
    onProjectIdsChange,
    readonly,
}: {
    title: string;
    rows: HaushaltsParseRow[];
    projects: Project[];
    onProjectIdsChange: Props["onProjectIdsChange"];
    readonly?: boolean;
}) {
    if (rows.length === 0) return null;

    // Use the year from the first row for dynamic column headers
    const year = rows[0]?.proposed_budget?.budget_year ?? 0;

    const projectOptions = projects.map((p) => ({
        value: String(p.id),
        label: `${p.project_number ?? p.id} – ${p.name}`,
    }));

    return (
        <Stack gap="xs">
            <Title order={5}>{title} ({rows.length})</Title>
            <Box style={{ overflowX: "auto" }}>
                <Table
                    withTableBorder
                    withColumnBorders
                    fz="xs"
                    style={{ minWidth: 1400, whiteSpace: "nowrap" }}
                >
                    <Table.Thead>
                        {/* Group header */}
                        <Table.Tr>
                            <Table.Th rowSpan={2} />
                            <Table.Th rowSpan={2}>Status</Table.Th>
                            <Table.Th rowSpan={2}>Lfd.Nr. / FinVe / BP</Table.Th>
                            <Table.Th rowSpan={2}>Bezeichnung</Table.Th>
                            {!readonly && <Table.Th rowSpan={2}>Projektzuordnung</Table.Th>}
                            <Table.Th rowSpan={2}>Aufn.</Table.Th>
                            <Table.Th colSpan={4} ta="center" style={{ borderBottom: "none" }}>
                                Voraussichtl. Gesamtausgaben (T€)
                            </Table.Th>
                            <Table.Th colSpan={2} ta="center" style={{ borderBottom: "none" }}>
                                Entwicklung z. Vorjahr
                            </Table.Th>
                            <Table.Th colSpan={5} ta="center" style={{ borderBottom: "none" }}>
                                Ausgaben (T€)
                            </Table.Th>
                        </Table.Tr>
                        <Table.Tr>
                            <Table.Th ta="right">Ursprüngl.</Table.Th>
                            <Table.Th ta="right">Vorjahr</Table.Th>
                            <Table.Th ta="right">Aktuell</Table.Th>
                            <Table.Th ta="right">Δ (T€)</Table.Th>
                            <Table.Th ta="right">Δ %</Table.Th>
                            <Table.Th ta="right">Verausgabt bis {year - 1}</Table.Th>
                            <Table.Th ta="right">Bewilligt {year}</Table.Th>
                            <Table.Th ta="right">Ausgabereste</Table.Th>
                            <Table.Th ta="right">Veranschl. {year}</Table.Th>
                            <Table.Th ta="right">Vorhalten {year + 1} ff.</Table.Th>
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        {rows.map((row) => (
                            <DataRow
                                key={row.finve_number}
                                row={row}
                                projectOptions={projectOptions}
                                onProjectIdsChange={onProjectIdsChange}
                                readonly={readonly}
                            />
                        ))}
                    </Table.Tbody>
                </Table>
            </Box>
        </Stack>
    );
}

export function ReviewTable({ rows, projects, onProjectIdsChange, readonly }: Props) {
    const regularNew    = rows.filter((r) => r.status === "new"    && !r.is_sammel_finve);
    const regularUpdate = rows.filter((r) => r.status === "update" && !r.is_sammel_finve);
    const svRows        = rows.filter((r) => r.is_sammel_finve ?? false);
    const unmatchedRows = rows.filter((r) => r.status === "unmatched");

    return (
        <Stack gap="xl">
            <RowGroup
                title="Neue FinVes"
                rows={regularNew}
                projects={projects}
                onProjectIdsChange={onProjectIdsChange}
                readonly={readonly}
            />
            <RowGroup
                title="Geänderte FinVes"
                rows={regularUpdate}
                projects={projects}
                onProjectIdsChange={onProjectIdsChange}
                readonly={readonly}
            />
            {svRows.length > 0 && (
                <Stack gap="xs">
                    <Text size="sm" c="dimmed">
                        Sammelfinanzierungsvereinbarungen – bitte Projekte manuell zuordnen
                    </Text>
                    <RowGroup
                        title="Sammel-FinVes (Phase 2)"
                        rows={svRows}
                        projects={projects}
                        onProjectIdsChange={onProjectIdsChange}
                        readonly={readonly}
                    />
                </Stack>
            )}
            <RowGroup
                title="Unbekannte Zeilen"
                rows={unmatchedRows}
                projects={projects}
                onProjectIdsChange={onProjectIdsChange}
                readonly={readonly}
            />
        </Stack>
    );
}
