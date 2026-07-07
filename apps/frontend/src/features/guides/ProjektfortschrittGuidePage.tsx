import { Accordion, Alert, Anchor, Box, Container, Group, List, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { ChronicleHeadline, ChronicleDataChip } from "../../components/chronicle";

const SECTIONS: { nr: string; title: string; content: React.ReactNode }[] = [
    {
        nr: "1",
        title: "Grundprinzip: abgeleitet, nicht eingetragen",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Ein Projekt hat <strong>kein</strong> einzelnes „Status"-Feld, das man von Hand
                    setzt. Stattdessen sammelt das Dashboard <strong>Beobachtungen</strong> aus
                    mehreren Quellen und leitet daraus einen angezeigten Planungsstand ab. So bleiben
                    widersprüchliche Quellen sichtbar, statt sich gegenseitig zu überschreiben.
                </Text>
                <Text size="sm">
                    Jede Beobachtung ist ein Tupel aus <em>Quelle, Spur, behaupteter Zustand,
                    Beobachtungsdatum und Konfidenz</em>. Der angezeigte Stand („Headline") ist immer
                    das Ergebnis einer Ableitung über alle Beobachtungen — nie ein direkt gespeicherter Wert.
                </Text>
            </Stack>
        ),
    },
    {
        nr: "2",
        title: "Die Leistungsphasen (Hauptspur)",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Die Hauptspur ist eine lineare, immer vorhandene Kette von fünf Phasen:
                </Text>
                <List size="sm" spacing={4}>
                    <List.Item><ChronicleDataChip>Nicht gestartet</ChronicleDataChip></List.Item>
                    <List.Item><ChronicleDataChip>Vorplanung</ChronicleDataChip> (Lph 1–2)</List.Item>
                    <List.Item><ChronicleDataChip>Genehmigungsplanung</ChronicleDataChip> (Lph 3–4)</List.Item>
                    <List.Item><ChronicleDataChip>Bau</ChronicleDataChip></List.Item>
                    <List.Item><ChronicleDataChip>In Betrieb</ChronicleDataChip> (faktisch abgeschlossen, grün)</List.Item>
                </List>
                <Text size="sm">
                    Dargestellt als horizontaler Verlauf mit Kreisen und Pfeilen. Manuelle
                    Beobachtungen erfassen <strong>ausschließlich</strong> diese Leistungsphasen.
                </Text>
            </Stack>
        ),
    },
    {
        nr: "3",
        title: "Begleitende Verfahren: Planfeststellung & Parl. Befassung",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Zwei Verfahren laufen parallel zur Hauptspur und werden als
                    <strong> Meilenstein-Rauten</strong> auf der Zeitleiste angezeigt
                    (grün = abgeschlossen + Datum, blau = läuft, Umriss = offen):
                </Text>
                <List size="sm" spacing="xs">
                    <List.Item>
                        <strong>Planfeststellung (PFB)</strong> — Raute zwischen Genehmigungsplanung
                        und Bau (das rechtliche Tor zum Bau). Nur sichtbar, wenn „hat PF" gesetzt ist;
                        das Flag setzt sich <em>automatisch</em>, sobald PF-Daten (Zustand/Datum/Link)
                        erfasst werden.
                    </List.Item>
                    <List.Item>
                        <strong>Parlamentarische Befassung</strong> — Raute zwischen Vorplanung und
                        Genehmigungsplanung. Voreinstellung kommt aus der Projektgruppe
                        (Bedarfsplan Schiene / BSWAG → an), manuell übersteuerbar.
                    </List.Item>
                </List>
                <Alert color="blue" variant="light" title="Wo erfassen?">
                    Beide Verfahren pflegst du im Bearbeiten-Drawer über das Schaltmenü
                    „Verfahren" (Switch je Verfahren, mit Zustand, Datum, Anmerkung und Links) —
                    <strong> nicht</strong> über eine manuelle Beobachtung.
                </Alert>
            </Stack>
        ),
    },
    {
        nr: "4",
        title: "Woher die Beobachtungen kommen (Quellen)",
        content: (
            <Stack gap="xs">
                <Text size="sm">Es gibt sechs Quellentypen:</Text>
                <List size="sm" spacing="xs">
                    <List.Item>
                        <ChronicleDataChip>VIB</ChronicleDataChip> und{" "}
                        <ChronicleDataChip>FinVe</ChronicleDataChip> — bereits importiert und m:n mit
                        Projekten verknüpft; Beobachtungen werden daraus <em>automatisch abgeleitet</em>.
                    </List.Item>
                    <List.Item>
                        <ChronicleDataChip>Fulda-Runde</ChronicleDataChip>,{" "}
                        <ChronicleDataChip>Bauportal</ChronicleDataChip> und{" "}
                        <ChronicleDataChip>Medien</ChronicleDataChip> — werden über die jeweiligen
                        Import-Workflows gepflegt (siehe Anleitungen).
                    </List.Item>
                    <List.Item>
                        <ChronicleDataChip>Manuell</ChronicleDataChip> — redaktionelle Beobachtung,
                        die du direkt am Projekt erfasst (Phase + Datum, optional als „erwartet").
                    </List.Item>
                </List>
            </Stack>
        ),
    },
    {
        nr: "5",
        title: "Wie der angezeigte Stand entsteht (Hybrid-Ableitung)",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Maßgeblich ist die <strong>glaubwürdigste</strong> Beobachtung: Unter allen
                    Hauptspur-Beobachtungen über der Glaubwürdigkeitsschwelle gewinnt die mit der
                    <strong> höchsten effektiven Konfidenz</strong> — ihre Phase wird zur Headline.
                    Entscheidend ist die Konfidenz, <em>nicht</em> die Phasen-Reihenfolge.
                </Text>
                <Text size="sm">
                    Die effektive Konfidenz = Default-Vertrauen je Quellentyp × Aktualitätsverfall
                    (<em>recency decay</em>). Deshalb verliert der „immer veraltete" VIB mit der Zeit
                    an Gewicht, und eine frische redaktionelle Korrektur schlägt ein schwaches
                    Automatik-Signal.
                </Text>
                <Alert color="yellow" variant="light" title="Bewusster Trade-off">
                    Ein frisches, schwach gewichtetes Signal kann ein älteres, höheres überstimmen —
                    der abgeleitete Stand kann für Automatik-Quellen also auch „zurückgehen". Das ist
                    gewollt, damit aktuelle und menschliche Eingaben maßgeblich bleiben. Konflikte
                    werden nie weggerechnet, sondern im Aufklappbereich transparent gezeigt.
                </Alert>
            </Stack>
        ),
    },
    {
        nr: "6",
        title: "Lebenszyklus-Overlay: aktiv / pausiert / abgebrochen",
        content: (
            <Text size="sm">
                Orthogonal zur Phasenkette liegt ein Lebenszyklus-Zustand
                (<ChronicleDataChip>Aktiv</ChronicleDataChip> /{" "}
                <ChronicleDataChip>Pausiert</ChronicleDataChip> /{" "}
                <ChronicleDataChip>Abgebrochen</ChronicleDataChip>). Er wird nicht in die Phasen
                gemischt. Bei „Pausiert"/„Abgebrochen" wird die gesamte Darstellung überblendet
                (Banner + abgeblendeter Stepper); die zuletzt bekannte Phase bleibt erhalten.
            </Text>
        ),
    },
    {
        nr: "7",
        title: "Unterprojekte & Aggregation",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Projekte mit mehreren Planfeststellungsabschnitten sind als
                    <strong> Unterprojekte</strong> modelliert. Der Fortschritt hängt immer am
                    <strong> Blatt-Projekt</strong> (genau ein Stand). Ein übergeordnetes Projekt
                    <strong> aggregiert</strong> seine Kinder und zeigt die Headline als
                    <strong> Spanne</strong> (min..max über alle erreichbaren Blätter).
                </Text>
                <List size="sm" spacing="xs">
                    <List.Item>Die Aggregation ist <strong>rekursiv</strong> über den ganzen Teilbaum (beliebige Tiefe), nicht nur eine Ebene.</List.Item>
                    <List.Item>Nur echte Blätter tragen einen Zustand; Zwischenknoten spannen die Blätter unter sich.</List.Item>
                    <List.Item>Ein <strong>manueller Override an einem Zwischenknoten</strong> fixiert den gesamten Teilbaum auf diese eine Phase.</List.Item>
                    <List.Item>Ein direktes Kind, das selbst Superior ist, zeigt seine eigene Sub-Spanne (Badge „Gruppe").</List.Item>
                </List>
            </Stack>
        ),
    },
    {
        nr: "8",
        title: "Prognose & erwartete Termine",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Neben dem aktuellen Stand zeigt der Aufklappbereich eine <strong>Prognose</strong>
                    (Restdauer der aktuellen Phase + nächste Schritte). Konkrete Termine aus VIB-PFA
                    und Fulda speisen die Prognose.
                </Text>
                <Text size="sm">
                    Eine manuelle Beobachtung kannst du als <strong>„erwartet"</strong> markieren
                    (Phase + Datum). Erwartete Einträge fließen <strong>nicht</strong> in die Headline
                    ein (sie verändern den heutigen Stand nicht), sondern übersteuern nur die Prognose.
                </Text>
            </Stack>
        ),
    },
    {
        nr: "9",
        title: "Wie du selbst eingreifst",
        content: (
            <List size="sm" spacing="xs">
                <List.Item>
                    <strong>Manuelle Beobachtung</strong> (Phase + Datum, optional „erwartet") am
                    Projekt erfassen — hohe Konfidenz, schlägt bei Bedarf Automatik-Signale.
                </List.Item>
                <List.Item>
                    <strong>Phasen-Override</strong> setzen, wenn der abgeleitete Vorschlag falsch ist
                    — an einem Zwischenknoten fixiert er den ganzen Teilbaum.
                </List.Item>
                <List.Item>
                    <strong>Verfahren-Drawer</strong> für Planfeststellung / Parl. Befassung pflegen.
                </List.Item>
                <List.Item>
                    Neue Quelldaten über die Import-Workflows einspielen:{" "}
                    <Anchor component={Link} to="/admin/haushalt-import/guide">Haushalt</Anchor>,{" "}
                    <Anchor component={Link} to="/admin/anleitungen/fulda">Fulda-Runde</Anchor>,{" "}
                    <Anchor component={Link} to="/admin/anleitungen/bauportal">Bauportal</Anchor>.
                </List.Item>
            </List>
        ),
    },
];

