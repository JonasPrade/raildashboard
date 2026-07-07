import type { ReactNode } from "react";
import {
    Anchor,
    Badge,
    Box,
    Button,
    Card,
    Checkbox,
    Divider,
    FileInput,
    Group,
    MultiSelect,
    NumberInput,
    Progress,
    Select,
    Stack,
    Stepper,
    Switch,
    Table,
    Text,
    Textarea,
    TextInput,
    Title,
} from "@mantine/core";
import { ChronicleDataChip } from "../../components/chronicle";
import PhaseStepper from "../projects/components/progress/PhaseStepper";

/**
 * Static, illustrative replicas of the real screens, shown inside guide steps
 * via GuideExampleView (which renders them non-interactive). Keep the labels
 * in sync with the actual feature UI they illustrate — the guides promise
 * "what you see here is what the page looks like".
 */

const PROJECT_OPTIONS = [
    { value: "1", label: "ABS/NBS Hanau–Würzburg/Fulda–Erfurt" },
    { value: "2", label: "   ↳ PFA Gelnhausen–Wächtersbach" },
    { value: "3", label: "ABS München–Mühldorf–Freilassing" },
];

// --- Projektfortschritt -------------------------------------------------------

function ProgressStepperExample() {
    return (
        <Stack gap="xs">
            <Text size="xs" c="dimmed">
                Projekt in der Genehmigungsplanung; parl. Befassung abgeschlossen,
                Planfeststellung läuft:
            </Text>
            <PhaseStepper
                current="GENEHMIGUNGSPLANUNG"
                parlRelevant
                parlState="ABGESCHLOSSEN"
                parlDate="2024-05-13"
                pfRelevant
                pfState="LAEUFT"
            />
        </Stack>
    );
}

// --- Fulda-Runde ---------------------------------------------------------------

function FuldaYearTableExample() {
    return (
        <Stack gap={6}>
            <Group gap="xs">
                <Title order={5}>Projekte in Lph 3–4</Title>
                <Badge variant="light" color="blue">2</Badge>
                <Badge variant="light" color="green">1 aktiv</Badge>
            </Group>
            <Table layout="fixed" w="100%" verticalSpacing="sm">
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th style={{ width: "28%" }}>Projekt (Roh)</Table.Th>
                        <Table.Th style={{ width: "24%" }}>Abschnitt → Unterprojekt</Table.Th>
                        <Table.Th style={{ width: "36%" }}>Projekte zuordnen</Table.Th>
                        <Table.Th style={{ width: "12%" }}>Übernehmen</Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    <Table.Tr>
                        <Table.Td><Text size="sm" fw={500}>ABS/NBS Hanau–Würzburg/Fulda</Text></Table.Td>
                        <Table.Td><Text size="sm">Gelnhausen–Wächtersbach</Text></Table.Td>
                        <Table.Td>
                            <Stack gap={4}>
                                <MultiSelect data={PROJECT_OPTIONS} defaultValue={["2"]} />
                                <Anchor size="xs">+ Projekt fehlt?</Anchor>
                            </Stack>
                        </Table.Td>
                        <Table.Td><Badge variant="light" color="green">aktiv</Badge></Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                        <Table.Td><Text size="sm" fw={500}>ABS München–Mühldorf</Text></Table.Td>
                        <Table.Td><Text size="sm" c="dimmed">—</Text></Table.Td>
                        <Table.Td>
                            <Stack gap={4}>
                                <MultiSelect
                                    data={PROJECT_OPTIONS}
                                    placeholder="Projekt / Unterprojekt zuordnen …"
                                />
                                <Anchor size="xs">+ Projekt fehlt?</Anchor>
                            </Stack>
                        </Table.Td>
                        <Table.Td><Badge variant="light" color="gray">offen</Badge></Table.Td>
                    </Table.Tr>
                </Table.Tbody>
            </Table>
        </Stack>
    );
}

// --- DB-Bauportal ---------------------------------------------------------------

