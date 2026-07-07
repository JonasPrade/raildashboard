import { Accordion, Alert, Anchor, Box, Container, Group, List, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { ChronicleHeadline, ChronicleDataChip } from "../../components/chronicle";

const STEPS: { nr: string; title: string; content: React.ReactNode }[] = [
    {
        nr: "1",
        title: "Das richtige PDF beschaffen",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Quelle ist die <strong>Antwort der Bundesregierung</strong> auf die Kleine Anfrage
                    zur „Fulda-Runde" (eine Bundestagsdrucksache). Nur die <em>Antwort</em> enthält die
                    Projektlisten — <strong>nicht</strong> die Anfrage selbst.
                </Text>
                <Alert color="yellow" variant="light" title="Wichtig">
                    Die Antwort listet pro nummerierter Frage eine Projektliste. Aus der
                    Frage-Überschrift (z. B. „… in Vorplanung", „… mit abgeschlossener
                    Genehmigungsplanung") wird die Leistungsphase abgeleitet — lade daher immer das
                    vollständige Antwort-PDF hoch, damit die Fragennummern erhalten bleiben.
                </Alert>
            </Stack>
        ),
    },
    {
        nr: "2",
        title: "Hochladen und auswerten",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Gehe zu <Anchor component={Link} to="/admin/fulda-import">Fulda-Runde</Anchor>.
                </Text>
                <List size="sm" spacing="xs" type="ordered">
                    <List.Item>
                        Trage das <strong>Jahr der Fulda-Runde</strong> ein (Jahrgang der Drucksache).
                    </List.Item>
                    <List.Item>
                        Wähle das <strong>Antwort-PDF</strong> aus und klicke auf
                        <strong> „Auswerten &amp; durcharbeiten"</strong>.
                    </List.Item>
                    <List.Item>
                        Der Server liest das PDF per <strong>OCR</strong> und ordnet jede Projektliste
                        per <strong>KI</strong> anhand der <strong>Fragennummer</strong> einer
                        Leistungsphase zu (inkl. Abschnitt → Unterprojekt).
                    </List.Item>
                    <List.Item>
                        Nach Abschluss erscheint eine Meldung mit Anzahl erkannter Einträge und
                        OCR-Status, und du landest automatisch auf der Jahrgangs-Seite.
                    </List.Item>
                </List>
                <Alert color="blue" variant="light" title="Zuordnung nach Fragennummer">
                    Die Phase wird über die Nummer der Frage bestimmt, nicht frei „geraten". Dadurch
                    bleibt die Zuordnung stabil, auch wenn Formulierungen variieren.
                </Alert>
            </Stack>
        ),
    },
    {
        nr: "3",
        title: "Den Jahrgang durcharbeiten",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Die Jahrgangs-Seite listet alle erkannten Einträge, gruppiert nach Kategorie
                    (Leistungsphase). Jeder Eintrag zeigt den Rohnamen und ggf. den Abschnitt.
                    Pro Eintrag:
                </Text>
                <List size="sm" spacing="xs" type="ordered">
                    <List.Item>
                        Ordne über das Auswahlfeld ein oder mehrere <strong>Projekte</strong> zu.
                        Das <ChronicleDataChip>✦</ChronicleDataChip>-Symbol markiert einen
                        automatischen Vorschlag (Fuzzy-Matching über den Namen) — bitte prüfen.
                    </List.Item>
                    <List.Item>
                        Findet sich kein passendes Projekt, kannst du direkt einen
                        <strong> Projekt-Entwurf</strong> anlegen und ihn später fertigstellen.
                    </List.Item>
                    <List.Item>
                        Ein Eintrag lässt sich <strong>bestätigen</strong>, sobald mindestens ein
                        Projekt zugeordnet ist. Offene und aktive (bestätigte) Einträge zeigt die
                        Übersicht als Badges („X aktiv", „Y offen").
                    </List.Item>
                </List>
                <Text size="sm">
                    Ein einmal ausgewerteter Jahrgang lässt sich jederzeit über die Jahrgangs-Tabelle
                    erneut öffnen und weiterbearbeiten — du musst nicht alles in einem Rutsch erledigen.
                </Text>
            </Stack>
        ),
    },
    {
        nr: "4",
        title: "Was beim Bestätigen passiert",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Jede bestätigte Zuordnung erzeugt pro Projekt eine <strong>Beobachtung</strong>
                    mit der Quelle <ChronicleDataChip>Fulda-Runde</ChronicleDataChip> (Phase +
                    Jahrgangsdatum). Diese fließt in die{" "}
                    <Anchor component={Link} to="/admin/anleitungen/projektfortschritt">
                        Ableitung des Planungsstands
                    </Anchor>{" "}
                    ein — je nach Konfidenz und Aktualität gegenüber den anderen Quellen.
                </Text>
                <Text size="sm">
                    Historische Jahrgänge bleiben erhalten; ein neuer Jahrgang ergänzt die Historie,
                    statt sie zu überschreiben.
                </Text>
            </Stack>
        ),
    },
];

