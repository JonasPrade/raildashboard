import { useState } from "react";
import {
    Alert,
    Button,
    Container,
    Group,
    Loader,
    NumberInput,
    Stack,
    Switch,
    Table,
    Text,
} from "@mantine/core";
import { ChronicleHeadline, ChronicleDataChip } from "../../components/chronicle";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import { useUnmatchedRows, useResolveUnmatchedRow } from "../../shared/api/queries";

export default function HaushaltsUnmatchedPage() {
    const { user } = useAuth();
    const [showResolved, setShowResolved] = useState(false);
    const [resolveValues, setResolveValues] = useState<Record<number, number | "">>({});

    const { data: rows, isLoading, isError } = useUnmatchedRows(showResolved ? undefined : false);
    const resolve = useResolveUnmatchedRow();

    if (user?.role !== "editor" && user?.role !== "admin") {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    const handleResolve = async (rowId: number) => {
        const finveId = resolveValues[rowId];
        if (!finveId) return;
        try {
            await resolve.mutateAsync({ rowId, finveId: Number(finveId) });
            notifications.show({ color: "green", message: "Zeile zugewiesen." });
            setResolveValues((prev) => { const n = { ...prev }; delete n[rowId]; return n; });
        } catch {
            notifications.show({ color: "red", message: "Zuweisung fehlgeschlagen." });
        }
    };

    return (
        <Container size="xl" py="xl">
            <Stack gap="lg">
                <Group justify="space-between">
                    <ChronicleHeadline as="h1">Unbekannte Haushaltszeilen</ChronicleHeadline>
                    <Switch
                        label="Erledigte anzeigen"
                        checked={showResolved}
                        onChange={(e) => setShowResolved(e.currentTarget.checked)}
                    />
                </Group>

                {isLoading && <Group justify="center"><Loader /></Group>}
                {isError && (
                    <Alert color="red" variant="light" title="Fehler">
                        Liste konnte nicht geladen werden.
                    </Alert>
                )}

                {!isLoading && !isError && (
                    <Table withTableBorder withColumnBorders striped>
                        <Table.Thead>
                            <Table.Tr>
                                <Table.Th>Jahr</Table.Th>
                                <Table.Th>FinVe-Nr. (roh)</Table.Th>
                                <Table.Th>Bezeichnung (roh)</Table.Th>
                                <Table.Th>Status</Table.Th>
                                <Table.Th>FinVe-ID zuweisen</Table.Th>
                            </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                            {(rows ?? []).length === 0 && (
                                <Table.Tr>
                                    <Table.Td colSpan={5}>
                                        <Text c="dimmed" size="sm" ta="center">
                                            Keine offenen Zeilen vorhanden.
                                        </Text>
                                    </Table.Td>
                                </Table.Tr>
                            )}
                            {(rows ?? []).map((row) => (
                                <Table.Tr key={row.id}>
                                    <Table.Td>{row.haushalt_year}</Table.Td>
                                    <Table.Td>{row.raw_finve_number}</Table.Td>
                                    <Table.Td>{row.raw_name}</Table.Td>
                                    <Table.Td>
                                        {row.resolved ? (
                                            <ChronicleDataChip>
                                                Erledigt (FinVe {row.resolved_finve_id})
                                            </ChronicleDataChip>
                                        ) : (
                                            <ChronicleDataChip>Offen</ChronicleDataChip>
                                        )}
                                    </Table.Td>
                                    <Table.Td>
                                        {!row.resolved && (
                                            <Group gap="xs">
                                                <NumberInput
                                                    placeholder="FinVe-ID"
                                                    value={resolveValues[row.id] ?? ""}
                                                    onChange={(v) =>
                                                        setResolveValues((prev) => ({
                                                            ...prev,
                                                            [row.id]: v === "" ? "" : Number(v),
                                                        }))
                                                    }
                                                    min={1}
                                                    size="xs"
                                                    w={120}
                                                    hideControls
                                                />
                                                <Button
                                                    size="xs"
                                                    disabled={!resolveValues[row.id]}
                                                    loading={resolve.isPending}
                                                    onClick={() => handleResolve(row.id)}
                                                >
                                                    Zuweisen
                                                </Button>
                                            </Group>
                                        )}
                                    </Table.Td>
                                </Table.Tr>
                            ))}
                        </Table.Tbody>
                    </Table>
                )}
            </Stack>
        </Container>
    );
}