function BauportalTableExample() {
    return (
        <Stack gap="sm">
            <Group justify="space-between">
                <Switch label="Nur offene (unbestätigt)" defaultChecked={false} />
                <Text size="sm" c="dimmed">128 Einträge · 97 aktiv</Text>
            </Group>
            <Table verticalSpacing="sm">
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Bauportal-Projekt</Table.Th>
                        <Table.Th>Phase</Table.Th>
                        <Table.Th>Bauzeitraum</Table.Th>
                        <Table.Th style={{ width: "30%" }}>Zuordnung</Table.Th>
                        <Table.Th>Übernehmen</Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    <Table.Tr>
                        <Table.Td>
                            <Stack gap={2}>
                                <Text size="sm" fw={500}>Gelnhausen–Wächtersbach: Streckenausbau</Text>
                                <Anchor size="xs">↗ Bauportal</Anchor>
                            </Stack>
                        </Table.Td>
                        <Table.Td><Badge color="orange" variant="light">Bau</Badge></Table.Td>
                        <Table.Td><Text size="xs" c="dimmed">2024–2027</Text></Table.Td>
                        <Table.Td>
                            <Stack gap={4}>
                                <Select data={PROJECT_OPTIONS} defaultValue="2" />
                                <Text size="xs" c="dimmed">✦ Vorschlag – bitte prüfen</Text>
                            </Stack>
                        </Table.Td>
                        <Table.Td><Badge variant="light" color="gray">offen</Badge></Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                        <Table.Td>
                            <Stack gap={2}>
                                <Text size="sm" fw={500}>Bahnhofsmodernisierung Kleinstadt</Text>
                                <Anchor size="xs">↗ Bauportal</Anchor>
                            </Stack>
                        </Table.Td>
                        <Table.Td><Text size="xs" c="dimmed">kein Beitrag</Text></Table.Td>
                        <Table.Td><Text size="xs" c="dimmed">–</Text></Table.Td>
                        <Table.Td>
                            <Select data={PROJECT_OPTIONS} placeholder="Projekt zuordnen …" />
                        </Table.Td>
                        <Table.Td><Badge variant="light" color="gray">offen</Badge></Table.Td>
                    </Table.Tr>
                </Table.Tbody>
            </Table>
        </Stack>
    );
}

// --- Haushalts-Import ------------------------------------------------------------

function HaushaltReviewExample() {
    return (
        <Table verticalSpacing="sm">
            <Table.Thead>
                <Table.Tr>
                    <Table.Th>FinVe</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th style={{ width: "40%" }}>Projekte zuordnen</Table.Th>
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
                <Table.Tr>
                    <Table.Td>
                        <Text size="sm" fw={500}>B0080 · ABS Hanau–Würzburg/Fulda</Text>
                    </Table.Td>
                    <Table.Td><Badge variant="light" color="blue">Neu</Badge></Table.Td>
                    <Table.Td>
                        <Stack gap={4}>
                            <MultiSelect
                                data={[{ value: "1", label: "ABS/NBS Hanau–Würzburg/Fulda–Erfurt ✦" }]}
                                defaultValue={["1"]}
                            />
                            <Text size="xs" c="blue">✦ automatischer Vorschlag</Text>
                        </Stack>
                    </Table.Td>
                </Table.Tr>
                <Table.Tr>
                    <Table.Td>
                        <Text size="sm" fw={500}>B0113 · ABS München–Mühldorf–Freilassing</Text>
                    </Table.Td>
                    <Table.Td><Badge variant="light" color="teal">Änd.</Badge></Table.Td>
                    <Table.Td>
                        <MultiSelect data={PROJECT_OPTIONS} defaultValue={["3"]} />
                    </Table.Td>
                </Table.Tr>
            </Table.Tbody>
        </Table>
    );
}

// --- VIB -------------------------------------------------------------------------

function VibImportFormExample() {
    return (
        <Stack gap="sm">
            <Text fw={600} size="md">Neuer Import</Text>
            <Group align="flex-end" gap="sm" wrap="wrap">
                <FileInput
                    label="PDF-Datei (Verkehrsinvestitionsbericht)"
                    placeholder="PDF auswählen..."
                    w={300}
                />
                <NumberInput label="Berichtsjahr" defaultValue={2025} w={120} />
                <NumberInput label="OCR: von Seite (optional)" placeholder="z. B. 45" w={180} />
                <NumberInput label="OCR: bis Seite (optional)" placeholder="z. B. 195" w={180} />
            </Group>
            <Group align="center" gap="xl">
                <Checkbox label="Kopf- und Fußzeilen ignorieren" defaultChecked />
                <Button>PDF parsen</Button>
            </Group>
            <Stack gap={4}>
                <Text size="sm">Seite 61 / 150</Text>
                <Progress value={41} size="sm" />
            </Stack>
        </Stack>
    );
}

function VibStructureRowExample() {
    return (
        <Stack gap="xs">
            <Group gap="xl">
                <div>
                    <Text size="xs" c="dimmed">Projekte erkannt</Text>
                    <Text fw={700} size="xl">78</Text>
                </div>
                <div>
                    <Text size="xs" c="dimmed">Berichtsjahr</Text>
                    <Text fw={700} size="xl">2025</Text>
                </div>
                <div>
                    <Text size="xs" c="dimmed">Drucksache</Text>
                    <Text fw={700} size="xl">21/1234</Text>
                </div>
                <div>
                    <Text size="xs" c="dimmed">Ohne PFA</Text>
                    <Text fw={700} size="xl" c="orange">3</Text>
                </div>
            </Group>
            <Text size="sm" fw={500} mt="xs">Zeile eines Vorhabens (Rohtext-Qualität &amp; Abschnitte):</Text>
            <Group gap={6} wrap="wrap">
                <ChronicleDataChip>3.2k</ChronicleDataChip>
                <ChronicleDataChip>4 PFA</ChronicleDataChip>
                <ChronicleDataChip>✓ Verk. Zielsetzung</ChronicleDataChip>
                <ChronicleDataChip>✓ Bauaktivitäten</ChronicleDataChip>
                <ChronicleDataChip>✓ Projektkenndaten</ChronicleDataChip>
                <ChronicleDataChip>✗ Teilinbetriebnahmen</ChronicleDataChip>
            </Group>
            <Text size="xs" c="blue">▼ Rohtext anzeigen</Text>
        </Stack>
    );
}

