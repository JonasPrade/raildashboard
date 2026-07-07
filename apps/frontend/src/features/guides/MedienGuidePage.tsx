import GuideRenderer from "./GuideRenderer";
import type { GuideDef } from "./guideContent";

const DEF: GuideDef = {
    slug: "medien",
    title: "Anleitung: Medien / Presse auswerten",
    chip: "Schritt für Schritt",
    intro: `Wie du einen Presseartikel (URL oder Text) per KI auswertest, den Entwurf prüfst und als Beobachtung mit der Quelle „Medien" übernimmst.`,
    prerequisites: `- Du bist als **Editor** oder **Admin** eingeloggt (Recht „Planungsstand bearbeiten").
- Ein Presseartikel mit einer konkreten Aussage zum Projektstand liegt vor (URL oder kopierter Text).
- Für die automatische Extraktion ist serverseitig ein LLM konfiguriert — ohne LLM bleibt der Entwurf leer und du füllst Phase, Projekt und Zitat manuell aus.`,
    steps: [
        {
            key: "artikel-waehlen",
            title: "Einen geeigneten Artikel wählen",
            body: `Geeignet sind Artikel mit einer **konkreten, belegbaren Aussage** zum Stand eines Projekts — z. B. „Bauarbeiten haben begonnen", „Planfeststellungsbeschluss liegt vor", „Strecke in Betrieb genommen". Reine Meinungsstücke oder vage Ankündigungen liefern keine brauchbare Beobachtung.

Die URL muss vom Server aus **öffentlich erreichbar** sein. Bei Paywall-Artikeln stattdessen den Artikeltext kopieren und einfügen.`,
        },
        {
            key: "extrahieren",
            title: "Extrahieren und Entwurf anlegen",
            body: `Gehe zu [Medien / Presse](/admin/media-import).

1. Füge die **„Artikel-URL"** ein **oder** kopiere den Text in das Feld **„… oder Text einfügen"** (bei URL wird der Text automatisch geladen).
2. Klicke auf **„Extrahieren & Entwurf anlegen"**.
3. Die KI schlägt **Publikation, Datum, Zitat, Phase und Projekt** vor; die Meldung „Entwurf angelegt — Bitte Phase & Projekt prüfen und bestätigen." erscheint und der neue Bericht taucht in der Liste darunter auf.

> [!blue] Ohne LLM
> Ist kein LLM konfiguriert (oder schlägt die Extraktion fehl), wird der Entwurf trotzdem angelegt — nur eben leer. Alle Felder lassen sich anschließend von Hand setzen.`,
            exampleKey: "medien-extract-form",
        },
        {
            key: "pruefen",
            title: "Entwurf prüfen und zuordnen",
            body: `Jeder Bericht ist eine Karte mit Publikation, Datum, dem stützenden **Zitat** (kursiv) und einem Link **„Artikel öffnen"**. Prüfe pro Karte:

1. **„Phase"** — die vom Artikel behauptete Leistungsphase (eine der fünf Hauptphasen).
2. **„Projekt"** — das betroffene Projekt (durchsuchbares Auswahlfeld). Ein \`✦\`-Vorschlag erscheint, wenn die KI einen Projektnamen erkannt, aber noch kein Projekt zugeordnet ist.
3. Das **Zitat** sollte die behauptete Phase tatsächlich belegen — es wird später in der Beobachtung angezeigt.

Mit dem Schalter **„Nur offene (unbestätigt)"** filterst du die Liste auf noch nicht übernommene Berichte.`,
            exampleKey: "medien-card",
        },
        {
            key: "bestaetigen",
            title: "Bestätigen — und was dann passiert",
            body: `Sobald **Phase und Projekt** gesetzt sind, lässt sich der Schalter **„Als Beobachtung übernehmen (bestätigt)"** aktivieren (vorher ist er gesperrt: „Phase und Projekt wählen, um den Bericht zu bestätigen."). Die Karte erhält das Badge \`bestätigt\`.

Das erzeugt eine abgeleitete **Beobachtung** mit der Quelle \`Medien\` und **niedrigem Vertrauen** — dafür ist sie meist sehr aktuell. Ob sie den angezeigten Stand bewegt, entscheidet die [glaubwürdigkeitsbasierte Ableitung](/admin/anleitungen/projektfortschritt) (Vertrauen je Quelle × Aktualität): Ein frischer Pressebericht kann veraltete Automatik-Signale überstimmen, verliert aber selbst schnell an Gewicht.

- Spätere Änderungen an Phase/Projekt aktualisieren die Beobachtung automatisch.
- Der Schalter lässt sich zurücknehmen; das entfernt die Beobachtung wieder.
- Das Papierkorb-Symbol löscht den Bericht **samt** seiner Beobachtung.`,
        },
    ],
    troubleshooting: [
        {
            key: "ts-extraktion-fehlgeschlagen",
            title: '„Extraktion fehlgeschlagen — URL/Text konnte nicht verarbeitet werden."',
            body: `Meist ist die URL vom Server aus nicht abrufbar (Paywall, Bot-Schutz, Login). Öffne den Artikel im Browser, kopiere den Text und füge ihn in das Textfeld ein — die Extraktion läuft dann über den eingefügten Text.`,
        },
        {
            key: "ts-schalter-gesperrt",
            title: "Der Bestätigen-Schalter ist ausgegraut",
            body: `Der Bericht kann erst übernommen werden, wenn **beide** Felder gesetzt sind: „Phase" und „Projekt". Der Hinweis unter dem Schalter („Phase und Projekt wählen, um den Bericht zu bestätigen.") verschwindet, sobald beides ausgefüllt ist.`,
        },
    ],
};

export default function MedienGuidePage() {
    return <GuideRenderer def={DEF} />;
}
