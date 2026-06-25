# Feature: Manuelle Geometrie-Erstellung (Linien & Punkte zeichnen)

## Ziel

Editors und Admins können für ein Projekt Geometrie **direkt auf der Karte von Hand**
anlegen: Linien zeichnen (Klick für Klick Stützpunkte setzen) und einzelne Punkte setzen.
Das ist nötig für Projekte, die Neubaustrecken sind oder auf Tram-/U-Bahn-Strecken fahren,
für die es keine über GraphHopper berechenbare Bahnroute gibt.

## Kontext

Heute entsteht Projektgeometrie nur auf drei Wegen — alle im geteilten `GeometryEditor`
(`apps/frontend/src/features/routing/GeometryEditor.tsx`), der sowohl im Projekt-Wizard
(Schritt 2) als auch im Bearbeiten-Modal (`GeometryManagementModal`) läuft:

1. Route über GraphHopper berechnen (`feature-routing.md`)
2. Betriebsstellen als Punkte hinzufügen
3. Fertige GeoJSON-Datei hochladen

Es fehlt das interaktive Zeichnen. Diese Funktion ergänzt genau diese Lücke.

## Scope

- Linien per Mausklick auf der Karte zeichnen (mehrere Stützpunkte, Doppelklick beendet die Linie)
- Einzelne Punkte per Klick setzen
- Gezeichnete Features **vor dem Speichern** editieren: Stützpunkte verschieben, einfügen, löschen
- Gezeichnete Geometrie wird mit bestehender Projektgeometrie gemischt (oder ersetzt sie, wenn
  „Bestehende Geometrie löschen" aktiv ist) und über `PATCH /api/v1/projects/{id}` gespeichert

## Nicht im Scope

- In-Place-Vertex-Edit bereits **gespeicherter** Geometrie (stattdessen: über den vorhandenen
  „Einzelne Features auswählen & löschen"-Modus entfernen und neu zeichnen)
- Manuelle numerische Koordinateneingabe (nur Klick auf der Karte)
- Backend-/Schema-/Migrations-Änderungen
- Snapping an bestehende Features, Undo/Redo-Historie

## Voraussetzungen

**Backend: keine Änderungen.** `project.geojson_representation` (Text) speichert bereits
beliebiges GeoJSON; `PATCH /api/v1/projects/{id}` schreibt es, die Parent-Aggregation
(`recompute_parent_geojson`) greift automatisch. Gezeichnete Features fließen über die
vorhandene `useUpdateProjectGeometry`-Mutation (`queries.ts`) in genau dieses Feld.

Neue Frontend-Dependencies: `terra-draw` (`^1.31.2`, TypeScript-nativ, enthält die Modi)
und der separate MapLibre-GL-Adapter `terra-draw-maplibre-gl-adapter` (`^1.4.1`, liefert
`TerraDrawMapLibreGLAdapter`, kompatibel mit MapLibre v5). In terra-draw v1.x ist der
Adapter **nicht** im Hauptpaket gebündelt, sondern ein eigenes Paket (ohne `@terra-draw/`-Scope).

## Verhalten

- Nur für `editor` / `admin` sichtbar (wie der restliche `GeometryEditor`)
- Zeichnen-Modus und „Einzelne Features auswählen & löschen" schließen sich gegenseitig aus
- Standard: gezeichnete Features werden an die bestehende Geometrie angehängt (`keepExisting`).
  Mit „Bestehende Geometrie löschen" ersetzen sie diese.
- Nach dem Speichern bleibt der Editor offen (Wizard-Verhalten); gezeichnete Features werden
  zurückgesetzt und die gespeicherte Geometrie wird zur neuen „bestehenden" Geometrie.

## Akzeptanzkriterien

- „Linie zeichnen" → mehrere Klicks setzen Stützpunkte, Doppelklick beendet → Linie auf der Karte
- „Bearbeiten" → Stützpunkt verschieben aktualisiert die Linie live
- „Punkt setzen" → Klick setzt einen Punkt
- „Geometrie speichern" → nach Reload ist die gezeichnete Geometrie persistent
  (als blaue Linie/Punkte aus `geojson_representation`)
- Im Bearbeiten-Modal mischt gezeichnete mit vorhandener Geometrie; „Bestehende Geometrie löschen" ersetzt sie
- Zeichnen-Sektion ist deaktiviert, solange `selectionMode` oder `deleteExisting` aktiv ist (und umgekehrt)

## Technische Hinweise

### Step 1 — Feature-Doku & Dependency
- Diese Datei (zuerst, AGENT.md-Regel). Querverweis von `docs/features/feature-routing.md`,
  Eintrag in `docs/roadmap.md`.
- `apps/frontend/package.json`: `terra-draw` (`^1.31.2`) und `terra-draw-maplibre-gl-adapter`
  (`^1.4.1`) zu `dependencies`, dann `npm install`.

### Step 2 — `GeometryPreviewMap.tsx`: terra-draw integrieren
Datei: `apps/frontend/src/features/routing/GeometryPreviewMap.tsx` (besitzt die MapLibre-Instanz)

Neue Props:
- `drawMode: "line" | "point" | "select" | null` — aktiver Modus (null = aus)
- `onDrawnFeaturesChange: (features: GeoJSON.Feature[]) => void` — feuert bei jeder Snapshot-Änderung
- `drawnFeatures: GeoJSON.Feature[]` — kontrollierter Bestand (Reset auf `[]` nach Speichern)

Umsetzung:
- Nach `map.on("load")` einen `TerraDraw` mit `TerraDrawMapLibreGLAdapter({ map })` und den Modi
  `TerraDrawLineStringMode`, `TerraDrawPointMode`, `TerraDrawSelectMode` (Select mit
  `editable`/`draggable` für Vertex verschieben/einfügen/löschen) erzeugen, in einem Ref halten.
- `useEffect` auf `drawMode` → `draw.setMode(...)`; `drawMode === null` → neutraler Modus (`static`),
  damit die bestehenden Selection-Mode-Klick-Handler ungestört bleiben.
- `draw.on("change"/"finish")` → `draw.getSnapshot()` (nur Line/Point) → `onDrawnFeaturesChange`.
- Cleanup: `draw.stop()` zusätzlich zu `map.remove()` im Unmount.
- terra-draw verwaltet eigene Layer/Sources; die bestehenden `existing`/`preview`-Layer bleiben unverändert.

### Step 3 — `GeometryEditor.tsx`: Zeichen-UI & Datenfluss
Datei: `apps/frontend/src/features/routing/GeometryEditor.tsx`
- Neuer State: `drawMode` und `drawnFeatures: GeoJSON.Feature[]`.
- Neue Sektion (`<Divider label="Zeichnen" />`): SegmentedControl/Buttons „Linie zeichnen",
  „Punkt setzen", „Bearbeiten", „Fertig"; Hinweistext; `ChronicleDataChip` mit Feature-Anzahl;
  „Zurücksetzen"-Button (leert `drawnFeatures`).
- Gegenseitiger Ausschluss: bestehende `disabled`-Logik (`selectionMode`/`deleteExisting`) erweitern.
- `buildFinalGeometry()`: `drawnFeatures` an die `features`-Liste anhängen (gleiches Merge-/
  `keepExisting`-Modell). `canAccept`/`hasNewGeometry` um `drawnFeatures.length > 0` ergänzen.
- `resetInputs()`: `drawnFeatures` → `[]`, `drawMode` → `null`.
- Neue Props an `GeometryPreviewMap` durchreichen.
- Optional: `computeGeojsonLengthKm` (`shared/geo/length.ts`) für Längenanzeige gezeichneter Linien.

### Step 4 — Texte & Doku
- `Step2Geometrie.tsx`: Einleitungstext um „… oder Linien und Punkte direkt auf der Karte zeichnen." ergänzen.
- `apps/frontend/src/features/documentation/documentationData.ts`: Geometrie-/Routing-Abschnitt ergänzen.
- `apps/frontend/README.md` Feature-Liste & `docs/roadmap.md` aktualisieren.

## Implementierungsreihenfolge

1. [x] Step 1: Feature-Doku (diese Datei) + `terra-draw` + `terra-draw-maplibre-gl-adapter` Dependency
2. [x] Step 2: `GeometryPreviewMap.tsx` — terra-draw, Modi, neue Props
3. [x] Step 3: `GeometryEditor.tsx` — Zeichen-UI, `drawnFeatures`-State, `buildFinalGeometry`
4. [x] Step 4: Wizard-/In-App-Doku-Texte, README, Roadmap

## Verifikation

- `cd apps/frontend && npm install && npm run lint && npm run build` — Typen & Build sauber
- `npm test` — bestehende Tests (inkl. `shared/geo/length.test.ts`) grün
- Manuell (`npm run dev`, eingeloggt als editor/admin): Akzeptanzkriterien oben durchklicken
- Gegencheck Backend unverändert: `cd apps/backend && .venv/bin/python -m pytest tests/api/test_projects.py`