function VibReviewEntryExample() {
    return (
        <Stack gap="sm">
            <Group gap="xs" align="center">
                <Button variant="default" size="compact-xs">‹</Button>
                <Text size="sm" fw={500}>12 / 78</Text>
                <Button variant="default" size="compact-xs">›</Button>
                <Text fw={600} size="sm">ABS/NBS Hanau–Würzburg/Fulda–Erfurt</Text>
                <ChronicleDataChip>ABS</ChronicleDataChip>
                <ChronicleDataChip>KI</ChronicleDataChip>
            </Group>
            <Group gap="sm" align="flex-end">
                <MultiSelect
                    label="Projekte zuordnen"
                    data={PROJECT_OPTIONS}
                    defaultValue={["1"]}
                    style={{ flex: 1, minWidth: 200 }}
                />
                <ChronicleDataChip style={{ marginBottom: 6 }}>✓</ChronicleDataChip>
            </Group>
            <Group gap="lg">
                <Text size="sm" fw={500}>Projektstatus</Text>
                <Checkbox label="Planung" defaultChecked />
                <Checkbox label="Bau" defaultChecked />
                <Checkbox label="Abgeschlossen" />
            </Group>
            <Box>
                <Text size="sm" fw={600} mb={4}>PFA-Tabelle (2 Einträge)</Text>
                <Table withTableBorder withColumnBorders fz="xs">
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th>Nr.</Table.Th>
                            <Table.Th>Örtlichkeit</Table.Th>
                            <Table.Th>PFB</Table.Th>
                            <Table.Th>Baubeginn</Table.Th>
                            <Table.Th>IBM</Table.Th>
                            <Table.Th>Unterprojekt</Table.Th>
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        <Table.Tr>
                            <Table.Td>1</Table.Td>
                            <Table.Td>Gelnhausen–Wächtersbach</Table.Td>
                            <Table.Td>2023</Table.Td>
                            <Table.Td>2024</Table.Td>
                            <Table.Td>2029</Table.Td>
                            <Table.Td>
                                <Select size="xs" data={PROJECT_OPTIONS} defaultValue="2" w={220} />
                            </Table.Td>
                        </Table.Tr>
                        <Table.Tr>
                            <Table.Td>2</Table.Td>
                            <Table.Td>Wächtersbach–Fulda</Table.Td>
                            <Table.Td>–</Table.Td>
                            <Table.Td>–</Table.Td>
                            <Table.Td>–</Table.Td>
                            <Table.Td>
                                <Select
                                    size="xs"
                                    data={PROJECT_OPTIONS}
                                    placeholder="✦ PFA Gelnhausen–Wächtersbach"
                                    w={220}
                                />
                            </Table.Td>
                        </Table.Tr>
                    </Table.Tbody>
                </Table>
            </Box>
            <Group justify="flex-end" gap="sm">
                <Button variant="light" size="xs">Entwurf speichern</Button>
                <Button variant="outline" size="xs">Abbrechen</Button>
                <Button color="green" size="xs">Import bestätigen</Button>
            </Group>
        </Stack>
    );
}

// --- Medien / Presse ---------------------------------------------------------------

function MedienExtractFormExample() {
    return (
        <Card withBorder padding="md">
            <Stack gap="sm">
                <TextInput label="Artikel-URL" placeholder="https://…" readOnly />
                <Textarea
                    label="… oder Text einfügen"
                    placeholder="Artikeltext hier einfügen"
                    minRows={3}
                    readOnly
                />
                <Group justify="flex-end">
                    <Button>Extrahieren &amp; Entwurf anlegen</Button>
                </Group>
            </Stack>
        </Card>
    );
}

