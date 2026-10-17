import GuideRenderer from "./GuideRenderer";
import type { GuideDef } from "./guideContent";

const DEF: GuideDef = {
    slug: "fulda",
    title: "Anleitung: Fulda-Runde einlesen",
    chip: "Schritt für Schritt",
    intro: `Wie Claude eine Antwort der Bundesregierung zur „Fulda-Runde" über den MCP-Server einliest und wie du das Ergebnis prüfst und freigibst.`,
    prerequisites: `- Dein Nutzer hat das Recht „Fulda-Runde einlesen" (\`fulda.import\`, in der Editor-Rolle enthalten).
- Du hast einen **API-Key** mit diesem Recht und Claude ist mit dem MCP-Server des Dashboards verbunden.
- Claude kennt den Skill \`fulda-runde\` (Ordner \`.claude/skills/fulda-runde\` im Repository).
- Das Antwort-PDF der Kleinen Anfrage liegt vor.`,
    steps: [
        {
            key: "pdf-beschaffen",
            title: "Das richtige PDF beschaffen",
            body: `Quelle ist die **Antwort der Bundesregierung** auf die Kleine Anfrage zu den „Ergebnissen der Fulda-Runde" (eine Bundestagsdrucksache). Nur die *Antwort* enthält die Projektlisten — **nicht** die Anfrage selbst.

> [!yellow] Jedes Jahr anders
> Aufbau, Fragen und Nummern wechseln von Jahr zu Jahr: mal Tabellen mit Projekt und Abschnitt, mal Aufzählungen, manchmal fast gar nichts („Fulda-Prozess nicht abgeschlossen"). Deshalb liest Claude das PDF selbst, statt eines festen Auslese-Programms.`,
        },
        {
            key: "einlesen",
            title: "Von Claude einlesen lassen",
            body: `Gib Claude das PDF und bitte: „Lies diese Fulda-Antwort mit dem Skill fulda-runde ein."

Claude legt dann über die MCP-Tools an:
1. das **Dokument** (Jahr, Drucksache, Datum, Antwortstand, Notiz zu unbeantworteten Fragen),
2. je Projektzeile einen **Eintrag** mit Kategorie, Fundstelle (Frage, Seite) und dem **Wortlaut**; Sammelzellen mit mehreren Maßnahmen werden aufgeteilt,
3. die **Zuordnung** zu Projekten bzw. Teilprojekten, jeweils mit Begründung,
4. die **Bestätigung** aller eindeutig zugeordneten Einträge.

Am Ende berichtet Claude, was übernommen, was selbst entschieden und was offen geblieben ist.

> [!blue] Kategorie nach Wortlaut, nicht nach Nummer
> Claude ordnet jede Liste nach dem Wortlaut der Frage zu („sind enthalten", „werden abgeschlossen", „sollen erhalten") — nie nach der Fragennummer.`,
        },
        {
            key: "durcharbeiten",
            title: "Ergebnis prüfen",
            body: `Öffne [Fulda-Runde](/admin/fulda-import) und den Jahrgang. Oben steht das Dokument mit Antwortstand und Notiz, darunter je Kategorie eine Tabelle. Jeder Eintrag zeigt Wortlaut, Fundstelle, Abschnitt, ggf. den angekündigten Termin und die Begründung der Zuordnung.

1. Prüfe offene Einträge und solche mit „Automatischer Vorschlag … ungeprüft".
2. Ordne über das Auswahlfeld ein oder mehrere **Projekte** zu; über **„Projekt fehlt?"** legst du einen Projekt-Entwurf an.
3. **„Übernehmen"** bestätigt einen Eintrag, **„Alle übernehmen (N)"** alle zugeordneten offenen Einträge.`,
            exampleKey: "fulda-year-table",
        },
        {
            key: "bestaetigen",
            title: "Was beim Bestätigen passiert",
            body: `Jeder bestätigte Eintrag erzeugt pro Projekt eine **Beobachtung** mit der Quelle \`Fulda-Runde\` (Vertrauen 0,55 — etwas unter VIB und Haushalt):

- **Ist-Aussagen** („aktuell in der Sammel-FinVe Lph 3/4", „hat eine Baufinanzierungsvereinbarung", „abgeschlossen, keine Aufnahme in die Folgephase") setzen die **Phase** zum Datum der Antwort.
- **Prognosen und Neuaufnahmen** („Lph 3/4 wird 2026 abgeschlossen", „soll eine Bau-FinVe erhalten") ändern die Phase **nicht**. Sie erscheinen als **erwarteter Termin** in der Prognose und im Zeitstrahl. Ein angekündigter Abschluss ist der frühestmögliche Beginn der nächsten Phase.

Konkurrieren ein Fulda-Termin und ein VIB-Termin, gewinnt der glaubwürdigere und aktuellere Bericht. Mehr dazu in der [Anleitung Planungsstand](/admin/anleitungen/projektfortschritt).`,
        },
    ],
    troubleshooting: [
        {
            key: "ts-keine-eintraege",
            title: "Ein Jahrgang hat keine oder kaum Einträge",
            body: `Manche Antworten enthalten keine Projektlisten (z. B. 2025: „Fulda-Prozess nicht abgeschlossen"). Das Dokument steht dann mit Antwortstand „ohne Ergebnis" bzw. „teilweise beantwortet" und einer Notiz in der Übersicht.`,
        },
        {
            key: "ts-falsche-phase",
            title: "Ein Eintrag steht in der falschen Kategorie",
            body: `Lass Claude den Eintrag korrigieren („Eintrag X gehört in COMPLETES_LPH_2") oder lösche ihn in der Jahrgangs-Ansicht. Die Beobachtungen der betroffenen Projekte werden danach neu berechnet.`,
        },
    ],
};

export default function FuldaGuidePage() {
    return <GuideRenderer def={DEF} />;
}
