import GuideRenderer from "./GuideRenderer";
import type { GuideDef } from "./guideContent";

const DEF: GuideDef = {
    slug: "vib",
    title: "Anleitung: VIB-Bericht importieren",
    chip: "Schritt für Schritt",
    intro: `Wie du den Verkehrsinvestitionsbericht (Schienenwege, Abschnitt B) per OCR einliest, die erkannte Struktur prüfst und die Vorhaben im Review den Projekten zuordnest.`,
    prerequisites: `- Du bist als **Editor** oder **Admin** eingeloggt (Recht „VIB importieren").
- Das VIB-PDF (Bundestagsdrucksache) liegt vor.
- Für Scan-PDFs und KI-Extraktion sind serverseitig OCR- und LLM-Zugang konfiguriert; ohne OCR greift der pymupdf-Fallback für Text-PDFs.`,
    steps: [
        {
            key: "pdf-beschaffen",
            title: "Das richtige PDF beschaffen",
            body: `Quelle ist der jährliche **Verkehrsinvestitionsbericht** (VIB), eine Bundestagsdrucksache („Verkehrsinvestitionsbericht für das Berichtsjahr XXXX"). Importiert wird ausschließlich **Abschnitt B (Schienenwege)** — die übrigen Abschnitte (Straße, Wasserstraße) werden ignoriert.

> [!yellow] Berichtsjahr beachten
> Der VIB beschreibt immer ein zurückliegendes Berichtsjahr (Erscheinung meist 1–2 Jahre später). Trage das **Berichtsjahr** ein, nicht das Erscheinungsjahr — die abgeleiteten Beobachtungen werden auf dieses Jahr datiert und verlieren mit der Zeit bewusst an Gewicht.`,
        },
        {
            key: "hochladen",
            title: "Hochladen und parsen",
            body: `Gehe zu [VIB-Import](/admin/vib-import) und fülle die Karte **„Neuer Import"** aus:

1. **„PDF-Datei (Verkehrsinvestitionsbericht)"** auswählen — darunter erscheint eine PDF-Vorschau zum Blättern.
2. **„Berichtsjahr"** eintragen.
3. Optional **„OCR: von Seite" / „OCR: bis Seite"** auf die Seiten von Abschnitt B eingrenzen (in der PDF-Vorschau nachschlagen). Das spart OCR-Zeit; leer lassen für automatische Erkennung.
4. **„Kopf- und Fußzeilen ignorieren"** angehakt lassen — entfernt wiederkehrende Seitenzahlen und Dokumenttitel aus dem Text.
5. Auf **„PDF parsen"** klicken. Der Fortschritt läuft als Statuszeile mit („Seite X / Y"); je nach Umfang dauert das mehrere Minuten.

> [!blue] OCR-Verfahren
> Ist serverseitig Mistral OCR konfiguriert, wird damit gelesen (Chip \`Mistral OCR\` im Review); sonst greift der pymupdf-Fallback (Chip \`pymupdf\`) — der funktioniert nur bei PDFs mit eingebettetem Text, nicht bei reinen Scans.`,
            exampleKey: "vib-import-form",
        },
        {
            key: "struktur",
            title: "Strukturvorschau prüfen",
            body: `Nach dem Parsen landest du automatisch auf der **Strukturvorschau**. Sie zeigt oben Kennzahlen (*Projekte erkannt, Berichtsjahr, Drucksache, Ohne PFA*) und darunter alle erkannten Vorhaben mit Sektion, Projektname und Kategorie.

- Die Spalte **„Rohtext-Qualität & Abschnitte"** zeigt pro Vorhaben, welche Unterabschnitte gefunden wurden (Verk. Zielsetzung, Durchgef. Maßnahmen, Noch umzusetzende, Bauaktivitäten, Teilinbetriebnahmen, Projektkenndaten) und wie viele PFA-Zeilen erkannt wurden.
- Per Klick auf eine Zeile (**„▼ Rohtext anzeigen"**) lässt sich der OCR-Rohtext des Vorhabens einsehen — nützlich, wenn ein Eintrag \`leer\` oder \`0 PFA\` meldet.
- Stimmt die Struktur grob, weiter mit **„Weiter zum Review →"**; sonst **„Abbrechen"** und mit angepasstem Seitenbereich neu parsen.`,
            exampleKey: "vib-structure",
        },
        {
            key: "review",
            title: "Review: Vorhaben für Vorhaben durcharbeiten",
            body: `Das Review zeigt **ein Vorhaben pro Seite** (Navigation über die Pfeile bzw. das Nummern-Auswahlfeld „X / Gesamt"). Pro Vorhaben:

1. **„KI extrahieren"** (bzw. **„KI wiederholen"**) füllt aus dem Rohtext die Strukturfelder: Überschrift, Länge (km), Gesamtkosten (Mio. €), Vmax, Projektstatus (Planung / Bau / Abgeschlossen), die Textabschnitte und die PFA-Tabelle.
2. Über **„Projekte zuordnen"** das Vorhaben einem oder **mehreren Projekten** zuordnen (m:n — z. B. wenn ein VIB-Vorhaben mehrere Dashboard-Projekte abdeckt). Der Chip daneben zeigt den KI-Vorschlag: \`✓\` Vorschlag übernommen, \`~\` manuell abweichend.
3. In der **PFA-Tabelle** jede Zeile prüfen (Nr., Örtlichkeit, Entwurfspl., Abschluss FinVe, PFB, Baubeginn, IBM) und in der Spalte **„Unterprojekt"** dem passenden Unterprojekt zuordnen — das ✦-Symbol markiert einen automatischen Vorschlag. Fehlende Zeilen über **„+ Zeile"** ergänzen.
4. Die Kopfzeile zeigt den Fortschritt („X / Y zugeordnet"). Mit **„Entwurf speichern"** kannst du jederzeit unterbrechen — der Stand erscheint auf der Import-Seite unter **„Offene Entwürfe"** („Weiterbearbeiten").`,
            exampleKey: "vib-review-entry",
        },
        {
            key: "bestaetigen",
            title: "Bestätigen — und was dann passiert",
            body: `**„Import bestätigen"** speichert den Bericht dauerhaft („Import erfolgreich: X Vorhaben, Y PFA-Einträge importiert") und er erscheint auf der Import-Seite unter **„Importierte Berichte"**.

Aus jeder Projekt-Verknüpfung werden **automatisch Beobachtungen** mit der Quelle \`VIB\` abgeleitet (Projektstatus → Phase, datiert auf das Berichtsjahr); die Termine der PFA-Tabelle speisen zusätzlich die **Prognose** der Unterprojekte. Beides fließt in die [Ableitung des Planungsstands](/admin/anleitungen/projektfortschritt) ein — als „immer veraltetes" Signal mit entsprechend abnehmendem Gewicht.

> [!yellow] Ein Bericht pro Jahr
> Pro Berichtsjahr gibt es genau einen VIB-Bericht. „Löschen" in der Tabelle entfernt den Bericht samt aller importierten Vorhaben unwiderruflich.`,
        },
    ],
    troubleshooting: [
        {
            key: "ts-ki-fehlgeschlagen",
            title: 'Ein Eintrag zeigt „KI ✗" / „KI fehlgeschlagen"',
            body: `Die KI-Extraktion ist für dieses Vorhaben fehlgeschlagen (Details im Tooltip des Chips). Öffne den Eintrag und klicke **„KI wiederholen"** — oft hilft ein zweiter Versuch. Schlägt es dauerhaft fehl, kannst du alle Felder auch manuell aus dem **Volltext** unten im Formular ausfüllen.`,
        },
        {
            key: "ts-fehlende-abschnitte",
            title: 'Vorhaben mit „0 PFA" oder fehlenden Abschnitten',
            body: `Prüfe in der Strukturvorschau den Rohtext des Vorhabens. Ist er leer oder abgeschnitten, war meist der **Seitenbereich** zu eng gewählt oder die OCR-Qualität schlecht — dann mit korrigiertem „OCR: von/bis Seite" neu parsen. Nicht jedes Vorhaben hat eine PFA-Tabelle; „0 PFA" ist bei kleinen Vorhaben normal.`,
        },
        {
            key: "ts-pymupdf",
            title: 'Im Review steht „pymupdf" statt „Mistral OCR"',
            body: `Serverseitig ist kein OCR-Zugang konfiguriert; der Text wurde direkt aus dem PDF extrahiert. Das funktioniert gut bei digital erzeugten PDFs, aber nicht bei reinen Scans — in dem Fall einen Administrator bitten, den OCR-Zugang zu konfigurieren.`,
        },
    ],
};

export default function VibGuidePage() {
    return <GuideRenderer def={DEF} />;
}
