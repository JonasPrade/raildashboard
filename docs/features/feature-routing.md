# Feature: Routenvorschlag per GrassHopper

> **Abgrenzung:** Dieses Feature berechnet Bahnrouten automatisch über GraphHopper.
> Das **freie Zeichnen** von Linien und Punkten von Hand (für Neubaustrecken, die OSM nicht
> erfasst, Tram/U-Bahn ohne routbaren Pfad) ist separat: siehe
> [`feature-manual-geometry.md`](feature-manual-geometry.md) (Issue #27).

## Ziel

Editors und Admins können für ein Projekt eine Streckenroute über GraphHopper berechnen lassen, die Route auf der Karte vorschauen und als Projektgeometrie übernehmen.

## Scope

- Suchbare OperationalPoint-Auswahl für Start und Ziel
- Routenberechnung via `POST /api/v1/routes/calculate`
- Kartenvorschau als gestrichelter blauer Layer
- Accept / Reject Flow: Route als Projektgeometrie speichern oder verwerfen
- Liste gespeicherter Routen in ProjectDetail

## Nicht im Scope

- Automatische Routenberechnung ohne Nutzerinteraktion
- Routenberechnung für Straße oder Wasser
- U-Bahn- und Straßenbahnnetze (Issue #363; die Netzwahl unten ist dafür erweiterbar gebaut)

## Voraussetzungen

Backend-Infrastruktur ist vollständig implementiert (GraphHopper HTTP client, `RouteService`, Endpoints, ORM model, CRUD, caching, Tests). Docker-Service ist konfiguriert. **Human task**: OSM-PBF-Datei unter `data/graphhopper/map.osm.pbf` ablegen.

## Verhalten

- Nur für `editor` / `admin` sichtbar
- Fehlerfall 502 → "Routing-Dienst nicht erreichbar"
- Fehlerfall 422 → "Kein Pfad gefunden"
- Accept: schreibt Route in DB und aktualisiert `geojson_representation` des Projekts
- Start-, Ziel- und Zwischenhalte werden **nicht** als Punkte eingezeichnet oder gespeichert —
  sie steuern nur die Route. Nur wenn es ausdrücklich gewünscht ist (Schalter „Start, Ziel und
  Zwischenhalte als Punkte übernehmen“ im Editor, `add_stations: true` im MCP-Tool
  `route_project_geometry`), kommen sie als Betriebsstellen-Punkte dazu.
- Reject: kein API-Call, Vorschau wird verworfen

## Akzeptanzkriterien

- OperationalPoint-Suche liefert Treffer ab 2 Zeichen
- Route wird als gestrichelte blaue Linie auf der Karte gezeigt
- Entfernung (km) und Dauer (min) werden angezeigt
- Accept speichert Route und aktualisiert die Projektkarte
- Gespeicherte Routen sind in ProjectDetail (editor/admin) aufgelistet

## Technische Hinweise

### Step 1 — Backend: OperationalPoints-Endpoint
- `GET /api/v1/operational-points?q=<name_or_id>&limit=20`
- Datei: `api/v1/endpoints/operational_points.py`
- Schema: `OperationalPointRef { id, op_id, name, type, latitude, longitude }`
- CRUD: `search_operational_points(db, query, limit)` — `ILIKE` auf `name` und `op_id`
- Router in `api/v1/router.py` eintragen (public, kein Auth)
- `make gen-api` ausführen

### Step 2 — Frontend: Route Calculator Modal
- `features/routing/RouteCalculatorModal.tsx`
- Zwei searchable Combobox-Felder für Start/Ziel (via neuen Endpoint)
- "Berechnen"-Button → `POST /api/v1/routes/calculate` mit `{ waypoints, profile: "rail_default", options: {} }`
- Ergebnis (`RoutePreviewOut` GeoJSON Feature) in lokalem State

### Step 3 — Frontend: Kartenvorschau
- Temporärer MapLibre `LineLayer` auf Basis des Preview-GeoJSON
- Style: gestrichelte blaue Linie (distinct von Projektgeometrie)
- Anzeige Distanz und Dauer aus `properties.distance_m` / `properties.duration_ms`

### Step 4 — Frontend: Accept / Reject
- Accept: `POST /api/v1/projects/{id}/routes` + `PATCH /api/v1/projects/{id}` (geojson_representation) → `projectRoutesQuery` invalidieren
- Reject: Preview-State leeren, kein API-Call

### Step 5 — Frontend: Saved Routes List
- Sektion in ProjectDetail (editor/admin) via `GET /api/v1/projects/{id}/routes`
- Jede Zeile: Datum, Distanz, Dauer, "Als aktive Geometrie setzen" (PATCH), "Ersetzen" (PUT)

### Step 6 — Frontend: Query Hooks in `queries.ts`
- `useOperationalPointSearch(query)` — debounced, enabled ab 2 Zeichen
- `useCalculateRoute()` — mutation
- `useConfirmRoute(projectId)` — mutation
- `useReplaceRoute(projectId)` — mutation

## Implementierungsreihenfolge

1. [ ] Step 1: Backend OperationalPoints-Endpoint + `make gen-api`
2. [ ] Step 2: RouteCalculatorModal
3. [ ] Step 3: Kartenvorschau
4. [ ] Step 4: Accept/Reject Flow
5. [ ] Step 5: Saved Routes List
6. [ ] Step 6: Query Hooks

## Geplante und im Bau befindliche Gleise aus OSM (Issue #364)

Auftrag von Jonas am 2026-11-12, übergeben aus der TRAVE-Sitzung. Neubau- und Ausbaustrecken
sind in OSM oft schon als geplante oder im Bau befindliche Gleise erfasst und dort häufig
genauer trassiert als die Projektgeometrien im Dashboard. Das Routing soll diese Gleise
**wahlweise** nutzen, damit die Geometrie einer Neubaustrecke auf der OSM-Trasse geroutet statt
von Hand gezeichnet wird. TRAVE übernimmt die Geometrien danach aus dem Dashboard.

### Bestand vor der Änderung (nachgeprüft am Quelltext)

- OpenRailRouting v1.1 (`docker/graphhopper/Dockerfile`) nimmt nur Wege mit
  `railway=rail|light_rail|tram|subway|narrow_gauge` in den Graphen auf (`RailAccessParser`);
  das Profil `rail_default` (`rail.json`) schränkt zusätzlich auf `railway_class == RAIL` ein.
  `railway=proposed`/`construction` und die Lifecycle-Präfixe (`proposed:railway=*`,
  `construction:railway=*`) fehlen im Graphen vollständig — OpenRailRouting unterstützt sie
  nicht, auch nicht über ein Custom Model.
- Projektgeometrie entsteht im `GeometryEditor` (Route, Betriebsstellen, Zeichnen, Upload,
  Bearbeiten) bzw. über die MCP-Tools `route_project_geometry` und `edit_project_geometry`.
  Gespeichert wurde eine Route als ein Feature mit leeren `properties`; woher eine Linie
  stammt, war nicht erkennbar.

### Verhalten

- **Netzwahl beim Routen:** zwei getrennte Schalter „Gleise im Bau (OSM)“ und „Geplante Gleise
  (OSM)“ (Editor: Checkboxen unter dem Zielbahnhof; MCP: `use_construction`, `use_proposed`;
  REST: `networks: {construction, proposed}` an `POST /routes/calculate`). **Voreinstellung:
  beide aus — das Bestandsrouting bleibt unverändert** und führt nie über ein geplantes oder im
  Bau befindliches Gleis, auch nicht beim Einrasten des Start- oder Zielpunkts.
- **Ist ein Schalter an, werden die gewählten Gleise bevorzugt** (Priorität der Bestandsgleise
  ×0,1). Grund: Wer den Schalter setzt, routet eine Neubaustrecke; ein OSM-Gleis ohne
  Geschwindigkeitsangabe gilt im Router als 25 km/h und würde sonst gegen jede parallele
  Bestandsstrecke verlieren. Via-Bahnhöfe erzwingen weiterhin den Korridor.
- **Herkunft je Linie:** Eine Route wird beim Speichern in Abschnitte gleichen Gleisstatus
  geteilt, jede Linie trägt `properties.geometry_source = "routing"` und `track_status =
  existing | construction | proposed`. Gezeichnete Linien tragen `geometry_source = "manual"`,
  hochgeladene `"upload"`; eine im Editor verschobene Linie wird zu `"manual"`. Linien von vor
  dieser Änderung haben keine Angabe („Ohne Herkunftsangabe“). Eine Route nur auf Bestandsgleisen
  bleibt ein einziges Feature wie bisher. Die Teilung trennt zugleich Neubau- und
  Bestandsabschnitte, wie TRAVE sie braucht (Dashboard-Aufgabe #91, Punkt 2).
- **Sichtbar:** Der Editor zeigt unter „Aktuelle Geometrie“ die Kilometer je Herkunft, die
  Vorschau färbt die Route je Gleisstatus und nennt die Kilometer je Status. MCP:
  `get_project_geometry` liefert `origin` je Linie und `line_km_by_origin`.
- **Abweichung:** Vor dem Übernehmen wird die Route mit den bisherigen Linien des Projekts
  verglichen (Editor: Karte „Vergleich mit der bisherigen Geometrie“, MCP: `deviation`):
  Anteil der Route innerhalb 100 m der bisherigen Linien, Abdeckung der bisherigen Linien,
  größter (symmetrischer Hausdorff, alle 50 m abgetastet) und mittlerer Abstand. Weicht die
  Route deutlich ab (< 90 % im 100-m-Korridor oder > 1 km), weist der Editor darauf hin.
- **Nichts wird ungefragt überschrieben:** Der Editor hängt eine Route wie bisher an; ersetzt
  wird nur mit „Bestehende Geometrie löschen“ bzw. MCP `mode: "replace"` mit `apply: true`.
- **Kein Pfad:** Verbinden die gewählten Gleise die Wegpunkte nicht durchgehend, meldet der
  Router 400; das Backend macht daraus „Kein Pfad gefunden“ (422) mit dem Hinweis auf eine Lücke
  in OSM, statt wie bisher „Routing-Dienst nicht erreichbar“ (502).

### Technik

- **Router-Erweiterung** (`docker/graphhopper/orr/`): Patch auf OpenRailRouting v1.1 plus neue
  Dateien, beim Image-Build angewandt.
  - `LifecycleTags.normalize` läuft in `OSMRailwayReader.acceptWay` vor allen Parsern und macht
    aus `railway=proposed|construction` + `proposed|construction=TYP` (oder
    `…:railway=TYP`) sowie aus `proposed:railway=TYP` / `construction:railway=TYP` ohne
    `railway=*` die Tags eines Gleises in Betrieb (`railway=TYP`) plus ein künstliches
    Status-Tag. TYP muss ein Gleistyp des Routers sein (rail, light_rail, tram, subway,
    narrow_gauge); ein `railway=proposed` ohne Typ bleibt draußen (könnte auch eine Tram sein).
    Ein Gleis in Betrieb mit Lifecycle-Präfix (geplanter Umbau) bleibt `existing`.
  - Neues Encoded Value `railway_status` (`EXISTING`, `CONSTRUCTION`, `PROPOSED`), Parser
    `OSMRailwayStatusParser`, als Path Detail abrufbar.
- **Profile** (`docker/graphhopper/config.yml`, `custom_models/`):
  - `rail_default`: nur `railway_status == EXISTING`, CH-vorbereitet (schnell).
  - `rail_flex`: alle Gleise der Klasse RAIL; das Backend schränkt je Anfrage mit einem
    Query-Custom-Model ein (`services/routing_networks.py`). Nicht vorbereitet, flexibel
    geroutet (langsamer, für Einzelanfragen ausreichend).
  - **Erweiterbar für #363:** Ein weiteres Netz ist ein weiterer Schalter, also eine weitere
    Zeile im Query-Modell; das Basismodell von `rail_flex` muss dafür das breiteste Netz
    zulassen (ein Query-Modell kann Prioritäten nur senken). Keine 2ⁿ Profile.
- **Backend:** `RoutingClient` fragt immer das Path Detail `railway_status` ab; mit Query-Modell
  per `POST /route`. `RouteService.calculate_only` liefert zusätzlich `networks`, `sections`,
  `status_km`; der Cache-Schlüssel enthält die Schalter. `services/geometry_deviation.py`
  berechnet die Abweichung in einer lokalen metrischen Ebene.
- **Graph-Cache:** Das Image trägt einen Fingerabdruck von Konfiguration, Custom Models und
  Patch; der Entrypoint verwirft einen Cache mit anderem (oder ohne) Fingerabdruck und baut ihn
  neu. Ohne das würde GraphHopper nach dem Deploy mit dem alten Cache gar nicht starten (neues
  Encoded Value, neues Profil).
- **Prüfung:** Stufe `test` im GraphHopper-Dockerfile: Unit-Tests der Normalisierung, dann der
  echte Entrypoint mit der echten Konfiguration gegen ein kleines Testnetz
  (`test/planned-tracks.osm`) — `rail_default` nutzt und rastet nie auf geplanten Gleisen,
  jeder Schalter schaltet genau sein Netz zu (`test/smoke.sh`). Ob diese Stufe in `make test`
  läuft, ist offen (W1 unten).

### Folgen für den Betrieb

- Nach dem ersten Deploy baut GraphHopper den Graphen für Deutschland neu (Download entfällt,
  die PBF liegt im Volume). Bis dahin ist das Routing nicht verfügbar; das Backend und sein
  `/healthz` sind davon unabhängig. Der Graph wird größer (zusätzliche Gleise, ein weiteres
  Encoded Value, ein zweites Profil).
- `GRAPH_VERSION` muss nicht erhöht werden: Der Cache-Schlüssel gespeicherter Routen enthält die
  Schalter, Bestandsrouten bleiben gültig.

### Offene Entscheidungen (Widerspruchs-Check 2026-11-12, Jonas entscheidet)

- **W1 – GraphHopper in `make test`?** `docs/workflow.md` → Ausnahmen: „GraphHopper wird nur in
  `release.yml` gebaut, nicht in `make test`“ (Maven-Build dauert Minuten). Der Patch an
  OpenRailRouting ist ohne Build ungeprüft; vorläufig steht die `test`-Stufe in `make test`
  (Entwurf, PR als Draft). Optionen: (a) in `make test` aufnehmen und die Ausnahme streichen,
  (b) die `test`-Stufe nur in `release.yml` vor dem Push des Images fahren,
  (c) nur bei Änderungen unter `docker/graphhopper/` in der CI bauen (zweiter Weg, widerspricht
  „ein Kommando“).
- **W2 – Wer gewinnt bei abweichender Trasse?** Empfehlung aus der TRAVE-Sitzung: OSM gewinnt,
  wenn es die Enden durchgehend verbindet; die Abweichung wird gemeldet. Noch nicht entschieden.
  Bis dahin ersetzt nichts automatisch; 1535 (Bielefeld–Seelze), 1773 und 1663 (mehrere
  Varianten) entscheidet Jonas einzeln.
- **W3 – Bevorzugungsfaktor.** Ist ein Schalter an, zählen Bestandsgleise ×0,1. Alternative:
  gleich gewichten (dann verliert ein OSM-Gleis ohne `maxspeed` meist gegen die Bestandsstrecke).

### Akzeptanzkriterien

- [ ] Ohne Schalter: Route wie bisher, kein Abschnitt auf geplanten oder im Bau befindlichen
      Gleisen, auch nicht am Start- oder Zielpunkt (Smoke-Test).
- [ ] „Gleise im Bau“ bzw. „Geplante Gleise“ einzeln zuschaltbar; die Vorschau färbt die
      Abschnitte und nennt die Kilometer je Status.
- [ ] Gespeicherte Linien tragen ihre Herkunft; der Editor zeigt die Kilometer je Herkunft.
- [ ] Vor dem Übernehmen: Abweichung von der bisherigen Geometrie sichtbar (Editor und MCP).
- [ ] Nach dem Deploy startet GraphHopper mit neu gebautem Graphen von selbst.
- [ ] Abgleich nach dem Deploy (siehe unten) gemeldet.

### Abgleich nach dem Deploy

Erst nach dem Deploy möglich (der Graph mit geplanten Gleisen existiert nur dort). Je Projekt
`route_project_geometry` mit `use_proposed`/`use_construction`, **ohne** `apply`, zwischen den
Enden der bisherigen Geometrie: Verbindet OSM die Enden durchgehend (sonst 422)? Wie groß ist
`deviation`? Ergebnisse als Kommentar in Issue #364, geschrieben wird nichts.

| Gruppe (laut TRAVE, ungeprüft) | Projekte |
|---|---|
| OSM deckt gut | 1783, 1507, 1845, 1553 |
| OSM deckt teilweise | 1510, 1556 |
| andere Trasse als das Dashboard | 1535 (Bielefeld–Seelze, Aufgabe #92), 1773 |
| mehrere Varianten | 1663 (Hamburg–Hannover) |
| OSM hat nichts (Gegenprobe) | 1562, 1627, 1523, 1486, 2018, 1846 |

Berührt sind die Dashboard-Aufgaben #90 (1774 Blankenheim–Kirchheim: Neubauabschnitte ggf.
routbar statt gezeichnet), #91 (Geometrien für das TRAVE-Zielnetz: getrennte Linien für Neubau
und Bestand) und #92 (1535: die Angleichung an die Trasse des Zielfahrplans ist mit OSM als
Vorlage möglich, sofern OSM dieselbe Trasse hat).
