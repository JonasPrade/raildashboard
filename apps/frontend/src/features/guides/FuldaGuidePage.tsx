import GuideRenderer from "./GuideRenderer";
import type { GuideDef } from "./guideContent";

const DEF: GuideDef = {
    slug: "fulda",
    title: "Anleitung: Fulda-Runde anlegen",
    chip: "Schritt für Schritt",
    intro: `Wie du eine Antwort der Bundesregierung auf die „Fulda-Runde" auswertest und den Jahrgang den Projekten zuordnest.`,
    prerequisites: `- Du bist als **Editor** oder **Admin** eingeloggt (Recht „Planungsstand bearbeiten").
- Das Antwort-PDF der Kleinen Anfrage liegt vor.
- OCR und KI-Extraktion sind serverseitig konfiguriert (OCR- und LLM-Zugang).`,
    steps: [
        {
            key: "pdf-beschaffen",
            title: "Das richtige PDF beschaffen",
            body: `Quelle ist die **Antwort der Bundesregierung** auf die Kleine Anfrage zur „Fulda-Runde" (eine Bundestagsdrucksache). Nur die *Antwort* enthält die Projektlisten — **nicht** die Anfrage selbst.

> [!yellow] Wichtig
> Die Antwort listet pro nummerierter Frage eine Projektliste. Aus der Frage-Überschrift (z. B. „… in Vorplanung", „… mit abgeschlossener Genehmigungsplanung") wird die Leistungsphase abgeleitet — lade daher immer das vollständige Antwort-PDF hoch, damit die Fragennummern erhalten bleiben.`,
        },
        {
            key: "hochladen",
            title: "Hochladen und auswerten",
            body: `Gehe zu [Fulda-Runde](/admin/fulda-import).

1. Trage das **Jahr der Fulda-Runde** ein (Jahrgang der Drucksache).
2. Wähle das **Antwort-PDF** aus und klicke auf **„Auswerten & durcharbeiten"**.
3. Der Server liest das PDF per **OCR** und ordnet jede Projektliste per **KI** anhand der **Fragennummer** einer Leistungsphase zu (inkl. Abschnitt → Unterprojekt).
4. Nach Abschluss erscheint eine Meldung mit Anzahl erkannter Einträge und OCR-Status, und du landest automatisch auf der Jahrgangs-Seite.

> [!blue] Zuordnung nach Fragennummer
> Die Phase wird über die Nummer der Frage bestimmt, nicht frei „geraten". Dadurch bleibt die Zuordnung stabil, auch wenn Formulierungen variieren.`,
        },
        {
            key: "durcharbeiten",
            title: "Den Jahrgang durcharbeiten",
            body: `Die Jahrgangs-Seite listet alle erkannten Einträge, gruppiert nach Kategorie (Leistungsphase). Jeder Eintrag zeigt den Rohnamen und ggf. den Abschnitt. Pro Eintrag:

1. Ordne über das Auswahlfeld ein oder mehrere **Projekte** zu. Das \`✦\`-Symbol markiert einen automatischen Vorschlag (Fuzzy-Matching über den Namen) — bitte prüfen.
2. Findet sich kein passendes Projekt, kannst du über **„Projekt fehlt?"** direkt einen **Projekt-Entwurf** anlegen und ihn später fertigstellen (siehe [Anleitung: Projekt anlegen](/admin/anleitungen/projekt-anlegen)).
3. Ein Eintrag lässt sich **bestätigen**, sobald mindestens ein Projekt zugeordnet ist (Badge \`offen\` → \`aktiv\`). Mit **„Alle übernehmen (N)"** bestätigst du alle zugeordneten, offenen Einträge auf einmal.

Ein einmal ausgewerteter Jahrgang lässt sich jederzeit über die Jahrgangs-Tabelle erneut öffnen und weiterbearbeiten — du musst nicht alles in einem Rutsch erledigen.`,
            exampleKey: "fulda-year-table",
        },
        {
            key: "bestaetigen",
            title: "Was beim Bestätigen passiert",
            body: `Jede bestätigte Zuordnung erzeugt pro Projekt eine **Beobachtung** mit der Quelle \`Fulda-Runde\` (Phase + Jahrgangsdatum). Diese fließt in die [Ableitung des Planungsstands](/admin/anleitungen/projektfortschritt) ein — je nach Konfidenz und Aktualität gegenüber den anderen Quellen.

Historische Jahrgänge bleiben erhalten; ein neuer Jahrgang ergänzt die Historie, statt sie zu überschreiben.`,
        },
    ],
    troubleshooting: [
        {
            key: "ts-keine-eintraege",
            title: "Es werden keine oder kaum Einträge erkannt",
            body: `Meist wurde die **Anfrage** statt der **Antwort** hochgeladen, oder das PDF ist ein reiner Scan ohne verwertbaren Text. Prüfe, dass es sich um die Antwort der Bundesregierung mit nummerierten Fragen und Projektlisten handelt.`,
        },
        {
            key: "ts-falsche-phase",
            title: "Ein Eintrag hat die falsche Leistungsphase",
            body: `Die Phase folgt der Fragennummer im PDF. Weicht sie ab, stimmt vermutlich die Zuordnung Frage → Phase für diesen Jahrgang nicht — in dem Fall die Zuordnung nicht bestätigen und einen Administrator hinzuziehen.`,
        },
    ],
};

export default function FuldaGuidePage() {
    return <GuideRenderer def={DEF} />;
}
