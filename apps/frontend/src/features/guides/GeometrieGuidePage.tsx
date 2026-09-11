import GuideRenderer from "./GuideRenderer";
import type { GuideDef } from "./guideContent";

const DEF: GuideDef = {
    slug: "geometrie",
    title: "Anleitung: Geometrien erstellen",
    chip: "Grundlagen",
    intro: `Wie du den Verlauf eines Projekts auf der Karte erfasst — per Routing über das Schienennetz, mit Betriebsstellen, per GeoJSON-Upload oder von Hand gezeichnet. Ein Editor, überall gleich.`,
    prerequisites: `- Du bist als **Editor** oder **Admin** eingeloggt (Recht „Projekte bearbeiten").
- Das Projekt existiert bereits (auch als Entwurf) — Geometrien hängen immer an einem Projekt.
- Für „Route berechnen" muss der Routing-Dienst (GraphHopper) auf dem Server laufen.`,
    steps: [
        {
            key: "einstieg",
            title: "Wo du Geometrien bearbeitest",
            body: `Es gibt **einen** Geometrie-Editor mit zwei Einstiegen:

- **Projektdetailseite** → Button **„Geometrie verwalten"** öffnet den Editor als Vollbild-Dialog (Speichern mit **„Übernehmen"**).
- **Assistent „Projekt anlegen"** → Schritt **„Geometrie"** (Speichern mit **„Geometrie speichern"**; der Editor bleibt danach offen, damit du weitere Geometrien ergänzen kannst) — siehe [Anleitung: Projekt anlegen](/admin/anleitungen/projekt-anlegen).

Der Editor besteht aus einem linken Bedienfeld mit den vier Erfassungswegen und einer Kartenvorschau rechts, die **bestehende und neue Geometrie gemeinsam** anzeigt.`,
            exampleKey: "geometrie-panel",
        },
        {
            key: "route",
            title: "Route berechnen (empfohlen für Strecken)",
            body: `Der schnellste Weg für Streckenverläufe — das Routing folgt dem realen Schienennetz:

1. **„Startbahnhof"** und **„Zielbahnhof"** suchen und auswählen.
2. Läuft die berechnete Route falsch, mit **„+ Via-Bahnhof hinzufügen"** Zwischenhalte („Via 1", „Via 2", …) erzwingen.
3. **„Route berechnen"** klicken — die Route erscheint als Vorschau auf der Karte und wird erst mit dem Speichern übernommen.`,
        },
        {
            key: "punkte-geojson",
            title: "Betriebsstellen hinzufügen oder GeoJSON hochladen",
            body: `Zwei weitere Wege für Sonderfälle:

- **„Betriebsstellen hinzufügen"** — über **„Betriebsstelle suchen"** einzelne Stationen als Punkte aufnehmen (z. B. für Knoten- oder Bahnhofsprojekte). Die Liste darunter zeigt die Auswahl; das ×-Symbol entfernt einen Punkt wieder.
- **„Oder: GeoJSON hochladen"** — eine fertige **„GeoJSON-Datei"** auswählen (z. B. Export aus QGIS). Die enthaltenen Linien/Punkte erscheinen sofort in der Kartenvorschau; bei ungültigen Dateien wird eine Fehlermeldung angezeigt.`,
        },
        {
            key: "zeichnen",
            title: "Von Hand zeichnen",
            body: `Wenn weder Routing noch fertige Daten passen, zeichnest du direkt auf der Karte:

- **„Linie zeichnen"** — Klick für Klick Stützpunkte setzen, **Doppelklick** beendet die Linie.
- **„Punkt setzen"** — einzelne Punkte per Klick.
- **„Bearbeiten"** — Stützpunkte verschieben, einfügen (Mittelpunkt anklicken) oder löschen.
- **„Fertig"** beendet den Zeichenmodus; der Zähler-Chip zeigt „N gezeichnet · x km", **„Zurücksetzen"** verwirft alles Gezeichnete.`,
        },
        {
            key: "speichern",
            title: "Speichern, ergänzen, löschen",
            body: `Erst der Speichern-Button (**„Übernehmen"** bzw. **„Geometrie speichern"**) schreibt die neue Geometrie ans Projekt — sie wird zur bestehenden Geometrie **hinzugefügt**. Du kannst die Wege auch nacheinander kombinieren (z. B. Route berechnen, speichern, dann einen Punkt ergänzen).

Zum Löschen gibt es zwei Schalter:

- **„Bestehende Geometrie löschen"** — ersetzt beim Speichern die komplette bisherige Geometrie durch die neue.
- **„Einzelne Features auswählen & löschen"** — bestehende Linien/Punkte per Klick auf der Karte markieren und mit **„Auswahl löschen (N)"** gezielt entfernen.

> [!yellow] Ohne Geometrie keine Karte
> Projekte ohne Geometrie erscheinen nicht auf der Karte, sind aber in Listen, Suche und Detailseite voll nutzbar. Die Geometrie lässt sich jederzeit nachtragen.`,
        },
    ],
    troubleshooting: [
        {
            key: "ts-route-falsch",
            title: "Die berechnete Route nimmt den falschen Weg",
            body: `Das Routing wählt den kürzesten Weg im Schienennetz. Erzwinge den gewünschten Verlauf mit **„+ Via-Bahnhof hinzufügen"** — meist reicht ein einzelner Via-Halt auf dem richtigen Ast. Führt kein Weg zum Ziel (Routing-Fehler), fehlt die Verbindung im Netzmodell: dann den Abschnitt von Hand zeichnen oder als GeoJSON hochladen.`,
        },
        {
            key: "ts-geojson-fehler",
            title: "Der GeoJSON-Upload wird abgelehnt",
            body: `Die Datei muss gültiges GeoJSON sein (Feature oder FeatureCollection mit Linien/Punkten, Koordinaten in WGS84/EPSG:4326). Beim Export aus GIS-Programmen darauf achten, das Koordinatensystem auf EPSG:4326 zu stellen.`,
        },
    ],
};

export default function GeometrieGuidePage() {
    return <GuideRenderer def={DEF} />;
}
