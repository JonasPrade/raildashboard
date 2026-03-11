import { Badge, Button, Group, Table, Text } from "@mantine/core";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import type { ParseResultPublic } from "../../../shared/api/queries";
import { useDeleteParseResult } from "../../../shared/api/queries";

function StatusBadge({ status }: { status: ParseResultPublic["status"] }) {
    const colorMap: Record<ParseResultPublic["status"], string> = {
        PENDING: "yellow",
        SUCCESS: "green",
        FAILURE: "red",
    };
    return <Badge color={colorMap[status]} variant="light">{status}</Badge>;
}

type Props = {
    results: ParseResultPublic[];
};

export function ParseResultList({ results }: Props) {
    const navigate = useNavigate();
    const deleteResult = useDeleteParseResult();

    const handleDelete = (r: ParseResultPublic) => {
        const hasConfirmedData = r.confirmed_at !== null;
        modals.openConfirmModal({
            title: `Import ${r.haushalt_year} löschen?`,
            children: (
                <Text size="sm">
                    {hasConfirmedData
                        ? `Dieser Import wurde bereits bestätigt. Alle importierten Budget-Daten für ${r.haushalt_year} werden ebenfalls gelöscht. Diese Aktion kann nicht rückgängig gemacht werden.`
                        : "Der Parse-Lauf wird unwiderruflich gelöscht."}
                </Text>
            ),
            labels: { confirm: "Löschen", cancel: "Abbrechen" },
            confirmProps: { color: "red" },
            onConfirm: async () => {
                try {
                    await deleteResult.mutateAsync(r.id);
                    notifications.show({ color: "green", message: "Import gelöscht." });
                } catch {
                    notifications.show({ color: "red", message: "Löschen fehlgeschlagen." });
                }
            },
        });
    };

    if (results.length === 0) {
        return <Text c="dimmed" size="sm">Noch keine Import-Läufe vorhanden.</Text>;
    }

    return (
        <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
                <Table.Tr>
                    <Table.Th>Jahr</Table.Th>
                    <Table.Th>Dateiname</Table.Th>
                    <Table.Th>Datum</Table.Th>
                    <Table.Th>Nutzer</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Importiert am</Table.Th>
                    <Table.Th />
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
                {results.map((r) => (
                    <Table.Tr key={r.id}>
                        <Table.Td>{r.haushalt_year}</Table.Td>
                        <Table.Td>
                            <Text size="sm" truncate maw={200}>{r.pdf_filename}</Text>
                        </Table.Td>
                        <Table.Td>
                            <Text size="sm" c="dimmed">
                                {new Date(r.parsed_at).toLocaleString("de-DE", { timeZone: "Europe/Berlin" })}
                            </Text>
                        </Table.Td>
                        <Table.Td>
                            <Text size="sm">{r.username_snapshot ?? "–"}</Text>
                        </Table.Td>
                        <Table.Td>
                            <StatusBadge status={r.status} />
                        </Table.Td>
                        <Table.Td>
                            {r.confirmed_at ? (
                                <Text size="sm" c="dimmed">
                                    {new Date(r.confirmed_at).toLocaleString("de-DE", { timeZone: "Europe/Berlin" })}
                                </Text>
                            ) : (
                                <Text size="sm" c="dimmed">–</Text>
                            )}
                        </Table.Td>
                        <Table.Td>
                            <Group gap="xs" wrap="nowrap">
                                <Button
                                    size="xs"
                                    variant="subtle"
                                    disabled={r.status !== "SUCCESS"}
                                    onClick={() => navigate(`/admin/haushalt-import/review/${r.id}`)}
                                >
                                    Öffnen
                                </Button>
                                <Button
                                    size="xs"
                                    variant="subtle"
                                    color="red"
                                    loading={deleteResult.isPending}
                                    onClick={() => handleDelete(r)}
                                >
                                    Löschen
                                </Button>
                            </Group>
                        </Table.Td>
                    </Table.Tr>
                ))}
            </Table.Tbody>
        </Table>
    );
}
