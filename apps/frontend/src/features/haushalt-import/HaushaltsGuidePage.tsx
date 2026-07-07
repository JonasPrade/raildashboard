import GuideRenderer from "../guides/GuideRenderer";
import type { GuideDef } from "../guides/guideContent";

const DEF: GuideDef = {
    slug: "haushalt",
    title: "Anleitung: Haushalts-Import",
    chip: "Schritt für Schritt",
    intro: `Diese Anleitung erklärt den vollständigen Import-Prozess der jährlichen Bundeshaushaltsdaten (Anlage VWIB, Teil B) in das Schienendashboard.`,
    prerequisites: `- Du bist als **Editor** oder **Admin** eingeloggt.
- Du hast das aktuelle PDF der Anlage VWIB Teil B zur Hand.
- Der Celery-Worker läuft im Hintergrund (lokal oder auf dem Server).`,
    steps: [
        {
            key: "pdf-beschaffen",
            title: "PDF-Datei beschaffen",
            body: `Die Quelldatei ist die **Anlage VWIB, Teil B** des Bundeshaushalts – ein Dokument mit dem Titel „Bedarfsplanmaßnahmen Schienenwegeinvestitionsprogramm".

Diese Anlage wird jährlich zusammen mit dem Bundeshaushaltsentwurf veröffentlicht (in der Regel im Frühjahr). Das aktuelle PDF kann über die offizielle Seite des Bundesministeriums der Finanzen oder direkt aus dem Haushaltssystem bezogen werden.

> [!yellow] Wichtig
> Es darf nur die offizielle Teil-B-Anlage (VWIB) verwendet werden – nicht die Gesamtanlage oder andere Bundeshaushalt-PDFs. Das Format der Tabelle ist spezifisch und unterscheidet sich stark von anderen Anhängen.`,
        },
        {
            key: "hochladen",
            title: "PDF hochladen und parsen",
            body: `Gehe zu [Haushalts-Import](/admin/haushalt-import).

1. Klicke auf „PDF auswählen…" und wähle die heruntergeladene VWIB-Teil-B-Datei aus.
2. Trage das **Haushaltsjahr** ein (z. B. 2026). Dieses Jahr wird für die Zuordnung der Sammel-FinVes genutzt und sollte dem Jahr des PDFs entsprechen.
3. Klicke auf **„PDF parsen"**. Der Server extrahiert die Tabelle mit pdfplumber und analysiert alle Zeilen im Hintergrund.
4. Während des Parsens wird ein Fortschrittsbalken angezeigt (Seite X / Gesamtseiten, Anzahl gefundener Zeilen). Bei großen PDFs kann das einige Sekunden dauern.
5. Nach Abschluss wird die Seite automatisch zur Ergebnis-Überprüfung weitergeleitet.

> [!blue] Hinweis
> Der Parser ist auf das 2026-Format kalibriert (zusammengeführte erste drei Spalten, mehrzeilige Zellen, Kap./Titel-Unterzeilen). Ältere PDFs können abweichende Strukturen haben.`,
        },
        {
            key: "phase1-finves",
            title: "Phase 1: Reguläre FinVes prüfen und zuordnen",
            body: `Die Ergebnis-Tabelle zeigt alle erkannten FinVes (Finanzierungsvereinbarungen) mit ihrem Status:

- \`Neu\` — FinVe wurde noch nie importiert, wird neu angelegt.
- \`Änd.\` — FinVe existiert bereits, Budgetdaten werden ergänzt.
- \`Unbek.\` — FinVe konnte keinem Projekt zugeordnet werden.

Pro Zeile kann über das **MultiSelect-Feld** ein oder mehrere Projekte aus der Datenbank zugeordnet werden. Der Fuzzy-Matching-Algorithmus schlägt automatisch passende Projekte vor (Symbol ✦). Die Vorschläge basieren auf dem Namen der FinVe.

Zuordnungen können auch leer gelassen werden – die FinVe wird trotzdem importiert, bleibt aber unverknüpft und erscheint später in der Unmatched-Liste.`,
            exampleKey: "haushalt-review",
        },
        {
            key: "phase2-sv-finves",
            title: "Phase 2: Sammel-FinVes prüfen",
            body: `Sammelfinanzierungsvereinbarungen (SV-FinVes) enthalten nicht eine einzelne Maßnahme, sondern bündeln viele kleinere Projekte. Sie werden im PDF durch eine **YYY-Projektnummer** (statt dem üblichen B-Prefix) und einen *Erläuterungstext* mit eingerückten Einzelprojekten gekennzeichnet.

Im Review-Bereich „Sammel-FinVes (Phase 2)" erscheint für jede SV-FinVe eine Liste der erkannten Unterzeilen (aus dem Erläuterungstext). Pro Unterzeile kann ein Projekt zugeordnet werden:

1. Das ✦-Symbol zeigt einen automatischen Vorschlag basierend auf dem Projektnamen.
2. Weitere Projekte können über „+ weitere Projekte" manuell ergänzt werden, falls nicht alle erkannt wurden.
3. Die Zuordnung gilt nur für das aktuelle Haushaltsjahr – historische Zuordnungen aus Vorjahren bleiben erhalten.

> [!blue] Hinweis
> SV-FinVes können bei Seitenumbrüchen im PDF gesplittet sein. Der Parser erkennt und verbindet diese automatisch über einen Raw-Text-Scan. Falls Unterzeilen fehlen, kann der Erläuterungstext im Original-PDF verglichen werden.`,
        },
        {
            key: "bestaetigen",
            title: "Import bestätigen und Nachbearbeitung",
            body: `Klicke auf **„Importieren"**, um alle Daten in die Datenbank zu übernehmen. Nach dem Import erscheint eine Bestätigung und du wirst zur Übersicht weitergeleitet.

FinVes ohne Projektzuordnung werden als *unmatched* gespeichert und können unter [Unbekannte FinVes](/admin/haushalt-unmatched) nachträglich Projekten zugeordnet werden.

Alle importierten FinVes und Budgetdaten sind anschließend sichtbar:

- In der [FinVe-Übersicht](/finves) mit Suche, Filter und Diagrammen.
- In der Projektdetailseite unter „Finanzierungsvereinbarungen (FinVe)".
- Sammel-FinVes erscheinen in Projektdetailseiten als kompakter Tag (kein Diagramm).

Aus verknüpften FinVes werden außerdem automatisch Beobachtungen für den [Planungsstand](/admin/anleitungen/projektfortschritt) abgeleitet.`,
        },
    ],
    troubleshooting: [
        {
            key: "ts-falsches-jahr",
            title: "Das falsche Haushaltsjahr wurde eingetragen",
            body: `Das Jahr kann nachträglich nicht mehr geändert werden. Der Import-Lauf muss verworfen werden (Button „Verwerfen" auf der Review-Seite), und das PDF muss erneut mit dem korrekten Jahr hochgeladen werden.`,
        },
        {
            key: "ts-fehlende-zeilen",
            title: "Es fehlen Zeilen im Parse-Ergebnis",
            body: `Bei Seitenumbrüchen innerhalb einer Zeile kann der Parser einzelne Einträge übersehen. Vergleiche die Zeilenanzahl im Parser-Ergebnis mit der Tabelle im Original-PDF. Falls Zeilen fehlen, wende dich an einen Administrator – das Debug-Script \`apps/backend/scripts/dump_parse_result.py\` hilft bei der Analyse.`,
        },
        {
            key: "ts-endloser-fortschritt",
            title: "Der Fortschrittsbalken dreht sich endlos",
            body: `Ursache ist meistens ein nicht laufender Celery-Worker. Der Worker muss separat vom Backend gestartet werden:

\`\`\`
cd apps/backend && celery -A dashboard_backend.celery_app worker --loglevel=info
\`\`\``,
        },
        {
            key: "ts-keine-zeilen",
            title: "Der Parser erkennt keine Zeilen (0 Zeilen gefunden)",
            body: `Das hochgeladene PDF entspricht möglicherweise nicht dem erwarteten Format. Prüfe, ob es sich um die Anlage VWIB Teil B handelt und ob das PDF selektierbare Texte enthält (kein Scan ohne OCR). PDFs anderer Jahrgänge können abweichende Spaltenstrukturen haben und benötigen ggf. Parser-Anpassungen.`,
        },
    ],
};

export default function HaushaltsGuidePage() {
    return <GuideRenderer def={DEF} />;
}
