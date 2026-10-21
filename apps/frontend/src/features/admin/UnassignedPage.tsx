import { useState } from "react";
import {
    Badge,
    Button,
    Container,
    Group,
    MultiSelect,
    Stack,
    Table,
    Text,
    Title,
} from "@mantine/core";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { Link } from "react-router-dom";
import { Stat } from "../../shared/ui/Stat";
import { notifications } from "@mantine/notifications";
import RequirePermission from "../../components/RequirePermission";
import { filterProjectOption } from "../../lib/filterProjectOption";
import {
    useProjectOptions,
    useUnassignedFinves,
    useUnassignedVibEntries,
    useAssignFinve,
    useAssignVibEntry,
    useVibEntry,
    useUnassignedGvfgEntries,
    useAssignGvfgEntry,
    useUnassignedInfraplanEntries,
    useAssignInfraplanEntry,
    type Project,
} from "../../shared/api/queries";
import CreateDraftProjectModal from "../projects/CreateDraftProjectModal";
import { MissingProjectAnchor } from "../import-review/shared";
import { formatMio, sumLine } from "../gvfg/gvfgFormat";
import VibEntryEditDrawer from "../vib-import/VibEntryEditDrawer";
import { SECTION_SHORT, formatMio as formatInfraplanMio } from "../infraplan/infraplanFormat";
import { LoadingState } from "../../shared/ui/LoadingState";

