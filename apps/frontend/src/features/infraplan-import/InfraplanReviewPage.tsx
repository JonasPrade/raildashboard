import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
    ActionIcon,
    Alert,
    Anchor,
    Badge,
    Button,
    Chip,
    Container,
    Group,
    List,
    Loader,
    Menu,
    Modal,
    MultiSelect,
    Pagination,
    Stack,
    Switch,
    Table,
    Text,
    TextInput,
    Tooltip,
} from "@mantine/core";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import { IconDotsVertical } from "@tabler/icons-react";
import { ChronicleCard, ChronicleHeadline } from "../../components/chronicle";
import RequirePermission from "../../components/RequirePermission";
import { filterProjectOption } from "../../lib/filterProjectOption";
import { API_BASE } from "../../shared/api/client";
import {
    infraplanPageImageUrl,
    useApplyInfraplanSuggestions,
    useConfirmInfraplanImport,
    useCreateInfraplanSubproject,
    useInfraplanParseResult,
    usePatchInfraplanRow,
    useProjectOptions,
    type InfraplanParseResult,
    type InfraplanParsedRow,
} from "../../shared/api/queries";
import { formatDateTime } from "../../shared/format";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import ProjectSearchSelect from "../projects/ProjectSearchSelect";
import Footnotes from "../infraplan/Footnotes";
import {
    PARL_LABEL,
    REASON_LABEL,
    SECTION_SHORT,
    SOURCE_COLOR,
    SOURCE_LABEL,
    filterRows,
    formatConfidence,
    formatMio,
    isAssigned,
} from "../infraplan/infraplanFormat";

const PAGE_SIZE = 50;

function errorDetail(error: unknown, fallback: string): string {
    return (error as { details?: { detail?: string } } | undefined)?.details?.detail ?? fallback;
}

function CostCell({ row }: { row: InfraplanParsedRow }) {
    const kind = row.cost_kind === "GESAMTKOSTEN" ? "GK" : "GWU";
    if (row.cost_mio == null) {
        return (
            <Stack gap={0}>
                <Text size="sm" c="dimmed">{row.cost_ref_raw ?? row.cost_raw ?? "–"}</Text>
                {row.cost_ref?.resolved && row.cost_ref.cost_mio != null && (
                    <Text size="xs" c="dimmed">→ {formatMio(row.cost_ref.cost_mio)} (Verweis)</Text>
                )}
            </Stack>
        );
    }
    return (
        <Stack gap={0} align="flex-end">
            <Text size="sm" style={{ whiteSpace: "nowrap" }}>{formatMio(row.cost_mio)}</Text>
            <Text size="xs" c="dimmed">{kind}</Text>
        </Stack>
    );
}

type Option = { value: string; label: string };

function AssignCell({
    row,
    options,
    projects,
    readonly,
    onChange,
    saving,
}: {
    row: InfraplanParsedRow;
    options: Option[];
    projects: InfraplanParseResult["projects"];
    readonly: boolean;
    onChange: (ids: number[]) => void;
    saving: boolean;
}) {
    const current = row.project_ids ?? [];
    const open = (row.suggestions ?? []).filter((s) => !current.includes(s.project_id));
    return (
        <Stack gap={4}>
            <MultiSelect
                data={options}
                value={current.map(String)}
                onChange={(vals) => onChange(vals.map(Number))}
                placeholder={current.length ? undefined : "Projekt wählen…"}
                searchable
                filter={filterProjectOption}
                limit={30}
                size="xs"
                disabled={readonly || saving}
                aria-label={`Zuordnung lfd. Nr. ${row.lfd_nr}`}
            />
            {(row.assignment_source || open.length > 0) && (
                <Group gap={4} wrap="wrap">
                    {row.assignment_source && current.length > 0 && (
                        <Tooltip
                            label={[row.assignment_note, row.assigned_by ? `von ${row.assigned_by}` : null]
                                .filter(Boolean)
                                .join(" · ") || SOURCE_LABEL[row.assignment_source]}
                            multiline
                            w={280}
                            withArrow
                            events={{ hover: true, focus: true, touch: true }}
                        >
                            <Badge size="xs" variant="light" color={SOURCE_COLOR[row.assignment_source] ?? "gray"}>
                                {SOURCE_LABEL[row.assignment_source] ?? row.assignment_source}
                                {row.assignment_note ? " ⓘ" : ""}
                            </Badge>
                        </Tooltip>
                    )}
                    {!readonly &&
                        open.map((s) => {
                            const name = projects?.[String(s.project_id)]?.name ?? `Projekt ${s.project_id}`;
                            return (
                                <Tooltip
                                    key={s.project_id}
                                    label={`Vorschlag (${REASON_LABEL[s.reason] ?? s.reason}) übernehmen`}
                                    withArrow
                                >
                                    <Badge
                                        size="xs"
                                        variant="outline"
                                        color={s.confidence >= 0.85 ? "green" : "gray"}
                                        style={{ cursor: "pointer", textTransform: "none", maxWidth: 260 }}
                                        onClick={() => onChange([...current, s.project_id])}
                                    >
                                        ✦ {name} · {formatConfidence(s.confidence)}
                                    </Badge>
                                </Tooltip>
                            );
                        })}
                </Group>
            )}
        </Stack>
    );
}

