# Feature: Strecken im Kartenhintergrund

## Ziel

Die Karte zeigt das reale Schienennetz als Hintergrundebene. Projektgeometrien
liegen damit nicht mehr auf einer leeren Graustufen-Basemap, sondern sichtbar auf
dem Netz: Nutzer erkennen sofort, welche Strecke ein Projekt betrifft, wo ein
Ausbau in eine Bestandsstrecke einfädelt und wo eine Neubaustrecke tatsächlich
neu ist.

## Scope

- Zuschaltbarer Raster-Overlay „Strecken" auf der Projektkarte (`/map`).
- Dieselbe `MapView` in der Projektdetailseite zeigt den Overlay ebenfalls (Prop
  `showRailwayLines`, Default `true`) — dort ohne eigenen Schalter.
- Derselbe Overlay im Geometrie-Editor (`GeometryPreviewMap`) — dort **fest an**,
  weil das Zeichnen und Prüfen von Verläufen ohne Netzbezug kaum möglich ist.
- Kachelquelle konfigurierbar über eine Umgebungsvariable; Default ist
  OpenRailwayMap.

Nicht im Scope: ein Vektor-Layer aus dem eigenen RINF-Netzmodell
(`section_of_line`). Dafür fehlt in der Datenbank die Streckengeometrie — dort
existieren nur Start-/Ziel-Betriebsstellen, ein daraus gebildeter Linienzug wäre
schematisch und irreführend. Ein solcher Diagnose-Layer wäre ein eigenes Feature.

## Datenquelle

[OpenRailwayMap](https://www.openrailwaymap.org/) liefert fertige Rasterkacheln
des Schienennetzes (Stil `standard`) auf Basis von OpenStreetMap-Daten.

- Default-Kacheln: `https://{a,b,c}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png`
- Überschreibbar über `REACT_APP_RAILWAY_TILE_LAYER_URL` (eine einzelne
  Template-URL, z. B. eine selbst gehostete Instanz).
- Der Wert `off` entfernt Layer und Schalter — für Deployments, die keine externe
  Kachelquelle anfragen dürfen. Ein *leerer* Wert bedeutet bewusst **nicht**
  „aus": Docker und GitHub Actions machen aus einem nicht gesetzten Build-Arg
  einen leeren String, „aus" braucht deshalb ein eigenes Wort.

**Nutzungsbedingungen:** Die öffentlichen OpenRailwayMap-Kacheln sind für
moderaten Gebrauch gedacht (Tile Usage Policy). Attribution ist Pflicht und wird
über die MapLibre-`attribution` der Rasterquelle ausgegeben:
„Strecken: © OpenRailwayMap · Daten © OpenStreetMap-Mitwirkende (ODbL)".
Bei wachsendem Traffic wird auf eine eigene Kachelinstanz umgestellt — dafür
genügt das Setzen der Umgebungsvariablen, kein Codeeingriff.

**Achtung Referrer:** Der öffentliche Kachelserver antwortet nur auf Anfragen mit
`Referer`-Header (ohne: HTTP 403). Browser senden ihn bei der Default-Policy
`strict-origin-when-cross-origin` als Origin mit. Eine später ergänzte
`Referrer-Policy: no-referrer` (nginx oder Meta-Tag) würde die Kacheln also
lautlos abschalten — dann ist eine eigene Kachelquelle nötig.

## Gewünschtes Verhalten

### Projektkarte (`MapPage`/`MapView`)

- Der Overlay liegt **über** der Basemap und **unter** Wahlkreis-Umrissen,
  Projektlinien und Projektpunkten: das Netz ist Kontext, die Projekte sind das
  Thema.
- Schalter „Strecken" in `MapControls`, **standardmäßig an**.
- Der Zustand steht wie die übrigen Kartenoptionen in der URL: `?strecken=0`
  schaltet ihn ab, ohne Parameter ist er an. Ein geteilter Link transportiert
  damit die gesehene Ansicht.
- Klicks gehen unverändert an Projekt- bzw. Wahlkreis-Layer; ein Rasterlayer ist
  nicht abfragbar und ändert die Klicklogik nicht.
- Die Attribution erscheint zusammen mit der Basemap-Attribution in der
  MapLibre-Attributionszeile, solange der Layer sichtbar ist.

### Geometrie-Editor (`GeometryPreviewMap`)

- Overlay dauerhaft aktiv (kein Schalter), gleiche Quelle und Reihenfolge:
  Basemap → Strecken → vorhandene Geometrie → Vorschau → Punkte.
- Terra-Draw-Ebenen bleiben unberührt oben auf.

## Technische Umsetzung

Ein gemeinsames Modul `apps/frontend/src/shared/map/railwayTiles.ts` kapselt
Quelle, Layer und Sichtbarkeit, damit beide Karten dieselbe Definition nutzen:

| Export | Zweck |
|---|---|
| `resolveRailwayTileUrls(configured)` | reine Funktion: konfigurierte URL oder Default-Subdomains; `[]` bei `off` |
| `railwayTileUrls` | aufgelöste URLs aus `import.meta.env.REACT_APP_RAILWAY_TILE_LAYER_URL` |
| `hasRailwayTiles` | ob der Layer überhaupt verfügbar ist |
| `RAILWAY_SOURCE_ID` / `RAILWAY_LAYER_ID` | stabile IDs für Style und Sichtbarkeitswechsel |
| `railwaySourceSpec()` / `railwayLayerSpec(visible)` | Style-Bausteine für die Map-Initialisierung |
| `setRailwayVisibility(map, visible)` | Sichtbarkeit umschalten, no-op wenn der Layer fehlt |

Rasterkacheln werden mit `raster-opacity: 0.85` gezeichnet: die Streckenfarben
bleiben klar lesbar, treten aber hinter die kräftigen Projektfarben zurück.

## Akzeptanzkriterien

- [ ] Auf `/map` sind Bahnstrecken hinter den Projektlinien sichtbar.
- [ ] Der Schalter „Strecken" blendet den Layer aus und wieder ein.
- [ ] `?strecken=0` in der URL öffnet die Karte ohne Streckenlayer; der Schalter
      spiegelt diesen Zustand.
- [ ] Projekt- und Wahlkreis-Klicks funktionieren mit aktivem Layer unverändert.
- [ ] Im Geometrie-Editor ist das Netz beim Zeichnen und in der Routing-Vorschau
      sichtbar.
- [ ] Die Attribution „OpenRailwayMap / OpenStreetMap-Mitwirkende" ist auf der
      Karte erreichbar.
- [ ] Mit `REACT_APP_RAILWAY_TILE_LAYER_URL=off` erscheint weder Layer noch
      Schalter, und die Karte funktioniert wie zuvor.
