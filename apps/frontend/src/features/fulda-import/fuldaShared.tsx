import { useMemo } from "react";
import {
    ActionIcon,
    Badge,
    Group,
    MultiSelect,
    Stack,
    Table,
    Text,
    Title,
} from "@mantine/core";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { IconTrash } from "@tabler/icons-react";

import {
    useDeleteFuldaEntry,
    useUpdateFuldaEntry,
    type FuldaEntry,
    type Project,
} from "../../shared/api/queries";
import { filterProjectOption } from "../../lib/filterProjectOption";
import {
    ConfirmBadge,
    MissingProjectAnchor,
    SavingIndicator,
    usePatchWithToast,
} from "../import-review/shared";

// Fixed display order of the category tables (mirrors services/fulda_categories.py):
// current state first, then announcements.
export const CATEGORY_ORDER = [
    "IN_LPH_1_2",
    "IN_LPH_3_4",
    "HAS_BAUFINVE",
    "COMPLETED_LPH_1_2_NO_FOLLOWUP",
    "COMPLETED_LPH_3_4_NO_FOLLOWUP",
    "COMPLETES_LPH_1",
    "COMPLETES_LPH_2",
    "COMPLETES_LPH_3_4",
    "NEW_LPH_1_2",
    "NEW_LPH_3_4",
    "NEW_BAUFINVE",
] as const;

export const CATEGORY_LABEL: Record<string, string> = {
    IN_LPH_1_2: "Aktuell in der Sammel-FinVe Lph 1/2",
    IN_LPH_3_4: "Aktuell in der Sammel-FinVe Lph 3/4",
    HAS_BAUFINVE: "Mit Baufinanzierungsvereinbarung",
    COMPLETED_LPH_1_2_NO_FOLLOWUP: "Lph 1/2 abgeschlossen, keine Aufnahme in Lph 3/4",
    COMPLETED_LPH_3_4_NO_FOLLOWUP: "Lph 3/4 abgeschlossen, keine Bau-FinVe",
    COMPLETES_LPH_1: "Abschluss Lph 1 angekündigt (nur Hinweis)",
    COMPLETES_LPH_2: "Abschluss Lph 2 bzw. 1/2 angekündigt",
    COMPLETES_LPH_3_4: "Abschluss Lph 3/4 angekündigt",
    NEW_LPH_1_2: "Neuaufnahme Lph 1/2 geplant",
    NEW_LPH_3_4: "Neuaufnahme Lph 3/4 geplant",
    NEW_BAUFINVE: "Bau-FinVe geplant",
};

// What a category does to the planning state (statement kind → effect).
export const KIND_LABEL: Record<string, { label: string; color: string }> = {
    IST: { label: "Ist · setzt Phase", color: "blue" },
    OHNE_FOLGEPHASE: { label: "Ist · ohne Folgephase", color: "orange" },
    PROGNOSE: { label: "Prognose · nur Termin", color: "grape" },
    NEUAUFNAHME: { label: "Neuaufnahme · nur Termin", color: "grape" },
};

export const ANSWER_STATUS_LABEL: Record<string, string> = {
    VOLLSTAENDIG: "vollständig",
    TEILWEISE: "teilweise beantwortet",
    OHNE_ERGEBNIS: "ohne Ergebnis",
};

export type ProjectOption = { value: string; label: string };

const GENERIC_ABSCHNITT = new Set(["", "gesamtstrecke", "gesamtprojekt", "gesamtmaßnahme"]);

/** Best default name for a missing project: the concrete Abschnitt if any, else the raw project. */
function draftName(entry: FuldaEntry): string {
    const abschnitt = (entry.abschnitt ?? "").trim();
    if (abschnitt && !GENERIC_ABSCHNITT.has(abschnitt.toLowerCase())) {
        return `${entry.raw_name} – ${abschnitt}`;
    }
    return entry.raw_name;
}

/** Group a year's entries into the fixed category buckets (+ an "other" bucket). */
export function bucketByCategory(rows: FuldaEntry[]) {
    const map = new Map<string, FuldaEntry[]>();
    for (const cat of CATEGORY_ORDER) map.set(cat, []);
    const other: FuldaEntry[] = [];
    for (const e of rows) {
        const list = e.category ? map.get(e.category) : undefined;
        if (list) list.push(e);
        else other.push(e);
    }
    return { map, other };
}