function UnassignedPageContent() {
    const [finveSelections, setFinveSelections] = useState<Record<number, string[]>>({});
    const [vibSelections, setVibSelections] = useState<Record<number, string[]>>({});
    const [gvfgSelections, setGvfgSelections] = useState<Record<number, string[]>>({});
    const [infraplanSelections, setInfraplanSelections] = useState<Record<number, string[]>>({});
    const [editingVibId, setEditingVibId] = useState<number | null>(null);
    const { data: editingVibEntry } = useVibEntry(editingVibId);
    // "A project is missing → create it as a draft and assign it here." One
    // modal serves every row; the anchor sets the target entry.
    const [draft, setDraft] = useState<{
        name: string;
        sourceLabel: string;
        onCreated: (project: Project) => void;
    } | null>(null);

    const { data: finves, isLoading: finvesLoading } = useUnassignedFinves();
    const { data: vibEntries, isLoading: vibLoading } = useUnassignedVibEntries();
    const { data: projects } = useProjectOptions();
    const assignFinve = useAssignFinve();
    const assignVib = useAssignVibEntry();
    const { data: gvfgEntries, isLoading: gvfgLoading } = useUnassignedGvfgEntries();
    const assignGvfg = useAssignGvfgEntry();
    const { data: infraplanEntries, isLoading: infraplanLoading } = useUnassignedInfraplanEntries();
    const assignInfraplan = useAssignInfraplanEntry();

    const projectOptions = (projects ?? []).map((p) => ({
        value: String(p.id),
        label: p.name ?? `Projekt ${p.id}`,
    }));

    const handleAssignFinve = async (finveId: number, extraIds: number[] = []) => {
        const ids = [...new Set([...(finveSelections[finveId] ?? []).map(Number), ...extraIds])];
        if (!ids.length) return;
        try {
            await assignFinve.mutateAsync({ finveId, projectIds: ids });
            notifications.show({ color: "green", message: "FinVe zugewiesen." });
            setFinveSelections((prev) => { const n = { ...prev }; delete n[finveId]; return n; });
        } catch {
            notifications.show({ color: "red", message: "Zuweisung fehlgeschlagen." });
        }
    };

    const handleAssignVib = async (entryId: number, extraIds: number[] = []) => {
        const ids = [...new Set([...(vibSelections[entryId] ?? []).map(Number), ...extraIds])];
        if (!ids.length) return;
        try {
            await assignVib.mutateAsync({ entryId, projectIds: ids });
            notifications.show({ color: "green", message: "VIB-Eintrag zugewiesen." });
            setVibSelections((prev) => { const n = { ...prev }; delete n[entryId]; return n; });
        } catch {
            notifications.show({ color: "red", message: "Zuweisung fehlgeschlagen." });
        }
    };

    const handleAssignGvfg = async (entryId: number, extraIds: number[] = []) => {
        const ids = [...new Set([...(gvfgSelections[entryId] ?? []).map(Number), ...extraIds])];
        if (!ids.length) return;
        try {
            await assignGvfg.mutateAsync({ entryId, projectIds: ids });
            notifications.show({ color: "green", message: "GVFG-Vorhaben zugewiesen." });
            setGvfgSelections((prev) => { const n = { ...prev }; delete n[entryId]; return n; });
        } catch {
            notifications.show({ color: "red", message: "Zuweisung fehlgeschlagen." });
        }
    };

    const handleAssignInfraplan = async (entryId: number, extraIds: number[] = []) => {
        const ids = [...new Set([...(infraplanSelections[entryId] ?? []).map(Number), ...extraIds])];
        if (!ids.length) return;
        try {
            await assignInfraplan.mutateAsync({ entryId, projectIds: ids });
            notifications.show({ color: "green", message: "Infraplan-Eintrag zugewiesen." });
            setInfraplanSelections((prev) => { const n = { ...prev }; delete n[entryId]; return n; });
        } catch {
            notifications.show({ color: "red", message: "Zuweisung fehlgeschlagen." });
        }
    };

    // The new draft is assigned right away, together with any projects already
    // picked in that row.
    const openDraft = (
        name: string | null | undefined,
        sourceLabel: string,
        assign: (extraIds: number[]) => void,
    ) =>
        setDraft({
            name: name ?? "",
            sourceLabel,
            onCreated: (project) => {
                if (project.id != null) assign([project.id]);
            },
        });

    const totalOpen =
        (finves?.length ?? 0) +
        (vibEntries?.length ?? 0) +
        (gvfgEntries?.length ?? 0) +
        (infraplanEntries?.length ?? 0);

    return (
        <Container size="xl" py="xl">
            <Stack gap="xl">
                <div>
                    <Text className="idt-eyebrow" component="div">Admin</Text>
                    <Title order={1}>Offene Zuordnungen</Title>
                </div>

                <Group justify="space-between" align="center" wrap="nowrap">
                    <Stat value={totalOpen} title={totalOpen === 1 ? "offene Zuordnung" : "offene Zuordnungen"} />
                    <Button component={Link} to="/admin/projects/new">
                        Neues Projekt anlegen
                    </Button>
                </Group>

                {/* FinVe section */}
                <Stack gap="sm">
                    <Group gap="xs" align="center">
                        <Title order={2}>
                            FinVes ohne Projektzuordnung
                        </Title>
                        <Badge variant="outline">{finves?.length ?? "…"}</Badge>
                    </Group>
                    {finvesLoading && <LoadingState rows={6} />}
                    {!finvesLoading && (
                        <ResponsiveTable minWidth={720} withTableBorder withColumnBorders>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>ID</Table.Th>
                                    <Table.Th>Name</Table.Th>
                                    <Table.Th>Typ</Table.Th>
                                    <Table.Th>Ab Jahr</Table.Th>
                                    <Table.Th>Projekte zuweisen</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {(finves ?? []).length === 0 && (
                                    <Table.Tr>
                                        <Table.Td colSpan={5}>
                                            <Text c="dimmed" size="sm" ta="center">Keine offenen FinVes.</Text>
                                        </Table.Td>
                                    </Table.Tr>
                                )}
                                {(finves ?? []).map((f) => (
                                    <Table.Tr key={f.id}>
                                        <Table.Td>{f.id}</Table.Td>
                                        <Table.Td>{f.name ?? "–"}</Table.Td>
                                        <Table.Td>
                                            <Badge variant="outline">
                                                {f.is_sammel_finve ? "SV-FinVe" : "FinVe"}
                                            </Badge>
                                        </Table.Td>
                                        <Table.Td>{f.starting_year ?? "–"}</Table.Td>
                                        <Table.Td>
                                            <Stack gap={4}>
                                                <Group gap="xs" wrap="nowrap">
                                                    <MultiSelect
                                                        data={projectOptions}
                                                        value={finveSelections[f.id] ?? []}
                                                        onChange={(v) =>
                                                            setFinveSelections((prev) => ({ ...prev, [f.id]: v }))
                                                        }
                                                        placeholder="Projekt suchen…"
                                                        searchable
                                                        filter={filterProjectOption}
                                                        size="xs"
                                                        w={300}
                                                    />
                                                    <Button
                                                        disabled={!(finveSelections[f.id]?.length)}
                                                        onClick={() => handleAssignFinve(f.id)}
                                                    >
                                                        Zuweisen
                                                    </Button>
                                                </Group>
                                                <MissingProjectAnchor
                                                    onClick={() =>
                                                        openDraft(f.name, "FinVe", (extra) => handleAssignFinve(f.id, extra))
                                                    }
                                                />
                                            </Stack>
                                        </Table.Td>
                                    </Table.Tr>
                                ))}
                            </Table.Tbody>
                        </ResponsiveTable>
                    )}
                </Stack>

                {/* VIB section */}
                <Stack gap="sm">
                    <Group gap="xs" align="center">
                        <Title order={2}>
                            VIB-Einträge ohne Projektzuordnung
                        </Title>
                        <Badge variant="outline">{vibEntries?.length ?? "…"}</Badge>
                    </Group>
                    {vibLoading && <LoadingState rows={6} />}
                    {!vibLoading && (
                        <ResponsiveTable minWidth={720} withTableBorder withColumnBorders>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>ID</Table.Th>
                                    <Table.Th>Name</Table.Th>
                                    <Table.Th>Abschnitt</Table.Th>
                                    <Table.Th>Kategorie</Table.Th>
                                    <Table.Th>VIB-Jahr</Table.Th>
                                    <Table.Th>Projekte zuweisen</Table.Th>
                                    <Table.Th />
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {(vibEntries ?? []).length === 0 && (
                                    <Table.Tr>
                                        <Table.Td colSpan={7}>
                                            <Text c="dimmed" size="sm" ta="center">Keine offenen VIB-Einträge.</Text>
                                        </Table.Td>
                                    </Table.Tr>
                                )}
                                {(vibEntries ?? []).map((e) => (
                                    <Table.Tr key={e.id}>
                                        <Table.Td>{e.id}</Table.Td>
                                        <Table.Td style={{ maxWidth: 300 }}>{e.vib_name_raw}</Table.Td>
                                        <Table.Td>{e.vib_section ?? "–"}</Table.Td>
                                        <Table.Td>
                                            <Badge variant="outline">{e.category}</Badge>
                                        </Table.Td>
                                        <Table.Td>{e.report_year}</Table.Td>
                                        <Table.Td>
                                            <Stack gap={4}>
                                                <Group gap="xs" wrap="nowrap">
                                                    <MultiSelect
                                                        data={projectOptions}
                                                        value={vibSelections[e.id] ?? []}
                                                        onChange={(v) =>
                                                            setVibSelections((prev) => ({ ...prev, [e.id]: v }))
                                                        }
                                                        placeholder="Projekt suchen…"
                                                        searchable
                                                        filter={filterProjectOption}
                                                        size="xs"
                                                        w={300}
                                                    />
                                                    <Button
                                                        disabled={!(vibSelections[e.id]?.length)}
                                                        onClick={() => handleAssignVib(e.id)}
                                                    >
                                                        Zuweisen
                                                    </Button>
                                                </Group>
                                                <MissingProjectAnchor
                                                    onClick={() =>
                                                        openDraft(e.vib_name_raw, "VIB", (extra) => handleAssignVib(e.id, extra))
                                                    }
                                                />
                                            </Stack>
                                        </Table.Td>
                                        <Table.Td>
                                            <Button size="xs" variant="light" onClick={() => setEditingVibId(e.id)}>
                                                Bearbeiten
                                            </Button>
                                        </Table.Td>
                                    </Table.Tr>
                                ))}
                            </Table.Tbody>
                        </ResponsiveTable>
                    )}
                </Stack>

                {/* GVFG section — newest edition only */}
                <Stack gap="sm">
                    <Group gap="xs" align="center">
                        <Title order={2}>
                            GVFG-Vorhaben ohne Projektzuordnung
                        </Title>
                        <Badge variant="outline">{gvfgEntries?.length ?? "…"}</Badge>
                    </Group>
                    <Text size="xs" c="dimmed">
                        Nur die neueste Ausgabe des Bundesprogramms. Zugewiesene Projekte kommen in die Gruppe „GVFG“
                        (Baden-Württemberg zusätzlich „GVFG BW“).
                    </Text>
                    {gvfgLoading && <LoadingState rows={6} />}
                    {!gvfgLoading && (
                        <ResponsiveTable minWidth={720} withTableBorder withColumnBorders>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Schlüssel</Table.Th>
                                    <Table.Th>Bezeichnung</Table.Th>
                                    <Table.Th>Land</Table.Th>
                                    <Table.Th className="num">Finanzhilfen Mio. €</Table.Th>
                                    <Table.Th>Projekte zuweisen</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {(gvfgEntries ?? []).length === 0 && (
                                    <Table.Tr>
                                        <Table.Td colSpan={5}>
                                            <Text c="dimmed" size="sm" ta="center">Keine offenen GVFG-Vorhaben.</Text>
                                        </Table.Td>
                                    </Table.Tr>
                                )}
                                {(gvfgEntries ?? []).map((e) => (
                                    <Table.Tr key={e.id}>
                                        <Table.Td style={{ whiteSpace: "nowrap" }}>{e.key}</Table.Td>
                                        <Table.Td style={{ maxWidth: 300 }}>
                                            {e.name ?? "–"}
                                            {e.part === "nachrichtlich" && (
                                                <Text span size="xs" c="dimmed"> · nachr.</Text>
                                            )}
                                        </Table.Td>
                                        <Table.Td>{e.land}</Table.Td>
                                        <Table.Td className="num">{formatMio(sumLine(e)?.aid_total)}</Table.Td>
                                        <Table.Td>
                                            <Stack gap={4}>
                                                <Group gap="xs" wrap="nowrap">
                                                    <MultiSelect
                                                        data={projectOptions}
                                                        value={gvfgSelections[e.id] ?? []}
                                                        onChange={(v) =>
                                                            setGvfgSelections((prev) => ({ ...prev, [e.id]: v }))
                                                        }
                                                        placeholder="Projekt suchen…"
                                                        searchable
                                                        filter={filterProjectOption}
                                                        size="xs"
                                                        w={300}
                                                    />
                                                    <Button
                                                        disabled={!(gvfgSelections[e.id]?.length)}
                                                        onClick={() => handleAssignGvfg(e.id)}
                                                    >
                                                        Zuweisen
                                                    </Button>
                                                </Group>
                                                <MissingProjectAnchor
                                                    onClick={() =>
                                                        openDraft(e.name, "GVFG", (extra) => handleAssignGvfg(e.id, extra))
                                                    }
                                                />
                                            </Stack>
                                        </Table.Td>
                                    </Table.Tr>
                                ))}
                            </Table.Tbody>
                        </ResponsiveTable>
                    )}
                </Stack>

                {/* Infraplan section — newest year only */}
                <Stack gap="sm">
                    <Group gap="xs" align="center">
                        <Title order={2}>
                            Infraplan-Einträge ohne Projektzuordnung
                        </Title>
                        <Badge variant="outline">{infraplanEntries?.length ?? "…"}</Badge>
                    </Group>
                    <Text size="xs" c="dimmed">
                        Nur der neueste Jahrgang des Infraplans. Eine Zuordnung aktualisiert den Planungsstand des
                        Projekts sofort.
                    </Text>
                    {infraplanLoading && <LoadingState rows={6} />}
                    {!infraplanLoading && (
                        <ResponsiveTable minWidth={880} withTableBorder withColumnBorders>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Abschnitt</Table.Th>
                                    <Table.Th>Bezeichnung / Maßnahme</Table.Th>
                                    <Table.Th>Stand · IBN</Table.Th>
                                    <Table.Th className="num">Kosten Mio. €</Table.Th>
                                    <Table.Th>Projekte zuweisen</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {(infraplanEntries ?? []).length === 0 && (
                                    <Table.Tr>
                                        <Table.Td colSpan={5}>
                                            <Text c="dimmed" size="sm" ta="center">Keine offenen Infraplan-Einträge.</Text>
                                        </Table.Td>
                                    </Table.Tr>
                                )}
                                {(infraplanEntries ?? []).map((e) => (
                                    <Table.Tr key={e.id}>
                                        <Table.Td style={{ whiteSpace: "nowrap" }}>
                                            {SECTION_SHORT[e.section] ?? e.section} Nr. {e.lfd_nr}
                                            <Text size="xs" c="dimmed">
                                                {e.report_year}
                                                {e.primary_number ? ` · ${e.primary_number}` : ""}
                                                {e.page != null ? ` · S. ${e.page}` : ""}
                                            </Text>
                                        </Table.Td>
                                        <Table.Td style={{ maxWidth: 300 }}>
                                            {e.bezeichnung ?? "–"}
                                            {e.massnahme && e.massnahme !== e.bezeichnung && (
                                                <Text size="xs">{e.massnahme}</Text>
                                            )}
                                            {e.laender && <Text size="xs" c="dimmed">{e.laender}</Text>}
                                        </Table.Td>
                                        <Table.Td style={{ maxWidth: 200 }}>
                                            <Text size="sm">{e.state_raw ?? "–"}</Text>
                                            {e.ibn_raw && <Text size="xs" c="dimmed">IBN {e.ibn_raw}</Text>}
                                        </Table.Td>
                                        <Table.Td className="num">{formatInfraplanMio(e.cost_mio)}</Table.Td>
                                        <Table.Td>
                                            <Stack gap={4}>
                                                <Group gap="xs" wrap="nowrap">
                                                    <MultiSelect
                                                        data={projectOptions}
                                                        value={infraplanSelections[e.id] ?? []}
                                                        onChange={(v) =>
                                                            setInfraplanSelections((prev) => ({ ...prev, [e.id]: v }))
                                                        }
                                                        placeholder="Projekt suchen…"
                                                        searchable
                                                        filter={filterProjectOption}
                                                        size="xs"
                                                        w={300}
                                                    />
                                                    <Button
                                                        disabled={!(infraplanSelections[e.id]?.length)}
                                                        onClick={() => handleAssignInfraplan(e.id)}
                                                    >
                                                        Zuweisen
                                                    </Button>
                                                </Group>
                                                <MissingProjectAnchor
                                                    onClick={() =>
                                                        openDraft(e.massnahme ?? e.bezeichnung, "Infraplan", (extra) =>
                                                            handleAssignInfraplan(e.id, extra),
                                                        )
                                                    }
                                                />
                                            </Stack>
                                        </Table.Td>
                                    </Table.Tr>
                                ))}
                            </Table.Tbody>
                        </ResponsiveTable>
                    )}
                </Stack>
            </Stack>

            <CreateDraftProjectModal
                opened={draft !== null}
                onClose={() => setDraft(null)}
                initialName={draft?.name}
                sourceLabel={draft?.sourceLabel}
                onCreated={draft ? draft.onCreated : () => {}}
            />

            <VibEntryEditDrawer
                entry={editingVibEntry ?? null}
                opened={editingVibId !== null}
                onClose={() => setEditingVibId(null)}
            />
        </Container>
    );
}

export default function UnassignedPage() {
    return (
        <RequirePermission perm="assignment.manage">
            <UnassignedPageContent />
        </RequirePermission>
    );
}
