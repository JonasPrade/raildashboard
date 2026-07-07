import { Link } from "react-router-dom";
import { Container, SimpleGrid, Stack, Text, Group } from "@mantine/core";
import { ChronicleHeadline, ChronicleCard, ChronicleDataChip } from "../../components/chronicle";
import { useAuth } from "../../lib/auth";

type Guide = {
    to: string;
    title: string;
    description: string;
};

// Conceptual foundation first, then the concrete "how do I feed data in" workflows.
const FOUNDATIONS: Guide[] = [
    {
        to: "/admin/anleitungen/projektfortschritt",
        title: "So funktioniert der Projektfortschritt",
        description:
            "Leistungsphasen, Quellen & Beobachtungen, glaubwürdigkeitsbasierte Ableitung, Verfahren (PF/Parl.), Unterprojekt-Aggregation und Prognose — das mentale Modell hinter dem Planungsstand.",
    },
    {
        to: "/admin/anleitungen/projekt-anlegen",
        title: "Projekt anlegen",
        description:
            "Den Assistenten von Stammdaten über Geometrie, Eigenschaften und Planungsstand bis zur FinVe/VIB-Verknüpfung durchlaufen — inkl. Entwürfe und Unterprojekte.",
    },
    {
        to: "/admin/anleitungen/geometrie",
        title: "Geometrien erstellen",
        description:
            "Projektverlauf auf der Karte erfassen: Route über das Schienennetz berechnen, Betriebsstellen setzen, GeoJSON hochladen oder von Hand zeichnen.",
    },
];

const WORKFLOWS: Guide[] = [
    {
        to: "/admin/haushalt-import/guide",
        title: "Haushaltstabelle importieren",
        description:
            "Jährliche Anlage VWIB Teil B (Bundeshaushalt) als PDF einlesen, FinVes und Sammel-FinVes prüfen und Projekten zuordnen.",
    },
    {
        to: "/admin/anleitungen/fulda",
        title: "Fulda-Runde anlegen",
        description:
            "Antwort der Bundesregierung auf die Kleine Anfrage per OCR+KI nach Leistungsphase auswerten und den Jahrgang durcharbeiten.",
    },
    {
        to: "/admin/anleitungen/bauportal",
        title: "DB-Bauportal abrufen",
        description:
            "Aktuellen Bau-/Planungsstand aus der offenen Bauportal-API ziehen, Vorschläge prüfen und als Beobachtung übernehmen.",
    },
    {
        to: "/admin/anleitungen/vib",
        title: "VIB-Bericht importieren",
        description:
            "Verkehrsinvestitionsbericht (Schienenwege) per OCR einlesen, Struktur prüfen und Vorhaben im Review den Projekten (m:n) zuordnen.",
    },
    {
        to: "/admin/anleitungen/medien",
        title: "Medien / Presse auswerten",
        description:
            "Presseartikel (URL oder Text) per KI auswerten, Phase und Projekt prüfen und als aktuelle, niedrig gewichtete Beobachtung übernehmen.",
    },
];

function GuideGrid({ guides }: { guides: Guide[] }) {
    return (
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm">
            {guides.map((g) => (
                <ChronicleCard key={g.to} style={{ textDecoration: "none" }}>
                    <Link to={g.to} style={{ textDecoration: "none", color: "inherit" }}>
                        <Stack gap={4}>
                            <Text fw={500}>{g.title}</Text>
                            <Text size="sm" c="dimmed">
                                {g.description}
                            </Text>
                        </Stack>
                    </Link>
                </ChronicleCard>
            ))}
        </SimpleGrid>
    );
}

/** Shown only to users who may edit guide texts in-app. */
function EditHint() {
    const { can } = useAuth();
    if (!can("guides.edit")) return null;
    return (
        <Text c="dimmed" size="xs">
            Du kannst die Anleitungstexte direkt bearbeiten: In jedem Abschnitt erscheint dafür
            ein „Bearbeiten"-Knopf (Markdown; „Zurücksetzen" stellt den Standardtext wieder her).
        </Text>
    );
}

export default function AnleitungenPage() {
    return (
        <Container size="lg" py="xl">
            <Stack gap="xl">
                <Stack gap="xs">
                    <Group gap="xs" align="center">
                        <ChronicleHeadline as="h1">Anleitungen</ChronicleHeadline>
                        <ChronicleDataChip>Datenpflege</ChronicleDataChip>
                    </Group>
                    <Text c="dimmed" size="sm">
                        Schritt-für-Schritt-Anleitungen für das Pflegen der Datenbank: wie der
                        Planungsstand eines Projekts zustande kommt und wie neue Quellen
                        (Bundeshaushalt, Fulda-Runden, DB-Bauportal, VIB, Presse, …) angelegt und
                        zugeordnet werden.
                    </Text>
                    <EditHint />
                </Stack>

                <Stack gap="sm">
                    <Text fw={600} size="sm" c="dimmed" tt="uppercase">
                        Grundlagen
                    </Text>
                    <GuideGrid guides={FOUNDATIONS} />
                </Stack>

                <Stack gap="sm">
                    <Text fw={600} size="sm" c="dimmed" tt="uppercase">
                        Datenquellen pflegen
                    </Text>
                    <GuideGrid guides={WORKFLOWS} />
                </Stack>
            </Stack>
        </Container>
    );
}