export function FuldaRow({
    entry,
    projectOptions,
}: {
    entry: FuldaEntry;
    projectOptions: ProjectOption[];
}) {
    const update = useUpdateFuldaEntry();
    const remove = useDeleteFuldaEntry();
    const patch = usePatchWithToast(update, entry.id);

    // The phase is implied by the table (category), so there is no per-row phase
    // picker — confirming only needs at least one assigned project/subproject.
    const canConfirm = entry.project_ids.length > 0;

    return (
        <Table.Tr>
            <Table.Td style={{ wordBreak: "break-word" }}>
                <Stack gap={2}>
                    <Text size="sm" fw={500}>
                        {entry.raw_name}
                    </Text>
                    <Text size="xs" c="dimmed">
                        {[
                            entry.drucksache ? `Drs. ${entry.drucksache}` : null,
                            entry.question_ref,
                            entry.page != null ? `S. ${entry.page}` : null,
                            entry.attributed_to === "DB" ? "Angabe der DB" : null,
                        ]
                            .filter(Boolean)
                            .join(" · ")}
                    </Text>
                    {entry.raw_text && (
                        <Text size="xs" c="dimmed" fs="italic" lineClamp={3} title={entry.raw_text}>
                            „{entry.raw_text}“
                        </Text>
                    )}
                </Stack>
            </Table.Td>
            <Table.Td style={{ wordBreak: "break-word" }}>
                <Stack gap={2}>
                    <Text size="sm" c={entry.abschnitt ? undefined : "dimmed"}>
                        {entry.abschnitt ?? "—"}
                    </Text>
                    {entry.expected_date && (
                        <Text size="xs" c="grape">
                            Termin: {new Date(entry.expected_date).toLocaleDateString("de-DE")}
                        </Text>
                    )}
                </Stack>
            </Table.Td>
            <Table.Td style={{ width: "36%" }}>
                <Stack gap={4}>
                    <MultiSelect
                        placeholder={entry.project_ids.length ? undefined : "Projekt / Unterprojekt zuordnen …"}
                        data={projectOptions}
                        value={entry.project_ids.map(String)}
                        onChange={(vs) => patch({ project_ids: vs.map(Number) })}
                        searchable
                        clearable
                        hidePickedOptions
                        filter={filterProjectOption}
                        nothingFoundMessage="Kein Projekt gefunden"
                    />
                    {entry.assignment_note && (
                        <Text size="xs" c="dimmed">
                            {entry.assignment_note}
                        </Text>
                    )}
                    <MissingProjectAnchor
                        alignSelfStart
                        initialName={draftName(entry)}
                        sourceLabel="Fulda-Runde"
                        onCreated={(project: Project) => {
                            if (project.id == null) return;
                            patch({ project_ids: [...entry.project_ids, project.id] });
                        }}
                    />
                </Stack>
            </Table.Td>
            <Table.Td>
                <Group gap="xs" wrap="nowrap">
                    <ConfirmBadge
                        confirmed={entry.confirmed}
                        canConfirm={canConfirm}
                        onToggle={() => patch({ confirmed: !entry.confirmed })}
                        blockedTitle="Mind. ein Projekt zuordnen"
                    />
                    {update.isPending ? (
                        <SavingIndicator />
                    ) : (
                        <ActionIcon
                            variant="subtle"
                            color="red"
                            onClick={() => remove.mutate(entry.id)}
                            title="Eintrag löschen"
                        >
                            <IconTrash size={16} />
                        </ActionIcon>
                    )}
                </Group>
            </Table.Td>
        </Table.Tr>
    );
}

export function PhaseTable({
    category,
    rows,
    projectOptions,
}: {
    category: string;
    rows: FuldaEntry[];
    projectOptions: ProjectOption[];
}) {
    const confirmed = useMemo(() => rows.filter((r) => r.confirmed).length, [rows]);
    const kind = rows[0]?.statement_kind ? KIND_LABEL[rows[0].statement_kind] : undefined;
    return (
        <Stack gap={6}>
            <Group gap="xs">
                <Title order={5}>{CATEGORY_LABEL[category] ?? category}</Title>
                {kind && (
                    <Badge variant="outline" color={kind.color}>
                        {kind.label}
                    </Badge>
                )}
                <Badge variant="light" color={rows.length ? "blue" : "gray"}>
                    {rows.length}
                </Badge>
                {rows.length > 0 && (
                    <Badge variant="light" color="green">
                        {confirmed} aktiv
                    </Badge>
                )}
            </Group>
            {rows.length === 0 ? (
                <Text size="sm" c="dimmed" pl={4}>
                    Keine Projekte in dieser Kategorie.
                </Text>
            ) : (
                <ResponsiveTable minWidth={640} striped highlightOnHover layout="fixed" w="100%" verticalSpacing="sm">
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th style={{ width: "28%" }}>Projekt (Wortlaut, Fundstelle)</Table.Th>
                            <Table.Th style={{ width: "24%" }}>Abschnitt → Unterprojekt</Table.Th>
                            <Table.Th style={{ width: "36%" }}>Projekte zuordnen</Table.Th>
                            <Table.Th style={{ width: "12%" }}>Übernehmen</Table.Th>
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        {rows.map((entry) => (
                            <FuldaRow key={entry.id} entry={entry} projectOptions={projectOptions} />
                        ))}
                    </Table.Tbody>
                </ResponsiveTable>
            )}
        </Stack>
    );
}
