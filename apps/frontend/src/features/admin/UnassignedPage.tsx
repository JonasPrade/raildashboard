import { useState } from "react";
import {
    Alert,
    Button,
    Container,
    Group,
    Loader,
    MultiSelect,
    Stack,
    Table,
    Text,
    Title,
} from "@mantine/core";
import { ChronicleButton, ChronicleDataChip } from "../../components/chronicle";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import { filterProjectOption } from "../../lib/filterProjectOption";
import {
    useProjects,
    useUnassignedFinves,
    useUnassignedVibEntries,
    useAssignFinve,
    useAssignVibEntry,
    useVibEntry,
} from "../../shared/api/queries";
import VibEntryEditDrawer from "../vib-import/VibEntryEditDrawer";

export default function UnassignedPage() {
    const { user } = useAuth();
    const [finveSelections, setFinveSelections] = useState<Record<number, string[]>>({});
    const [vibSelections, setVibSelections] = useState<Record<number, string[]>>({});
    const [editingVibId, setEditingVibId] = useState<number | null>(null);
    const { data: editingVibEntry } = useVibEntry(editingVibId);

    const { data: finves, isLoading: finvesLoading } = useUnassignedFinves();
    const { data: vibEntries, isLoading: vibLoading } = useUnassignedVibEntries();
    const { data: projects } = useProjects();
    const assignFinve = useAssignFinve();
    const assignVib = useAssignVibEntry();

    if (user?.role !== "editor" && user?.role !== "admin") {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    const projectOptions = (projects ?? []).map((p) => ({
        value: String(p.id),
        label: p.name ?? `Projekt ${p.id}`,
    }));

    const handleAssignFinve = async (finveId: number) => {
        const ids = (finveSelections[finveId] ?? []).map(Number);
        if (!ids.length) return;
        try {
            await assignFinve.mutateAsync({ finveId, projectIds: ids });
            notifications.show({ color: "green", message: "FinVe zugewiesen." });
            setFinveSelections((prev) => { const n = { ...prev }; delete n[finveId]; return n; });
        } catch {
            notifications.show({ color: "red", message: "Zuweisung fehlgeschlagen." });
        }
    };

    const handleAssignVib = async (entryId: number) => {
        const ids = (vibSelections[entryId] ?? []).map(Number);
        if (!ids.length) return;
        try {
            await assignVib.mutateAsync({ entryId, projectIds: ids });
            notifications.show({ color: "green", message: "VIB-Eintrag zugewiesen." });
            setVibSelections((prev) => { const n = { ...prev }; delete n[entryId]; return n; });
        } catch {
            notifications.show({ color: "red", message: "Zuweisung fehlgeschlagen." });
        }
    };

    return (
        <Container size="xl" py="xl">
            <Stack gap="xl">
                <Title order={2}>Offene Zuordnungen</Title>

                {/* FinVe section */}
                <Stack gap="sm">
                    <Group gap="xs">
                        <Title order={4}>FinVes ohne Projektzuordnung</Title>
                        <ChronicleDataChip>{finves?.length ?? "…"}</ChronicleDataChip>
                    </Group>
                    {finvesLoading && <Loader size="sm" />}
                    {!finvesLoading && (
                        <Table withTableBorder withColumnBorders>
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
                                            <ChronicleDataChip>
                                                {f.is_sammel_finve ? "SV-FinVe" : "FinVe"}
                                            </ChronicleDataChip>
                                        </Table.Td>
                                        <Table.Td>{f.starting_year ?? "–"}</Table.Td>
                                        <Table.Td>
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
                                                <ChronicleButton
                                                    disabled={!(finveSelections[f.id]?.length)}
                                                    onClick={() => handleAssignFinve(f.id)}
                                                >
                                                    Zuweisen
                                                </ChronicleButton>
                                            </Group>
                                        </Table.Td>
                                    </Table.Tr>
                                ))}
                            </Table.Tbody>
                        </Table>
                    )}
                </Stack>

                {/* VIB section */}
                <Stack gap="sm">
                    <Group gap="xs">
                        <Title order={4}>VIB-Einträge ohne Projektzuordnung</Title>
                        <ChronicleDataChip>{vibEntries?.length ?? "…"}</ChronicleDataChip>
                    </Group>
                    {vibLoading && <Loader size="sm" />}
                    {!vibLoading && (
                        <Table withTableBorder withColumnBorders>
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
                                            <ChronicleDataChip>{e.category}</ChronicleDataChip>
                                        </Table.Td>
                                        <Table.Td>{e.report_year}</Table.Td>
                                        <Table.Td>
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
                                                <ChronicleButton
                                                    disabled={!(vibSelections[e.id]?.length)}
                                                    onClick={() => handleAssignVib(e.id)}
                                                >
                                                    Zuweisen
                                                </ChronicleButton>
                                            </Group>
                                        </Table.Td>
                                        <Table.Td>
                                            <Button size="xs" variant="light" onClick={() => setEditingVibId(e.id)}>
                                                Bearbeiten
                                            </Button>
                                        </Table.Td>
                                    </Table.Tr>
                                ))}
                            </Table.Tbody>
                        </Table>
                    )}
                </Stack>
            </Stack>

            <VibEntryEditDrawer
                entry={editingVibEntry ?? null}
                opened={editingVibId !== null}
                onClose={() => setEditingVibId(null)}
            />
        </Container>
    );
}