function SubprojectModal({
    row,
    onClose,
    parseResultId,
}: {
    row: InfraplanParsedRow | null;
    onClose: () => void;
    parseResultId: number;
}) {
    const create = useCreateInfraplanSubproject(parseResultId);
    const [parentId, setParentId] = useState<number | null>(null);
    const [name, setName] = useState("");
    const [seededFor, setSeededFor] = useState<string | null>(null);

    // Re-seed whenever the dialog opens for another row.
    if (row && seededFor !== row.row_key) {
        setSeededFor(row.row_key);
        setName(row.massnahme ?? row.bezeichnung ?? "");
        setParentId(row.project_ids?.[0] ?? null);
    }

    const submit = async () => {
        if (!row || parentId === null) return;
        try {
            const result = await create.mutateAsync({ rowKey: row.row_key, parentId, name: name.trim() || null });
            notifications.show({
                color: "green",
                title: "Teilprojekt angelegt",
                message: `„${result.name}“ wurde angelegt und der Zeile zugeordnet.`,
            });
            onClose();
        } catch (error) {
            notifications.show({ color: "red", message: errorDetail(error, "Anlegen fehlgeschlagen.") });
        }
    };

    return (
        <Modal opened={row !== null} onClose={onClose} title="Teilprojekt anlegen unter …">
            <Stack gap="sm">
                {row && (
                    <Text size="sm" c="dimmed">
                        {SECTION_SHORT[row.section] ?? row.section} · lfd. Nr. {row.lfd_nr}
                        {row.primary_number ? ` · ${row.primary_number}` : ""}
                    </Text>
                )}
                <ProjectSearchSelect
                    label="Übergeordnetes Projekt"
                    description="Unter diesem Projekt wird das Teilprojekt angelegt."
                    value={parentId}
                    onChange={setParentId}
                />
                <TextInput
                    label="Name des Teilprojekts"
                    description="Vorbelegt mit der Maßnahme der Zeile."
                    value={name}
                    onChange={(e) => setName(e.currentTarget.value)}
                />
                <Group justify="flex-end">
                    <Button variant="default" onClick={onClose}>Abbrechen</Button>
                    <Button onClick={submit} loading={create.isPending} disabled={parentId === null}>
                        Anlegen und zuordnen
                    </Button>
                </Group>
            </Stack>
        </Modal>
    );
}