function MedienCardExample() {
    return (
        <Card withBorder padding="md">
            <Stack gap="sm">
                <Group gap="xs">
                    <Text fw={600}>Fuldaer Zeitung</Text>
                    <Text size="xs" c="dimmed">05.07.2026</Text>
                    <Anchor size="xs">↗ Artikel öffnen</Anchor>
                </Group>
                <Text size="sm" fs="italic" c="dimmed">
                    „Für den Abschnitt Gelnhausen–Wächtersbach haben die Bauarbeiten offiziell
                    begonnen."
                </Text>
                <Group grow align="flex-end">
                    <Select
                        label="Phase"
                        data={[{ value: "BAU", label: "Bau" }]}
                        defaultValue="BAU"
                    />
                    <Select label="Projekt" data={PROJECT_OPTIONS} defaultValue="2" />
                </Group>
                <Switch label="Als Beobachtung übernehmen (bestätigt)" defaultChecked />
            </Stack>
        </Card>
    );
}

// --- Projekt anlegen ------------------------------------------------------------------

function ProjektWizardExample() {
    return (
        <Stack gap="md">
            <Stepper active={0} size="sm">
                <Stepper.Step label="Stammdaten" description="Pflicht" />
                <Stepper.Step label="Geometrie" description="Optional" />
                <Stepper.Step label="Eigenschaften" description="Optional" />
                <Stepper.Step label="Planungsstand" description="Optional" />
                <Stepper.Step label="FinVes" description="Optional" />
                <Stepper.Step label="VIB" description="Optional" />
            </Stepper>
            <Group justify="space-between">
                <Button variant="subtle" size="xs">Zurück</Button>
                <Group gap="xs">
                    <Button variant="default" size="xs">Weiter</Button>
                    <Button variant="subtle" size="xs">Als Entwurf speichern</Button>
                    <Button size="xs">Projekt fertigstellen</Button>
                </Group>
            </Group>
        </Stack>
    );
}

function ProjektStammdatenExample() {
    return (
        <Stack gap="sm">
            <TextInput label="Projektname" required defaultValue="ABS Musterstadt–Beispielheim" />
            <TextInput label="Projektnummer" placeholder="z. B. ABS 123" readOnly />
            <Textarea label="Beschreibung" minRows={2} readOnly />
            <Select
                label="Übergeordnetes Projekt"
                data={PROJECT_OPTIONS}
                placeholder="Projekt suchen…"
            />
            <MultiSelect
                label="Projektgruppen"
                data={[{ value: "1", label: "Bedarfsplan Schiene" }]}
                defaultValue={["1"]}
            />
            <Group justify="flex-end">
                <Button>Projekt anlegen</Button>
            </Group>
        </Stack>
    );
}

// --- Geometrie -------------------------------------------------------------------------

function GeometriePanelExample() {
    return (
        <Group align="flex-start" gap="md" wrap="nowrap">
            <Stack gap="sm" style={{ width: 300, flexShrink: 0 }}>
                <Divider label="Zeichnen" labelPosition="left" />
                <Button.Group>
                    <Button size="xs" variant="default">Linie zeichnen</Button>
                    <Button size="xs" variant="default">Punkt setzen</Button>
                    <Button size="xs" variant="default">Bearbeiten</Button>
                    <Button size="xs" variant="default">Fertig</Button>
                </Button.Group>
                <Divider label="Route berechnen" labelPosition="left" />
                <Select label="Startbahnhof" data={["Hanau Hbf"]} defaultValue="Hanau Hbf" size="xs" />
                <Select label="Zielbahnhof" data={["Fulda"]} defaultValue="Fulda" size="xs" />
                <Button size="xs">Route berechnen</Button>
                <Divider label="Betriebsstellen hinzufügen" labelPosition="left" />
                <Select label="Betriebsstelle suchen" data={[]} placeholder="Suchen…" size="xs" />
                <Divider label="Oder: GeoJSON hochladen" labelPosition="left" />
                <FileInput label="GeoJSON-Datei" placeholder="Datei auswählen…" size="xs" />
                <Button mt="xs">Geometrie speichern</Button>
            </Stack>
            <Box
                style={{
                    flex: 1,
                    minWidth: 220,
                    height: 320,
                    borderRadius: 8,
                    background: "var(--mantine-color-gray-1)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                }}
            >
                <Text size="sm" c="dimmed">Kartenvorschau (bestehende + neue Geometrie)</Text>
            </Box>
        </Group>
    );
}

export const GUIDE_EXAMPLES: Record<string, ReactNode> = {
    "geometrie-panel": <GeometriePanelExample />,
    "projektfortschritt-stepper": <ProgressStepperExample />,
    "fulda-year-table": <FuldaYearTableExample />,
    "bauportal-table": <BauportalTableExample />,
    "haushalt-review": <HaushaltReviewExample />,
    "vib-import-form": <VibImportFormExample />,
    "vib-structure": <VibStructureRowExample />,
    "vib-review-entry": <VibReviewEntryExample />,
    "medien-extract-form": <MedienExtractFormExample />,
    "medien-card": <MedienCardExample />,
    "projekt-wizard": <ProjektWizardExample />,
    "projekt-stammdaten": <ProjektStammdatenExample />,
};
