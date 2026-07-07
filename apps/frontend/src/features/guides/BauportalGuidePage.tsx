import { Accordion, Alert, Anchor, Box, Container, Group, List, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { ChronicleHeadline, ChronicleDataChip } from "../../components/chronicle";

const STEPS: { nr: string; title: string; content: React.ReactNode }[] = [
    {
        nr: "1",
        title: "Aktuellen Stand abrufen",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Gehe zu <Anchor component={Link} to="/admin/bauportal-import">DB-Bauportal</Anchor>{" "}
                    und klicke auf <strong>„Bauportal abrufen"</strong>. Das Dashboard holt die
                    aktuellen Einträge aus der offenen Bauportal-API der Deutschen Bahn.
                </Text>
                <Text size="sm">
                    Die Meldung nach dem Abruf zeigt, wie viele Einträge insgesamt geholt, neu
                    angelegt und aktualisiert wurden. Ein erneuter Abruf ist jederzeit möglich und
                    aktualisiert bestehende Einträge (Status/Zeitangaben), ohne deine bestätigten
                    Zuordnungen zu verlieren.
                </Text>
            </Stack>
        ),
    },
    {
        nr: "2",
        title: "Vorschläge prüfen und Projekte zuordnen",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Die Tabelle zeigt pro Bauportal-Eintrag: den Kurztitel (mit Link zum Bauportal),
                    die abgeleitete <strong>Phase</strong>, den Bauzeitraum und ein Feld zur
                    Projektzuordnung.
                </Text>
                <List size="sm" spacing="xs">
                    <List.Item>
                        Die Phase wird aus dem Bauportal-Status gemappt (z. B.{" "}
                        <ChronicleDataChip>Bau</ChronicleDataChip>,{" "}
                        <ChronicleDataChip>In Betrieb</ChronicleDataChip>). Steht dort
                        <strong> „kein Beitrag"</strong>, liefert der Status keine verwertbare Phase —
                        solche Einträge müssen nicht übernommen werden.
                    </List.Item>
                    <List.Item>
                        Ein <ChronicleDataChip>✦</ChronicleDataChip>-Vorschlag ist bereits vorbelegt.
                        Prüfe ihn, passe ihn im Auswahlfeld an oder entferne ihn.
                    </List.Item>
                    <List.Item>
                        Gibt es das Projekt noch nicht, kannst du direkt einen
                        <strong> Projekt-Entwurf</strong> anlegen; er wird dem Eintrag zugeordnet und
                        bleibt zunächst unbestätigt.
                    </List.Item>
                    <List.Item>
                        Mit dem Schalter <strong>„Nur offene (unbestätigt)"</strong> blendest du bereits
                        übernommene Einträge aus, um den Rest abzuarbeiten.
                    </List.Item>
                </List>
            </Stack>
        ),
    },
    {
        nr: "3",
        title: "Übernehmen",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Mit <strong>„Alle übernehmen (N)"</strong> bestätigst du auf einen Schlag alle
                    zugeordneten, noch offenen Einträge. N zeigt an, wie viele bereit sind (zugeordnet
                    und unbestätigt). Zuordnungen lassen sich auch nach dem Übernehmen weiter anpassen.
                </Text>
                <Alert color="blue" variant="light" title="Was dabei entsteht">
                    Jede bestätigte Zuordnung erzeugt eine abgeleitete <strong>Beobachtung</strong> mit
                    der Quelle <ChronicleDataChip>Bauportal</ChronicleDataChip>. Wie stark sie den
                    angezeigten Stand beeinflusst, entscheidet die{" "}
                    <Anchor component={Link} to="/admin/anleitungen/projektfortschritt">
                        glaubwürdigkeitsbasierte Ableitung
                    </Anchor>{" "}
                    (Vertrauen je Quelle × Aktualität).
                </Alert>
            </Stack>
        ),
    },
];

export default function BauportalGuidePage() {
    return (
        <Container size="md" py="xl">
            <Stack gap="xl">
                <Stack gap="xs">
                    <Anchor component={Link} to="/admin/anleitungen" size="sm">
                        ← Alle Anleitungen
                    </Anchor>
                    <Group gap="xs" align="center">
                        <ChronicleHeadline as="h1">Anleitung: DB-Bauportal abrufen</ChronicleHeadline>
                        <ChronicleDataChip>Schritt für Schritt</ChronicleDataChip>
                    </Group>
                    <Text c="dimmed" size="sm">
                        Wie du den aktuellen Bau- und Planungsstand aus der offenen Bauportal-API der
                        Deutschen Bahn abrufst, prüfst und den Projekten zuordnest.
                    </Text>
                </Stack>

                <Alert color="green" variant="light" title="Voraussetzungen">
                    <List size="sm" mt="xs" spacing={4}>
                        <List.Item>Du bist als <strong>Editor</strong> oder <strong>Admin</strong> eingeloggt (Recht „Planungsstand bearbeiten").</List.Item>
                        <List.Item>Die Bauportal-API ist vom Server aus erreichbar.</List.Item>
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
                    <Accordion.Item value="api-down">
                        <Accordion.Control>
                            <Text size="sm" fw={500}>„Abruf fehlgeschlagen — API nicht erreichbar"</Text>
                        </Accordion.Control>
                        <Accordion.Panel>
                            <Text size="sm">
                                Die Bauportal-API antwortet nicht (temporär offline oder vom Server aus
                                nicht erreichbar). Später erneut versuchen; besteht das Problem fort,
                                einen Administrator hinzuziehen.
                            </Text>
                        </Accordion.Panel>
                    </Accordion.Item>
                    <Accordion.Item value="no-phase">
                        <Accordion.Control>
                            <Text size="sm" fw={500}>Ein Eintrag zeigt „kein Beitrag"</Text>
                        </Accordion.Control>
                        <Accordion.Panel>
                            <Text size="sm">
                                Der Bauportal-Status lässt sich nicht auf eine Leistungsphase abbilden
                                (z. B. rein informative Einträge). Solche Zeilen liefern keine sinnvolle
                                Beobachtung und können offen bleiben.
                            </Text>
                        </Accordion.Panel>
                    </Accordion.Item>
                </Accordion>
            </Stack>
        </Container>
    );
}
