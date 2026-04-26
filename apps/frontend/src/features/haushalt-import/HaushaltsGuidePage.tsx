import {
    Accordion,
    Alert,
    Anchor,
    Box,
    Container,
    Group,
    List,
    Stack,
    Text,
} from "@mantine/core";
import { ChronicleHeadline, ChronicleDataChip } from "../../components/chronicle";
import { Link } from "react-router-dom";

const STEPS: { title: string; nr: string; content: React.ReactNode }[] = [
    {
        nr: "1",
        title: "PDF-Datei beschaffen",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Die Quelldatei ist die <strong>Anlage VWIB, Teil B</strong> des Bundeshaushalts –
                    ein Dokument mit dem Titel „Bedarfsplanmaßnahmen Schienenwegeinvestitionsprogramm".
                </Text>
                <Text size="sm">
                    Diese Anlage wird jährlich zusammen mit dem Bundeshaushaltsentwurf veröffentlicht
                    (in der Regel im Frühjahr). Das aktuelle PDF kann über die offizielle
                    Seite des Bundesministeriums der Finanzen oder direkt aus dem Haushaltssystem bezogen werden.
                </Text>
                <Alert color="yellow" variant="light" title="Wichtig">
                    Es darf nur die offizielle Teil-B-Anlage (VWIB) verwendet werden – nicht die Gesamtanlage
                    oder andere Bundeshaushalt-PDFs. Das Format der Tabelle ist spezifisch und unterscheidet
                    sich stark von anderen Anhängen.
                </Alert>
            </Stack>
        ),
    },
    {
        nr: "2",
        title: "PDF hochladen und parsen",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Gehe zu <Anchor component={Link} to="/admin/haushalt-import">Haushalts-Import</Anchor>.
                </Text>
                <List size="sm" spacing="xs" type="ordered">
                    <List.Item>
                        Klicke auf „PDF auswählen…" und wähle die heruntergeladene VWIB-Teil-B-Datei aus.
                    </List.Item>
                    <List.Item>
                        Trage das <strong>Haushaltsjahr</strong> ein (z. B. 2026). Dieses Jahr wird
                        für die Zuordnung der Sammel-FinVes genutzt und sollte dem Jahr des PDFs entsprechen.
                    </List.Item>
                    <List.Item>
                        Klicke auf <strong>„PDF parsen"</strong>. Der Server extrahiert die Tabelle
                        mit pdfplumber und analysiert alle Zeilen im Hintergrund.
                    </List.Item>
                    <List.Item>
                        Während des Parsens wird ein Fortschrittsbalken angezeigt
                        (Seite X / Gesamtseiten, Anzahl gefundener Zeilen).
                        Bei großen PDFs kann das einige Sekunden dauern.
                    </List.Item>
                    <List.Item>
                        Nach Abschluss wird die Seite automatisch zur Ergebnis-Überprüfung weitergeleitet.
                    </List.Item>
                </List>
                <Alert color="blue" variant="light" title="Hinweis">
                    Der Parser ist auf das 2026-Format kalibriert (zusammengeführte erste drei Spalten,
                    mehrzeilige Zellen, Kap./Titel-Unterzeilen). Ältere PDFs können abweichende Strukturen haben.
                </Alert>
            </Stack>
        ),
    },
    {
        nr: "3",
        title: "Phase 1: Reguläre FinVes prüfen und zuordnen",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Die Ergebnis-Tabelle zeigt alle erkannten FinVes (Finanzierungsvereinbarungen)
                    mit ihrem Status:
                </Text>
                <List size="sm" spacing="xs">
                    <List.Item>
                        <ChronicleDataChip>Neu</ChronicleDataChip>{" "}
                        — FinVe wurde noch nie importiert, wird neu angelegt.
                    </List.Item>
                    <List.Item>
                        <ChronicleDataChip>Aktualisiert</ChronicleDataChip>{" "}
                        — FinVe existiert bereits, Budgetdaten werden ergänzt.
                    </List.Item>
                    <List.Item>
                        <ChronicleDataChip>Unbekannt</ChronicleDataChip>{" "}
                        — FinVe konnte keinem Projekt zugeordnet werden.
                    </List.Item>
                </List>
                <Text size="sm">
                    Pro Zeile kann über das <strong>MultiSelect-Feld</strong> ein oder mehrere Projekte
                    aus der Datenbank zugeordnet werden. Der Fuzzy-Matching-Algorithmus schlägt automatisch
                    passende Projekte vor (Symbol ✦). Die Vorschläge basieren auf dem Namen der FinVe.
                </Text>
                <Text size="sm">
                    Zuordnungen können auch leer gelassen werden – die FinVe wird trotzdem importiert,
                    bleibt aber unverknüpft und erscheint später in der Unmatched-Liste.
                </Text>
            </Stack>
        ),
    },
    {
        nr: "4",
        title: "Phase 2: Sammel-FinVes prüfen",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Sammelfinanzierungsvereinbarungen (SV-FinVes) enthalten nicht eine einzelne Maßnahme,
                    sondern bündeln viele kleinere Projekte. Sie werden im PDF durch eine
                    <strong> YYY-Projektnummer</strong> (statt dem üblichen B-Prefix) und einen
                    <em> Erläuterungstext</em> mit eingerückten Einzelprojekten gekennzeichnet.
                </Text>
                <Text size="sm">
                    Im Review-Bereich „Sammel-FinVes (Phase 2)" erscheint für jede SV-FinVe
                    eine Liste der erkannten Unterzeilen (aus dem Erläuterungstext). Pro Unterzeile
                    kann ein Projekt zugeordnet werden:
                </Text>
                <List size="sm" spacing="xs" type="ordered">
                    <List.Item>
                        Das ✦-Symbol zeigt einen automatischen Vorschlag basierend auf dem Projektnamen.
                    </List.Item>
                    <List.Item>
                        Weitere Projekte können über „+ weitere Projekte" manuell ergänzt werden,
                        falls nicht alle erkannt wurden.
                    </List.Item>
                    <List.Item>
                        Die Zuordnung gilt nur für das aktuelle Haushaltsjahr – historische Zuordnungen
                        aus Vorjahren bleiben erhalten.
                    </List.Item>
                </List>
                <Alert color="blue" variant="light" title="Hinweis">
                    SV-FinVes können bei Seitenumbrüchen im PDF gesplittet sein. Der Parser erkennt
                    und verbindet diese automatisch über einen Raw-Text-Scan. Falls Unterzeilen fehlen,
                    kann der Erläuterungstext im Original-PDF verglichen werden.
                </Alert>
            </Stack>
        ),
    },
    {
        nr: "5",
        title: "Import bestätigen und Nachbearbeitung",
        content: (
            <Stack gap="xs">
                <Text size="sm">
                    Klicke auf <strong>„Importieren"</strong>, um alle Daten in die Datenbank zu übernehmen.
                    Nach dem Import erscheint eine Bestätigung und du wirst zur Übersicht weitergeleitet.
                </Text>
                <Text size="sm">
                    FinVes ohne Projektzuordnung werden als <em>unmatched</em> gespeichert und können
                    unter <Anchor component={Link} to="/admin/haushalt-unmatched">Unbekannte FinVes</Anchor>{" "}
                    nachträglich Projekten zugeordnet werden.
                </Text>
                <Text size="sm">
                    Alle importierten FinVes und Budgetdaten sind anschließend sichtbar:
                </Text>
                <List size="sm" spacing="xs">
                    <List.Item>
                        In der <Anchor component={Link} to="/finves">FinVe-Übersicht</Anchor> mit Suche,
                        Filter und Diagrammen.
                    </List.Item>
                    <List.Item>
                        In der Projektdetailseite unter „Finanzierungsvereinbarungen (FinVe)".
                    </List.Item>
                    <List.Item>
                        Sammel-FinVes erscheinen in Projektdetailseiten als kompakter Tag (kein Diagramm).
                    </List.Item>
                </List>
            </Stack>
        ),
    },
];