function ConfirmBlock({ record }: { record: InfraplanParseResult }) {
    const confirm = useConfirmInfraplanImport();
    const [publishedOn, setPublishedOn] = useState("");
    const [title, setTitle] = useState(`Infraplan ${record.year}`);
    const warnings = record.warnings_json ?? [];
    const unassigned = record.row_count != null ? record.row_count - record.assigned_count : null;

    const run = async (force: boolean) => {
        try {
            const result = await confirm.mutateAsync({
                parse_result_id: record.id,
                published_on: publishedOn || null,
                title: title.trim() || null,
                force,
            });
            notifications.show({
                color: "green",
                title: `Infraplan ${result.year} übernommen`,
                message: `${result.entries} Einträge, ${result.links} Zuordnungen, ${result.unassigned} ohne Projekt, ${result.projects_updated} Projekte aktualisiert.`,
            });
        } catch (error) {
            const detail = errorDetail(error, "Übernahme fehlgeschlagen.");
            const status = (error as { status?: number } | undefined)?.status;
            // Only parser warnings may be overridden — an existing year never.
            if (status === 409 && !force && detail.includes("Warnung")) {
                modals.openConfirmModal({
                    title: "Trotzdem übernehmen?",
                    children: (
                        <Text size="sm">
                            {detail} Wenn du die {warnings.length} Warnung(en) geprüft hast, kannst du den Entwurf
                            trotzdem übernehmen.
                        </Text>
                    ),
                    labels: { confirm: "Trotzdem übernehmen", cancel: "Abbrechen" },
                    confirmProps: { color: "orange" },
                    onConfirm: () => void run(true),
                });
                return;
            }
            notifications.show({ color: "red", title: "Übernahme fehlgeschlagen", message: detail, autoClose: false });
        }
    };

    return (
        <ChronicleCard>
            <Stack gap="sm">
                <Text fw={600}>Übernehmen</Text>
                <Text size="sm" c="dimmed">
                    Legt den Jahrgang {record.year} mit allen Zeilen an, verknüpft die zugeordneten Projekte und
                    aktualisiert deren Planungsstand.
                    {unassigned ? ` ${unassigned} Zeilen bleiben ohne Projekt und erscheinen unter „Offene Zuordnungen“.` : ""}
                </Text>
                {record.report_year_exists && (
                    <Alert color="red" variant="light">
                        Den Infraplan {record.year} gibt es bereits. Erst den Jahrgang auf der Import-Seite löschen.
                    </Alert>
                )}
                <Group align="flex-end" gap="sm" wrap="wrap">
                    <TextInput
                        type="date"
                        label="Veröffentlicht am"
                        value={publishedOn}
                        onChange={(e) => setPublishedOn(e.currentTarget.value)}
                        w={{ base: "100%", xs: 180 }}
                    />
                    <TextInput
                        label="Titel"
                        value={title}
                        onChange={(e) => setTitle(e.currentTarget.value)}
                        w={{ base: "100%", xs: 280 }}
                    />
                    <Button
                        onClick={() => void run(false)}
                        loading={confirm.isPending}
                        disabled={record.report_year_exists}
                    >
                        Übernehmen
                    </Button>
                </Group>
            </Stack>
        </ChronicleCard>
    );
}

