import { Badge, Collapse, Group, Stack, Table, Text, UnstyledButton } from "@mantine/core";
import { useState } from "react";
import type { TitelEntryProposed } from "../../../shared/api/queries";

function fmt(val: number | null) {
    if (val === null) return "–";
    return val.toLocaleString("de-DE") + " T€";
}

type Props = {
    entries: TitelEntryProposed[];
};

export function TitelBreakdown({ entries }: Props) {
    const [open, setOpen] = useState(false);

    if (entries.length === 0) return null;

    return (
        <Stack gap={4}>
            <UnstyledButton onClick={() => setOpen((o) => !o)}>
                <Group gap={4}>
                    <Text size="xs" c="dimmed">{open ? "▲" : "▼"}</Text>
                    <Text size="xs" c="dimmed">{entries.length} Titel</Text>
                </Group>
            </UnstyledButton>
            <Collapse in={open}>
                <Table withColumnBorders fz="xs" mt={4}>
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th>Titel</Table.Th>
                            <Table.Th>Vorjahr</Table.Th>
                            <Table.Th>Aktuell</Table.Th>
                            <Table.Th>Verausgabt</Table.Th>
                            <Table.Th>Bewilligt</Table.Th>
                            <Table.Th>Ausgabereste</Table.Th>
                            <Table.Th>Veranschlagt</Table.Th>
                            <Table.Th>Vorhalten</Table.Th>
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        {entries.map((e) => (
                            <Table.Tr key={e.titel_key}>
                                <Table.Td>
                                    <Group gap={4}>
                                        <Text>{e.label}</Text>
                                        {e.is_nachrichtlich && (
                                            <Badge size="xs" variant="outline" color="gray">
                                                nachrichtl.
                                            </Badge>
                                        )}
                                    </Group>
                                </Table.Td>
                                <Table.Td>{fmt(e.cost_estimate_last_year)}</Table.Td>
                                <Table.Td>{fmt(e.cost_estimate_aktuell)}</Table.Td>
                                <Table.Td>{fmt(e.verausgabt_bis)}</Table.Td>
                                <Table.Td>{fmt(e.bewilligt)}</Table.Td>
                                <Table.Td>{fmt(e.ausgabereste_transferred)}</Table.Td>
                                <Table.Td>{fmt(e.veranschlagt)}</Table.Td>
                                <Table.Td>{fmt(e.vorhalten_future)}</Table.Td>
                            </Table.Tr>
                        ))}
                    </Table.Tbody>
                </Table>
            </Collapse>
        </Stack>
    );
}
