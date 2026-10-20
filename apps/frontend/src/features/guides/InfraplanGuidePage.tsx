import GuideRenderer from "./GuideRenderer";
import type { GuideDef } from "./guideContent";

const DEF: GuideDef = {
    slug: "infraplan",
    title: "Anleitung: Infraplan einlesen",
    chip: "Schritt für Schritt",
    intro: `Wie ein neuer Jahrgang des Infraplans (Fünfjahresplan des Bundes für die Schiene) ins Dashboard kommt: hochladen, Maßnahmen Projekten zuordnen, übernehmen, Kennzahlen erfassen und freigeben. Zuordnen und Kennzahlen gehen auf **zwei Wegen mit gleichem Ergebnis** — von Hand im Frontend oder durch Claude über den MCP-Server.`,
    prerequisites: `- Dein Nutzer hat das Recht „Infraplan importieren" (\`infraplan.import\`, in der Editor-Rolle enthalten).
- Das PDF des Infraplans liegt vor (z. B. Infraplan 2026 vom 6. Oktober 2026).
- Für den KI-Weg: ein **API-Key** mit diesem Recht, Claude ist mit dem MCP-Server verbunden und lädt den Skill \`infraplan-import\` (der Server liefert ihn selbst aus).`,
    steps: [
        {
            key: "hochladen",
            title: "1. PDF hochladen (immer im Frontend)",
            body: `Gehe zu [Infraplan-Import](/admin/infraplan-import), gib den **Jahrgang** an und wähle das PDF. **„PDF lesen"** startet das Auslesen im Hintergrund; danach öffnet sich die Prüfansicht.

Der Entwurf steht in der Liste **„Entwürfe"** mit Status, Zeilenzahl und Warnungen. **„Neu auslesen"** liest dasselbe PDF erneut (bestehende Zuordnungen bleiben je Zeile erhalten), **„Verwerfen"** löscht den Entwurf.

> [!yellow] Warnungen des Parsers
> Lücken oder Dubletten in den laufenden Nummern, unaufgelöste Kostenverweise oder ein leerer Abschnitt stehen oben in der Prüfansicht (mit Link auf die PDF-Seite). Ein Entwurf mit Warnungen lässt sich nur im Frontend mit „Trotzdem übernehmen" bestätigen — der KI-Agent hält an dieser Stelle an.`,
        },
        {
            key: "zuordnen-manuell",
            title: "2a. Zuordnen von Hand",
            body: `In der Prüfansicht wählst du oben den **Abschnitt** (Bedarfsplan Teil A–D, GVFG Kat. A/C, InvKG) und filterst mit **„nur ohne Zuordnung"**.

1. **„Vorschläge übernehmen (≥ 85 %)"** ordnet alle sicheren Treffer zu: gleiche Projektnummer, GVFG-Schlüssel oder sehr ähnlicher Name.
2. Für die übrigen Zeilen wählst du im Feld **Zuordnung** ein oder mehrere Projekte. Vorschläge erscheinen darunter als \`✦ Projekt · 92 %\` — ein Klick übernimmt sie. Jede Änderung wird sofort gespeichert.
3. Das Abzeichen zeigt, woher eine Zuordnung stammt: \`Projektnummer\`, \`Namensähnlichkeit\`, \`manuell\` oder \`KI-Agent\` (mit Begründung als Tooltip).
4. Fehlt ein passendes Teilprojekt: Menü **⋮ → „Teilprojekt anlegen unter …"**, Elternprojekt wählen; der Name ist mit der Maßnahme vorbelegt.

Unten listet **„Im Vorjahr enthalten, jetzt ohne Eintrag"** Projekte, die im letzten Jahrgang eine Zeile hatten und jetzt keine — meist ist die Maßnahme umbenannt oder zusammengelegt.`,
        },
        {
            key: "zuordnen-ki",
            title: "2b. Zuordnen durch Claude (MCP + Skill)",
            body: `Bitte Claude: „Ordne den Infraplan 2026 mit dem Skill infraplan-import zu." Claude

1. übernimmt die sicheren Vorschläge,
2. sucht für offene Zeilen das passende Projekt oder Teilprojekt und ordnet **mit Begründung** zu (Abzeichen \`KI-Agent\`),
3. legt fehlende Teilprojekte als Entwurf an,
4. bestätigt den Jahrgang — **nur ohne Parser-Warnungen**,
5. liest die Kennzahlen aus den Diagrammen und trägt sie als **ungeprüft** ein,
6. berichtet, was übernommen, selbst entschieden und offen geblieben ist.

Alles, was Claude tut, steht im Änderungsprotokoll und lässt sich in der Prüfansicht oder unter „Offene Zuordnungen" korrigieren.`,
        },
        {
            key: "uebernehmen",
            title: "3. Übernehmen",
            body: `Unten in der Prüfansicht trägst du das **Veröffentlichungsdatum** ein (vom Titelblatt) und klickst **„Übernehmen"**. Das Datum datiert die Aussagen zum Planungsstand.

Danach fließen die zugeordneten Zeilen in Phase, Planfeststellung, parlamentarische Befassung, Prognose (geplante Inbetriebnahme) und Kosten der Projekte ein. Zeilen ohne Projekt landen unter [Offene Zuordnungen](/admin/unassigned) und lassen sich dort jederzeit nachtragen.

> [!blue] Rückgängig machen
> Unter „Übernommene Jahrgänge" löscht **„Löschen"** einen Jahrgang samt Zuordnungen und Kennzahlwerten. Der Entwurf bleibt erhalten und kann erneut übernommen werden.`,
        },
        {
            key: "kennzahlen",
            title: "4. Kennzahlen erfassen und freigeben",
            body: `Unter „Übernommene Jahrgänge" führt **„Kennzahlen"** zur Kennzahlen-Seite des Jahrgangs.

- **Erfassen:** Kennzahl wählen, Zeilen mit Jahr, Ist/Ziel, Teilreihe (z. B. ein Teilprogramm), Wert und Quellseite eintragen, **„Speichern"**. Von Hand eingetragene Werte gelten sofort als geprüft.
- **Freigabe:** Werte, die Claude aus den Diagrammen gelesen hat, stehen neben dem Bild ihrer Quellseite. Stimmen sie, gibt **„Jahrgang freigeben"** alle frei; falsche Werte korrigierst du vorher unter „Erfassen".

Öffentlich auf der Seite [Infraplan](/infraplan) erscheinen nur geprüfte Werte: Ist-Werte des neuesten Jahrgangs als Balken, die Zielwerte jedes Jahrgangs als eigene Linie.`,
        },
    ],
    troubleshooting: [
        {
            key: "ts-jahrgang-existiert",
            title: '„Der Infraplan … ist bereits übernommen"',
            body: `Ein Jahrgang lässt sich nur einmal übernehmen. Um ihn neu einzulesen, zuerst unter „Übernommene Jahrgänge" löschen und dann den (neuen) Entwurf übernehmen.`,
        },
        {
            key: "ts-falsche-zuordnung",
            title: "Eine Zeile hängt am falschen Projekt",
            body: `Vor dem Übernehmen: in der Prüfansicht das Projekt austauschen oder über **⋮ → „Zuordnung entfernen"** lösen. Danach: den Jahrgang löschen und neu übernehmen oder Claude bitten, die Zeile mit \`assign_infraplan_row\` umzuhängen.`,
        },
        {
            key: "ts-kein-seitenbild",
            title: "In der Freigabe fehlt das Seitenbild",
            body: `Das Bild wird aus dem gespeicherten PDF des Entwurfs erzeugt. Wurde der Entwurf gelöscht oder ist das PDF nicht mehr vorhanden, fehlt es — dann den Wert anhand des Original-PDFs prüfen.`,
        },
    ],
};

export default function InfraplanGuidePage() {
    return <GuideRenderer def={DEF} />;
}