export default function HaushaltsGuidePage() {
    return (
        <Container size="md" py="xl">
            <Stack gap="xl">
                <Stack gap="xs">
                    <Group gap="xs" align="center">
                        <ChronicleHeadline as="h1">Anleitung: Haushalts-Import</ChronicleHeadline>
                        <ChronicleDataChip>Schritt für Schritt</ChronicleDataChip>
                    </Group>
                    <Text c="dimmed" size="sm">
                        Diese Anleitung erklärt den vollständigen Import-Prozess der jährlichen
                        Bundeshaushaltsdaten (Anlage VWIB, Teil B) in das Schienendashboard.
                    </Text>
                </Stack>

                <Alert color="green" variant="light" title="Voraussetzungen">
                    <List size="sm" mt="xs" spacing={4}>
                        <List.Item>Du bist als <strong>Editor</strong> oder <strong>Admin</strong> eingeloggt.</List.Item>
                        <List.Item>Du hast das aktuelle PDF der Anlage VWIB Teil B zur Hand.</List.Item>
                        <List.Item>Der Celery-Worker läuft im Hintergrund (lokal oder auf dem Server).</List.Item>
                    </List>
                </Alert>

                <Accordion variant="separated" radius="md" defaultValue="step-1">
                    {STEPS.map((step) => (
                        <Accordion.Item key={step.nr} value={`step-${step.nr}`}>
                            <Accordion.Control>
                                <Group gap="sm" align="center">
                                    <ChronicleDataChip>
                                        {step.nr}
                                    </ChronicleDataChip>
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
                    <Accordion.Item value="wrong-year">
                        <Accordion.Control>
                            <Text size="sm" fw={500}>Das falsche Haushaltsjahr wurde eingetragen</Text>
                        </Accordion.Control>
                        <Accordion.Panel>
                            <Text size="sm">
                                Das Jahr kann nachträglich nicht mehr geändert werden. Der Import-Lauf muss
                                verworfen werden (Button „Verwerfen" auf der Review-Seite), und das PDF
                                muss erneut mit dem korrekten Jahr hochgeladen werden.
                            </Text>
                        </Accordion.Panel>
                    </Accordion.Item>
                    <Accordion.Item value="missing-rows">
                        <Accordion.Control>
                            <Text size="sm" fw={500}>Es fehlen Zeilen im Parse-Ergebnis</Text>
                        </Accordion.Control>
                        <Accordion.Panel>
                            <Text size="sm">
                                Bei Seitenumbrüchen innerhalb einer Zeile kann der Parser einzelne
                                Einträge übersehen. Vergleiche die Zeilenanzahl im Parser-Ergebnis
                                mit der Tabelle im Original-PDF. Falls Zeilen fehlen, wende dich an
                                einen Administrator – das Debug-Script{" "}
                                <code>apps/backend/scripts/dump_parse_result.py</code> hilft bei der Analyse.
                            </Text>
                        </Accordion.Panel>
                    </Accordion.Item>
                    <Accordion.Item value="no-worker">
                        <Accordion.Control>
                            <Text size="sm" fw={500}>Der Fortschrittsbalken dreht sich endlos</Text>
                        </Accordion.Control>
                        <Accordion.Panel>
                            <Stack gap="xs">
                                <Text size="sm">
                                    Ursache ist meistens ein nicht laufender Celery-Worker. Der Worker
                                    muss separat vom Backend gestartet werden:
                                </Text>
                                <Box p="xs" style={{ background: "var(--mantine-color-dark-8)", borderRadius: 4 }}>
                                    <Text size="xs" ff="monospace" c="gray.3">
                                        cd apps/backend && celery -A dashboard_backend.celery_app worker --loglevel=info
                                    </Text>
                                </Box>
                            </Stack>
                        </Accordion.Panel>
                    </Accordion.Item>
                    <Accordion.Item value="wrong-format">
                        <Accordion.Control>
                            <Text size="sm" fw={500}>Der Parser erkennt keine Zeilen (0 Zeilen gefunden)</Text>
                        </Accordion.Control>
                        <Accordion.Panel>
                            <Text size="sm">
                                Das hochgeladene PDF entspricht möglicherweise nicht dem erwarteten Format.
                                Prüfe, ob es sich um die Anlage VWIB Teil B handelt und ob das PDF
                                selektierbare Texte enthält (kein Scan ohne OCR). PDFs anderer Jahrgänge
                                können abweichende Spaltenstrukturen haben und benötigen ggf. Parser-Anpassungen.
                            </Text>
                        </Accordion.Panel>
                    </Accordion.Item>
                </Accordion>
            </Stack>
        </Container>
    );
}
