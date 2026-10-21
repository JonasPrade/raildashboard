import { Link, useNavigate } from "react-router-dom";
import {
    Alert,
    Anchor,
    Badge,
    Button,
    Container,
    Group,
    Loader,
    Stack,
    Table,
    Text,
    Title,
} from "@mantine/core";
import { ChevronRight } from "lucide-react";

import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { useFuldaYearSummaries } from "../../shared/api/queries";
import { ANSWER_STATUS_LABEL } from "./fuldaShared";

export default function FuldaImportPage() {
    const navigate = useNavigate();
    const { data: summaries, isLoading } = useFuldaYearSummaries();

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Stack gap={4}>
                    <Title order={2}>Fulda-Runde</Title>
                    <Text c="dimmed" size="sm">
                        Die Ergebnisse der Fulda-Runde stehen in den <b>Antworten der
                        Bundesregierung</b> auf Kleine Anfragen. Diese PDFs liest Claude mit dem
                        Skill <code>fulda-runde</code> über den MCP-Server ein: Dokument, jede
                        Projektzeile mit Kategorie, Fundstelle und Wortlaut, Zuordnung zu Projekten.
                        Hier prüfst du das Ergebnis und gibst es frei. Ist-Aussagen setzen den
                        Planungsstand, angekündigte Abschlüsse und Neuaufnahmen erscheinen nur als
                        erwarteter Termin in der Prognose.{" "}
                        <Anchor component={Link} to="/admin/anleitungen/fulda" size="sm">
                            Anleitung
                        </Anchor>
                    </Text>
                </Stack>

                <Stack gap="xs">
                    <Title order={4}>Jahrgänge</Title>
                    {isLoading ? (
                        <Group justify="center" py="xl">
                            <Loader />
                        </Group>
                    ) : !summaries || summaries.length === 0 ? (
                        <Alert variant="light" title="Keine Jahrgänge">
                            Noch keine Fulda-Antworten eingelesen. Gib Claude das PDF und bitte, es
                            mit dem Skill „fulda-runde" einzulesen.
                        </Alert>
                    ) : (
                        <ResponsiveTable minWidth={640} striped highlightOnHover>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Jahr</Table.Th>
                                    <Table.Th>Drucksache</Table.Th>
                                    <Table.Th>Einträge</Table.Th>
                                    <Table.Th>Status</Table.Th>
                                    <Table.Th />
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {summaries.map((s) => {
                                    const open = s.total - s.confirmed;
                                    const target = `/admin/fulda-import/year/${s.announcement_year}`;
                                    return (
                                        <Table.Tr
                                            key={s.announcement_year}
                                            style={{ cursor: "pointer" }}
                                            onClick={() => navigate(target)}
                                        >
                                            <Table.Td>
                                                <Text fw={600}>{s.announcement_year}</Text>
                                            </Table.Td>
                                            <Table.Td>
                                                <Stack gap={2}>
                                                    {(s.documents ?? []).map((d) => (
                                                        <Group key={d.id} gap={6} wrap="nowrap">
                                                            <Text size="sm">Drs. {d.drucksache}</Text>
                                                            {d.answer_status !== "VOLLSTAENDIG" && (
                                                                <Badge size="xs" variant="light" color="orange">
                                                                    {ANSWER_STATUS_LABEL[d.answer_status]}
                                                                </Badge>
                                                            )}
                                                        </Group>
                                                    ))}
                                                </Stack>
                                            </Table.Td>
                                            <Table.Td>{s.total}</Table.Td>
                                            <Table.Td>
                                                <Group gap="xs">
                                                    <Badge variant="light" color="green">
                                                        {s.confirmed} aktiv
                                                    </Badge>
                                                    {open > 0 && (
                                                        <Badge variant="light" color="orange">
                                                            {open} offen
                                                        </Badge>
                                                    )}
                                                </Group>
                                            </Table.Td>
                                            <Table.Td onClick={(e) => e.stopPropagation()}>
                                                <Group gap="xs" justify="flex-end" wrap="nowrap">
                                                    <Button
                                                        size="xs"
                                                        variant="light"
                                                        rightSection={<ChevronRight size={16} />}
                                                        onClick={() => navigate(target)}
                                                    >
                                                        Öffnen
                                                    </Button>
                                                </Group>
                                            </Table.Td>
                                        </Table.Tr>
                                    );
                                })}
                            </Table.Tbody>
                        </ResponsiveTable>
                    )}
                </Stack>
            </Stack>
        </Container>
    );
}