function InfraplanReviewPageContent() {
    const { parseResultId } = useParams<{ parseResultId: string }>();
    const id = Number(parseResultId);
    const { data: record, isLoading, isError } = useInfraplanParseResult(id);
    const { data: projectOptions } = useProjectOptions();
    const patchRow = usePatchInfraplanRow(id);
    const applySuggestions = useApplyInfraplanSuggestions(id);

    const [section, setSection] = useState("ALL");
    const [onlyUnassigned, setOnlyUnassigned] = useState(false);
    const [search, setSearch] = useState("");
    const [page, setPage] = useState(1);
    const [savingRow, setSavingRow] = useState<string | null>(null);
    const [subprojectRow, setSubprojectRow] = useState<InfraplanParsedRow | null>(null);

    const options = useMemo(() => {
        const list: Option[] = (projectOptions ?? []).map((p) => ({
            value: String(p.id),
            label: `${p.project_number ?? "–"} – ${p.name}`,
        }));
        // A project created a moment ago may not be in the picker list yet.
        const known = new Set(list.map((o) => o.value));
        for (const p of Object.values(record?.projects ?? {})) {
            if (!known.has(String(p.id))) list.push({ value: String(p.id), label: p.name });
        }
        return list;
    }, [projectOptions, record?.projects]);

    const rows = useMemo(() => record?.result_json?.rows ?? [], [record]);
    const filtered = useMemo(
        () => filterRows(rows, { section, onlyUnassigned, search }),
        [rows, section, onlyUnassigned, search],
    );

    if (isLoading) return <Container py="xl"><Group justify="center"><Loader /></Group></Container>;
    if (isError || !record) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Fehler">Entwurf konnte nicht geladen werden.</Alert>
            </Container>
        );
    }
    if (record.status === "PENDING" || record.status === "RUNNING") {
        return (
            <Container size="sm" py="xl">
                <Group gap="sm"><Loader size="sm" /><Text>Der Infraplan {record.year} wird ausgelesen …</Text></Group>
            </Container>
        );
    }
    if (record.status !== "SUCCESS" || !record.result_json) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Auslesen fehlgeschlagen">
                    {record.error_message ?? "Der Entwurf hat kein Ergebnis."}{" "}
                    <Anchor component={Link} to="/admin/infraplan-import">Zurück zum Import</Anchor>
                </Alert>
            </Container>
        );
    }

    const confirmed = record.confirmed_at != null;
    const warnings = record.warnings_json ?? [];
    const sections = record.result_json.sections;
    const unassignedCount = rows.filter((r) => !isAssigned(r)).length;
    const pageRows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    const pageImage = (p: number) => infraplanPageImageUrl(record.id, p, API_BASE);

    const setProjects = (row: InfraplanParsedRow, ids: number[]) => {
        setSavingRow(row.row_key);
        patchRow.mutate(
            { rowKey: row.row_key, patch: { project_ids: ids } },
            {
                onError: (error) =>
                    notifications.show({ color: "red", message: errorDetail(error, "Zuordnung nicht gespeichert.") }),
                onSettled: () => setSavingRow(null),
            },
        );
    };

    const handleApply = async () => {
        try {
            const result = await applySuggestions.mutateAsync({ min_confidence: 0.85, only_unassigned: true });
            notifications.show({
                color: "green",
                message: `${result.applied} Vorschläge übernommen, ${result.unassigned} Zeilen noch ohne Projekt.`,
            });
        } catch (error) {
            notifications.show({ color: "red", message: errorDetail(error, "Vorschläge nicht übernommen.") });
        }
    };

    const changeFilter = (fn: () => void) => {
        fn();
        setPage(1);
    };

    return (
        <Container size="xl" py="xl">
            <Stack gap="lg">
                <Group justify="space-between" align="flex-end" wrap="wrap">
                    <Stack gap={2}>
                        <Anchor component={Link} to="/admin/infraplan-import" size="sm">← Infraplan-Import</Anchor>
                        <ChronicleHeadline as="h1">Infraplan {record.year}</ChronicleHeadline>
                        <Text size="sm" c="dimmed" style={{ overflowWrap: "anywhere" }}>
                            {record.file_name} · {record.assigned_count} von {record.row_count ?? rows.length} Zeilen
                            zugeordnet
                        </Text>
                    </Stack>
                    {!confirmed && (
                        <Button variant="light" onClick={handleApply} loading={applySuggestions.isPending}>
                            Vorschläge übernehmen (≥ 85 %)
                        </Button>
                    )}
                </Group>

                {confirmed && (
                    <Alert color="green" variant="light">
                        Übernommen am {formatDateTime(record.confirmed_at as string)}
                        {record.confirmed_by_snapshot ? ` von ${record.confirmed_by_snapshot}` : ""}. Der Entwurf ist
                        nur noch lesbar; Zuordnungen pflegst du jetzt unter{" "}
                        <Anchor component={Link} to="/admin/unassigned" size="sm">Offene Zuordnungen</Anchor>.
                    </Alert>
                )}

                {warnings.length > 0 && (
                    <Alert color="yellow" variant="light" title={`${warnings.length} Warnung(en) des Parsers`}>
                        <List size="sm" spacing={2}>
                            {warnings.map((w, i) => (
                                <List.Item key={`${w.kind}-${i}`}>
                                    {w.section ? `${SECTION_SHORT[w.section] ?? w.section}` : ""}
                                    {w.lfd_nr != null ? ` Nr. ${w.lfd_nr}` : ""}
                                    {w.section || w.lfd_nr != null ? ": " : ""}
                                    {w.message}
                                    {w.page != null && record.has_pdf && (
                                        <>
                                            {" "}
                                            <Anchor href={pageImage(w.page)} target="_blank" rel="noreferrer" size="sm">
                                                (S. {w.page})
                                            </Anchor>
                                        </>
                                    )}
                                </List.Item>
                            ))}
                        </List>
                        <Text size="xs" mt="xs">
                            Mit Warnungen lässt sich der Entwurf nur über „Trotzdem übernehmen“ bestätigen.
                        </Text>
                    </Alert>
                )}

                <ChronicleCard>
                    <Stack gap="sm">
                        <Chip.Group multiple={false} value={section} onChange={(v) => changeFilter(() => setSection(v))}>
                            <Group gap={6} wrap="wrap">
                                <Chip value="ALL" size="xs">Alle ({rows.length})</Chip>
                                {sections.map((s) => (
                                    <Tooltip key={s.key} label={s.title} withArrow>
                                        <div>
                                            <Chip value={s.key} size="xs">
                                                {SECTION_SHORT[s.key] ?? s.key} ({s.row_count})
                                            </Chip>
                                        </div>
                                    </Tooltip>
                                ))}
                            </Group>
                        </Chip.Group>
                        <Group gap="sm" wrap="wrap" align="center">
                            <TextInput
                                placeholder="Nummer, Bezeichnung, Maßnahme"
                                value={search}
                                onChange={(e) => {
                                    const v = e.currentTarget.value;
                                    changeFilter(() => setSearch(v));
                                }}
                                w={{ base: "100%", xs: 280 }}
                            />
                            <Switch
                                label={`nur ohne Zuordnung (${unassignedCount})`}
                                checked={onlyUnassigned}
                                onChange={(e) => {
                                    const v = e.currentTarget.checked;
                                    changeFilter(() => setOnlyUnassigned(v));
                                }}
                            />
                        </Group>

                        <ResponsiveTable minWidth={1280} striped withTableBorder verticalSpacing="xs">
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Nr.</Table.Th>
                                    <Table.Th>Projektnummer</Table.Th>
                                    <Table.Th>Bezeichnung / Maßnahme</Table.Th>
                                    <Table.Th>Stand</Table.Th>
                                    <Table.Th>IBN</Table.Th>
                                    <Table.Th ta="right">Kosten Mio. €</Table.Th>
                                    <Table.Th>Befassung</Table.Th>
                                    <Table.Th style={{ minWidth: 320 }}>Zuordnung</Table.Th>
                                    <Table.Th />
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {pageRows.map((row) => (
                                    <Table.Tr key={row.row_key}>
                                        <Table.Td style={{ whiteSpace: "nowrap" }}>
                                            <Text size="sm" fw={500}>{row.lfd_nr}</Text>
                                            <Text size="xs" c="dimmed">
                                                {SECTION_SHORT[row.section] ?? row.section}
                                                {" · "}
                                                {record.has_pdf ? (
                                                    <Anchor href={pageImage(row.page)} target="_blank" rel="noreferrer" size="xs">
                                                        S. {row.page}
                                                    </Anchor>
                                                ) : (
                                                    `S. ${row.page}`
                                                )}
                                            </Text>
                                        </Table.Td>
                                        <Table.Td style={{ whiteSpace: "nowrap" }}>
                                            <Text size="sm">{row.primary_number ?? "–"}</Text>
                                            {(row.project_numbers ?? []).length > 1 && (
                                                <Text size="xs" c="dimmed">
                                                    {(row.project_numbers ?? []).filter((n) => n !== row.primary_number).join(", ")}
                                                </Text>
                                            )}
                                        </Table.Td>
                                        <Table.Td style={{ maxWidth: 320 }}>
                                            <Text size="sm" fw={500}>
                                                {row.bezeichnung ?? "–"}
                                                <Footnotes footnotes={row.footnotes} />
                                            </Text>
                                            {row.massnahme && row.massnahme !== row.bezeichnung && (
                                                <Text size="xs">{row.massnahme}</Text>
                                            )}
                                            {row.laender && <Text size="xs" c="dimmed">{row.laender}</Text>}
                                        </Table.Td>
                                        <Table.Td style={{ maxWidth: 180 }}>
                                            <Text size="sm">{row.state_raw ?? "–"}</Text>
                                        </Table.Td>
                                        <Table.Td style={{ whiteSpace: "nowrap" }}>{row.ibn_raw ?? "–"}</Table.Td>
                                        <Table.Td ta="right"><CostCell row={row} /></Table.Td>
                                        <Table.Td style={{ maxWidth: 160 }}>
                                            <Text size="sm">
                                                {row.parl_state ? PARL_LABEL[row.parl_state] : (row.parl_raw ?? "–")}
                                            </Text>
                                            {row.parl_state && row.parl_raw && (
                                                <Text size="xs" c="dimmed">{row.parl_raw}</Text>
                                            )}
                                        </Table.Td>
                                        <Table.Td>
                                            <AssignCell
                                                row={row}
                                                options={options}
                                                projects={record.projects}
                                                readonly={confirmed}
                                                saving={savingRow === row.row_key}
                                                onChange={(ids) => setProjects(row, ids)}
                                            />
                                        </Table.Td>
                                        <Table.Td>
                                            {!confirmed && (
                                                <Menu position="bottom-end" withinPortal>
                                                    <Menu.Target>
                                                        <ActionIcon variant="subtle" aria-label="Aktionen">
                                                            <IconDotsVertical size={16} />
                                                        </ActionIcon>
                                                    </Menu.Target>
                                                    <Menu.Dropdown>
                                                        <Menu.Item onClick={() => setSubprojectRow(row)}>
                                                            Teilprojekt anlegen unter …
                                                        </Menu.Item>
                                                        {isAssigned(row) && (
                                                            <Menu.Item color="red" onClick={() => setProjects(row, [])}>
                                                                Zuordnung entfernen
                                                            </Menu.Item>
                                                        )}
                                                    </Menu.Dropdown>
                                                </Menu>
                                            )}
                                        </Table.Td>
                                    </Table.Tr>
                                ))}
                            </Table.Tbody>
                        </ResponsiveTable>
                        {filtered.length === 0 && <Text c="dimmed" size="sm">Keine Zeilen in dieser Auswahl.</Text>}
                        {filtered.length > PAGE_SIZE && (
                            <Group justify="center">
                                <Pagination
                                    total={Math.ceil(filtered.length / PAGE_SIZE)}
                                    value={page}
                                    onChange={setPage}
                                    size="sm"
                                />
                            </Group>
                        )}
                    </Stack>
                </ChronicleCard>

                {(record.missing_from_previous ?? []).length > 0 && (
                    <ChronicleCard>
                        <Stack gap="sm">
                            <Text fw={600}>
                                Im Vorjahr enthalten, jetzt ohne Eintrag ({record.missing_from_previous?.length})
                            </Text>
                            <Text size="sm" c="dimmed">
                                Projekte mit einem Eintrag im Infraplan {record.previous_year}, denen in diesem Entwurf
                                keine Zeile zugeordnet ist. Entweder fehlt die Zuordnung oder die Maßnahme ist
                                entfallen; die Phase des Projekts ändert sich dadurch nicht.
                            </Text>
                            <ResponsiveTable minWidth={560} striped withTableBorder verticalSpacing={4} fz="sm">
                                <Table.Thead>
                                    <Table.Tr>
                                        <Table.Th>Projekt</Table.Th>
                                        <Table.Th>Einträge {record.previous_year}</Table.Th>
                                    </Table.Tr>
                                </Table.Thead>
                                <Table.Tbody>
                                    {(record.missing_from_previous ?? []).map((m) => (
                                        <Table.Tr key={m.project_id}>
                                            <Table.Td>
                                                <Anchor component={Link} to={`/projects/${m.project_id}`} size="sm">
                                                    {m.project_name}
                                                </Anchor>
                                            </Table.Td>
                                            <Table.Td>
                                                {m.entries.map((e) => (
                                                    <Text key={`${e.section}-${e.lfd_nr}`} size="sm">
                                                        {SECTION_SHORT[e.section] ?? e.section} Nr. {e.lfd_nr}
                                                        {e.primary_number ? ` · ${e.primary_number}` : ""}
                                                        {e.massnahme ? ` · ${e.massnahme}` : ""}
                                                    </Text>
                                                ))}
                                            </Table.Td>
                                        </Table.Tr>
                                    ))}
                                </Table.Tbody>
                            </ResponsiveTable>
                        </Stack>
                    </ChronicleCard>
                )}

                {!confirmed && <ConfirmBlock record={record} />}
            </Stack>

            <SubprojectModal row={subprojectRow} onClose={() => setSubprojectRow(null)} parseResultId={id} />
        </Container>
    );
}

export default function InfraplanReviewPage() {
    return (
        <RequirePermission perm="infraplan.import">
            <InfraplanReviewPageContent />
        </RequirePermission>
    );
}