export default function ProjektfortschrittGuidePage() {
    return (
        <Container size="md" py="xl">
            <Stack gap="xl">
                <Stack gap="xs">
                    <Anchor component={Link} to="/admin/anleitungen" size="sm">
                        ← Alle Anleitungen
                    </Anchor>
                    <Group gap="xs" align="center">
                        <ChronicleHeadline as="h1">So funktioniert der Projektfortschritt</ChronicleHeadline>
                        <ChronicleDataChip>Grundlagen</ChronicleDataChip>
                    </Group>
                    <Text c="dimmed" size="sm">
                        Das mentale Modell hinter dem Planungsstand: Wie aus mehreren, teils
                        widersprüchlichen Quellen ein nachvollziehbarer, angezeigter Stand entsteht —
                        und wo du eingreifen kannst.
                    </Text>
                </Stack>

                <Accordion variant="separated" radius="md" defaultValue="step-1">
                    {SECTIONS.map((s) => (
                        <Accordion.Item key={s.nr} value={`step-${s.nr}`}>
                            <Accordion.Control>
                                <Group gap="sm" align="center">
                                    <ChronicleDataChip>{s.nr}</ChronicleDataChip>
                                    <Text fw={500}>{s.title}</Text>
                                </Group>
                            </Accordion.Control>
                            <Accordion.Panel>
                                <Box pl="md" pt="xs" pb="xs">
                                    {s.content}
                                </Box>
                            </Accordion.Panel>
                        </Accordion.Item>
                    ))}
                </Accordion>
            </Stack>
        </Container>
    );
}