export default function FuldaGuidePage() {
    return (
        <Container size="md" py="xl">
            <Stack gap="xl">
                <Stack gap="xs">
                    <Anchor component={Link} to="/admin/anleitungen" size="sm">
                        ← Alle Anleitungen
                    </Anchor>
                    <Group gap="xs" align="center">
                        <ChronicleHeadline as="h1">Anleitung: Fulda-Runde anlegen</ChronicleHeadline>
                        <ChronicleDataChip>Schritt für Schritt</ChronicleDataChip>
                    </Group>
                    <Text c="dimmed" size="sm">
                        Wie du eine Antwort der Bundesregierung auf die „Fulda-Runde" auswertest und
                        den Jahrgang den Projekten zuordnest.
                    </Text>
                </Stack>

                <Alert color="green" variant="light" title="Voraussetzungen">
                    <List size="sm" mt="xs" spacing={4}>
                        <List.Item>Du bist als <strong>Editor</strong> oder <strong>Admin</strong> eingeloggt (Recht „Planungsstand bearbeiten").</List.Item>
                        <List.Item>Das Antwort-PDF der Kleinen Anfrage liegt vor.</List.Item>
                        <List.Item>OCR und KI-Extraktion sind serverseitig konfiguriert (OCR- und LLM-Zugang).</List.Item>
                    </List>
                </Alert>

                <Accordion variant="separated" radius="md" defaultValue="step-1">
                    {STEPS.map((step) => (
                        <Accordion.Item key={step.nr} value={`step-${step.nr}`}>
                            <Accordion.Control>
                                <Group gap="sm" align="center">
                                    <ChronicleDataChip>{step.nr}</ChronicleDataChip>
                                    <Text fw={500}>{step.title}</Text>
                                </Group>
                            </Accordion.Control>
                            <Accordion.Panel>
                                <Box pl="md" pt="xs" pb="xs">
                                    {step.content}
                                </Box>
                            </Accordion.Panel>
                        </Accordion.Item>
                    ))}
                </Accordion>

                <Accordion variant="contained" radius="md">
                    <Accordion.Item value="wrong-pdf">
                        <Accordion.Control>
                            <Text size="sm" fw={500}>Es werden keine oder kaum Einträge erkannt</Text>
                        </Accordion.Control>
                        <Accordion.Panel>
                            <Text size="sm">
                                Meist wurde die <strong>Anfrage</strong> statt der <strong>Antwort</strong>
                                {" "}hochgeladen, oder das PDF ist ein reiner Scan ohne verwertbaren Text.
                                Prüfe, dass es sich um die Antwort der Bundesregierung mit nummerierten
                                Fragen und Projektlisten handelt.
                            </Text>
                        </Accordion.Panel>
                    </Accordion.Item>
                    <Accordion.Item value="wrong-phase">
                        <Accordion.Control>
                            <Text size="sm" fw={500}>Ein Eintrag hat die falsche Leistungsphase</Text>
                        </Accordion.Control>
                        <Accordion.Panel>
                            <Text size="sm">
                                Die Phase folgt der Fragennummer im PDF. Weicht sie ab, stimmt
                                vermutlich die Zuordnung Frage → Phase für diesen Jahrgang nicht — in
                                dem Fall die Zuordnung nicht bestätigen und einen Administrator
                                hinzuziehen.
                            </Text>
                        </Accordion.Panel>
                    </Accordion.Item>
                </Accordion>
            </Stack>
        </Container>
    );
}
