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
- Routen, die Vollbahn- und S-/U-Bahn-/Straßenbahngleise in einem Zug mischen (siehe „Gleisarten“ unten: abschnittsweise routen und anhängen)

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
  jeder Schalter schaltet genau sein Netz zu (`test/smoke.sh`). Die Stufe läuft in `make test` (W1 unten).

### Folgen für den Betrieb

- Nach dem ersten Deploy baut GraphHopper den Graphen für Deutschland neu (Download entfällt,
  die PBF liegt im Volume). Bis dahin ist das Routing nicht verfügbar; das Backend und sein
  `/healthz` sind davon unabhängig. Der Graph wird größer (zusätzliche Gleise, ein weiteres
  Encoded Value, ein zweites Profil).
- `GRAPH_VERSION` muss nicht erhöht werden: Der Cache-Schlüssel gespeicherter Routen enthält die
  Schalter, Bestandsrouten bleiben gültig.

### Entscheidungen (Jonas, 2026-11-12)

Aus dem Widerspruchs-Check; Entscheidungskarten im Vault, Stapel EKS-2026-024.

- **W1 – GraphHopper wird in `make test` geprüft** (EK-2026-150, A). Die Ausnahme in
  `docs/workflow.md` („GraphHopper nur in `release.yml`“) entfällt: Der Router ist mit dem Patch
  eigener Code mit einer Sicherheitszusage. Verworfen: nur in `release.yml`; nur bei Änderungen
  unter `docker/graphhopper/`.
- **W2 – Abweichende, von Hand gezeichnete Geometrien werden nach dem Deploy schrittweise durch
  die OSM-Trasse ersetzt** (EK-2026-151). Je Projekt erst ohne `apply` routen; verbindet OSM die
  Enden durchgehend, ersetzt Claude die Geometrie per MCP (Änderungsprotokoll, rücknehmbar) und
  hält Abweichung und Ergebnis in der Dashboard-Aufgabe des Projekts fest. Mehrere Varianten in
  OSM (1663) und Lücken in OSM gehen als Rückfrage an Jonas. Verworfen: bisherige Geometrie
  bleibt maßgeblich.
- **W3 – Gewählte geplante bzw. im Bau befindliche Gleise werden bevorzugt** (EK-2026-152, A):
  Bestandsgleise ×0,1, solange ein Haken gesetzt ist. Verworfen: gleich gewichten; nur
  geplante Gleise.

### Wann die Bevorzugung zum Problem wird

Der Router minimiert Fahrzeit geteilt durch Priorität. Ein OSM-Gleis ohne `maxspeed` gilt als
25 km/h, eine Hauptbahn mit 160 km/h als rund 144 km/h; mit Faktor 0,1 auf den Bestand ist ein
Kilometer geplantes Gleis (1/25) billiger als ein Kilometer Bestand (1/14,4). Ein Weg über
geplante Gleise wird deshalb genommen, **solange er höchstens etwa 1,7-mal so lang ist** wie der
über den Bestand — mit `maxspeed` an den geplanten Gleisen noch deutlich länger. Daraus folgen
die Fälle, in denen das Ergebnis falsch sein kann:

- **Fremde Planungen in der Nähe:** Die Route biegt auf geplante Gleise eines anderen Projekts
  ab, wenn sie grob in dieselbe Richtung führen (Verbindungskurven, parallele Neubaustrecken).
- **Mehrere Varianten in OSM** (z. B. 1663 Hamburg–Hannover): Der Router nimmt die billigste,
  nicht die beschlossene.
- **Veraltete Planungen:** OSM behält oft aufgegebene `railway=proposed`-Trassen; die Route kann
  darüber laufen.
- **Ausbaustrecken:** Wird nur ein Teil neu gebaut, zieht die Route auch Bestandsabschnitte auf
  benachbarte geplante Gleise.

Gegenmittel: Via-Bahnhöfe an Anfang und Ende jedes Neubauabschnitts setzen, in der Vorschau
„km je Status“ und den Vergleich mit der bisherigen Geometrie prüfen, den Haken nur für das
eine Projekt setzen. Ohne Haken tritt keiner dieser Fälle auf.

### Akzeptanzkriterien

- [ ] Ohne Schalter: Route wie bisher, kein Abschnitt auf geplanten oder im Bau befindlichen
      Gleisen, auch nicht am Start- oder Zielpunkt (Smoke-Test).
- [ ] „Gleise im Bau“ bzw. „Geplante Gleise“ einzeln zuschaltbar; die Vorschau färbt die
      Abschnitte und nennt die Kilometer je Status.
- [ ] Gespeicherte Linien tragen ihre Herkunft; der Editor zeigt die Kilometer je Herkunft.
- [ ] Vor dem Übernehmen: Abweichung von der bisherigen Geometrie sichtbar (Editor und MCP).
- [x] Nach dem Deploy startet GraphHopper mit neu gebautem Graphen von selbst (Aufgabe #93, 2026-11-12).
- [x] Abgleich nach dem Deploy (siehe unten) gemeldet (2026-11-12 und 2026-11-23).

### Abgleich nach dem Deploy

Erst nach dem Deploy möglich (der Graph mit geplanten Gleisen existiert nur dort). Je Projekt
`route_project_geometry` mit `use_proposed`/`use_construction`, **ohne** `apply`, zwischen den
Enden der bisherigen Geometrie: Verbindet OSM die Enden durchgehend (sonst 422)? Wie groß ist
`deviation`? Danach nach W2 schrittweise ersetzen. Die Schritte stehen als LLM-Aufgaben im
Dashboard (Tag `@LLM`), je Projekt eine.

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

#### Ergebnis (2026-11-12 und 2026-11-23)

Am 2026-11-12 (nur Gleise mit Typ): 1845 ersetzt (OSM verbindet die Enden, 14,49 km); bei allen
anderen fand der Router keine oder nur Splitter geplanter Gleise. Am 2026-11-23, nach #363, erneut
mit `track_classes: ["rail", "unknown"]`, `use_proposed` und `use_construction`, ohne `apply`:

| Projekt | Ergebnis | Aufgabe |
|---|---|---|
| 1783 | 57,3 km, davon 0,22 km im Bau, sonst Bestand; 4 % im Korridor | #94 offen |
| 1507 | 66,3 km nur Bestand | #95 offen |
| 1553 | kein Pfad | #97 offen |
| 1510 | Geometrie aus Teilprojekten, nicht direkt routbar | #98 offen |
| 1556 | 73,7 km nur Bestand | #99 offen |
| 1535 | 98,1 km nur Bestand (über Minden), keine OSM-Trasse über Kirchhorsten | #100, #92 offen |
| 1773 | 62,0 km, davon 0,51 km im Bau | #101 offen |
| 1663 | 153,8 km nur Bestand, keine Variante routbar | #102 offen |
| Gegenprobe | 1562, 1627, 1523, 1846 nur Bestand; 1486, 2018 kein Pfad | #103 erledigt |

Kein Projekt hat einen Abschnitt der Gleisart `unknown`. Der Router-Code für typlose Planungen ist
korrekt (Quelltext, Smoke-Test). Offen ist, ob OSM die Planungen gar nicht führt, mit einem Typwert,
den der Router nicht kennt, oder als lose Wege, die als Kleinst-Teilnetz
(`prepare.min_network_size`) aus dem Graphen fallen; Overpass ist aus der Sandbox nicht erreichbar.
Nichts ersetzt; Entscheidung über das weitere Vorgehen: EK-2026-404.

## Gleisarten (S-Bahn, U-Bahn, Straßenbahn, Schmalspur) (Issue #363)

Anlass (Jonas, 2026-11-19): Die i2030-S-Bahn-Projekte in Berlin liegen auf den parallelen
Fernbahn- und Gütergleisen oder fahren Umwege, weil die Berliner S-Bahn in OSM
`railway=light_rail` ist und der Router nur `railway=rail` nutzt. Probe im Prod-Routing:
Treptower Park (DE00BTP) → Sonnenallee (DE00BSO) ergibt 7,05 km über Baumschulenweg statt rund
2 km über den Ring. Fortsetzung des Musters aus #364 (Abschnitt oben). Zusätzlich aus #363:
geplante Gleise ohne Gleistyp und Haltestellen von U-Bahn und Straßenbahn für die Wegpunktsuche.

### Bestand vor der Änderung (nachgeprüft am Quelltext)

- OpenRailRouting v1.1 nimmt `railway=rail|light_rail|tram|subway|narrow_gauge` bereits in den
  Graphen auf (`RailAccessParser`); das Encoded Value `railway_class` (`OTHER`, `RAIL`, `SUBWAY`,
  `TRAM`, `NARROW_GAUGE`, `LIGHT_RAIL`, `FUNICULAR`, als Path Detail kleingeschrieben) steht in
  `graph.encoded_values`. Ausgeschlossen werden die übrigen Gleisarten nur in den Custom Models
  (`railway_class != RAIL` → Priorität 0).
- Ein `railway=proposed|construction` ohne Gleistyp bleibt draußen (`LifecycleTags`). Für die
  meisten Neubaustrecken aus dem Abgleich von #364 (1507, 1535, 1556, 1663, 1773, 1783) fand der
  Router deshalb keine geplanten Gleise; die Dashboard-Aufgaben #94, #95, #97–#103 warten darauf.
- Wegpunkte (Start, Ziel, Via) kommen aus der Tabelle `operational_point` (RINF): nur
  Betriebsstellen der Eisenbahn, darunter die S-Bahnhöfe. U-Bahn- und Straßenbahnhalte fehlen;
  im MCP-Tool gehen nur freie Koordinaten.

### Verhalten

- **Gleisart-Auswahl, exklusiv zur Vollbahn:** Neben den Status-Schaltern („im Bau“, „geplant“)
  wählt man die Gleisarten. Vorgabe ist **Vollbahn** (`rail`). Wählbar sind daneben
  **S-Bahn/Stadtbahn** (`light_rail`), **U-Bahn** (`subway`), **Straßenbahn** (`tram`) und
  **Schmalspur** (`narrow_gauge`), untereinander beliebig kombiniert. Vollbahn und eine dieser
  Gleisarten nie zusammen: Der Editor wählt die Vollbahn ab, sobald eine andere Gleisart
  angehakt wird, und umgekehrt; das Backend lehnt `rail` zusammen mit einer anderen Gleisart mit
  422 ab. Kein Bevorzugungsfaktor zwischen Gleisarten (entfällt durch die Exklusivität).
- **Gleisart unbekannt (nur Planungen):** Geplante oder im Bau befindliche Gleise, bei denen OSM
  keinen Gleistyp nennt (bloßes `railway=proposed|construction`), sind eine sechste Gleisart
  `unknown`. Sie hat einen eigenen Haken, ist mit **jeder** Auswahl kombinierbar (auch mit der
  Vollbahn — Ausnahme von der Exklusivität, weil es keine Bestandsgleise dieser Art gibt) und
  wirkt nur zusammen mit „im Bau“ bzw. „geplant“; ohne einen der beiden lehnt das Backend sie
  mit 422 ab. Ohne Haken bleiben Planungen ohne Typ draußen — eine Straßenbahn-Planung gilt nie
  stillschweigend als Eisenbahn.
- **Status-Schalter bleiben unabhängig:** Eine geplante S-Bahn ist `light_rail` + „geplant“.
  Die Bevorzugung gewählter geplanter bzw. im Bau befindlicher Gleise (Bestand ×0,1, W3) gilt
  innerhalb der gewählten Gleisarten weiter.
- **Ohne Auswahl ändert sich nichts:** Nur Vollbahn, kein Status-Schalter → Profil
  `rail_default` wie bisher; die Route nutzt und rastet nie auf S-Bahn-, U-Bahn-,
  Straßenbahn-, Schmalspur- oder typlose Gleise ein.
- **Gemischte Routen:** Ein S-Bahn-Projekt, das auf Fernbahngleise wechselt, ist ohne Kombimodus
  nicht in einem Zug routbar. Seit 2026-11-23 überbrückt der Schalter „Lücken über andere
  Gleisarten überbrücken“ solche Stücke (Abschnitt „Kombimodus“ unten, EK-2026-389); sonst
  abschnittsweise routen (Editor: Route anhängen) und die Teile zusammensetzen.
- **Herkunft je Linie:** Eine Route wird in Abschnitte gleichen Status **und** gleicher Gleisart
  geteilt; jede Linie trägt zusätzlich `properties.railway_class` (`rail`, `light_rail`, `subway`,
  `tram`, `narrow_gauge`, `unknown`). Eine Route nur auf Vollbahn-Bestand bleibt ein einziges
  Feature. Linien von vor dieser Änderung haben keine Angabe und zählen als „ohne Gleisart“,
  nicht als Vollbahn.
- **Sichtbar:** Die Editor-Vorschau nennt neben den km je Status die km je Gleisart; „Aktuelle
  Geometrie“ zeigt die km je Gleisart der gespeicherten Linien. MCP: `get_project_geometry`
  liefert `railway_class` je Linie und `line_km_by_class`, `route_project_geometry` meldet
  `route.class_km`.
- **Haltestellen aus OSM für die Wegpunktsuche:** Bahnhöfe und Halte von U-Bahn, S-Bahn/Stadtbahn
  (`station=light_rail`) und Straßenbahn kommen aus OSM als weitere Betriebsstellen in
  `operational_point` (`source = "osm"`, `network = subway | light_rail | tram`, `op_id` =
  `OSM-<n|w|r><id>`). RINF-Betriebsstellen tragen `source = "rinf"`, `network = "rail"`. Die Suche
  (REST `GET /operational-points?network=…`, Editor, MCP `search_operational_points`) nennt das
  Netz je Treffer und lässt sich danach filtern; im Editor zeigt jeder Treffer ein Kürzel
  (S, U, Tram) — gleiche Namen oder Kürzel verschiedener Netze sind so unterscheidbar. Ein
  OSM-S-Bahnhof, der schon als RINF-Betriebsstelle vorhanden ist (gleicher Name, höchstens
  300 m entfernt), wird nicht doppelt angelegt. Straßenbahnhalte (`railway=tram_stop`) werden
  je Name auf einen Punkt zusammengefasst (beide Richtungen, höchstens 300 m). Import mit
  `make import-osm-stops` (Overpass-API, Deutschland), erneut ausführbar: vorhandene OSM-Halte
  werden aktualisiert, nicht dupliziert; Halte, die in OSM verschwunden sind, bleiben stehen
  (sie könnten Projekten zugeordnet sein).
- **Einrasten:** Eine Wegpunkt-Koordinate rastet an das nächste Gleis der gewählten Gleisarten
  ein. Ein RINF-S-Bahnhof funktioniert also mit dem S-Bahn-Haken, ein U-Bahnhof aus OSM mit dem
  U-Bahn-Haken.

### Technik

- **Router-Erweiterung** (`docker/graphhopper/orr/`):
  - `LifecycleTags.normalize`: Ein `railway=proposed|construction` ohne `<status>=TYP` und ohne
    `<status>:railway=TYP` bekommt das Status-Tag und bleibt sonst unverändert; damit gilt es
    für `railway_class` als `OTHER`. Nennt der Weg einen Typ, den der Router nicht kennt (z. B.
    `proposed=platform`), bleibt er draußen.
  - `RailAccessParser` (Patch): Ein Weg mit Status-Tag ist befahrbar, auch ohne Gleistyp.
    `OTHER` kommt damit nur bei typlosen Planungen vor.
- **Profile:**
  - `rail_default` bleibt unverändert (nur `RAIL`, nur Bestand, CH).
  - `rail_flex`: Basismodell auf das breiteste Netz erweitert — jeder befahrbare Weg
    (`RAIL`, `LIGHT_RAIL`, `SUBWAY`, `TRAM`, `NARROW_GAUGE`, `OTHER`). Neuer Fingerabdruck →
    der Graph wird nach dem Deploy neu gebaut.
- **Backend** (`services/routing_networks.py`): `networks` bekommt `track_classes` (Liste,
  Vorgabe `["rail"]`). Alles außer „nur Vollbahn ohne Status-Schalter“ läuft auf `rail_flex`
  mit einem Query-Modell: je nicht gewählter Gleisart `railway_class == X` ×0 (`unknown` ↔
  `OTHER`), je nicht gewähltem Status `railway_status == X` ×0, mit Status-Schalter Bestand
  ×0,1. Validierung (422): leere Liste, unbekannte Gleisart, `rail` mit anderer Gleisart außer
  `unknown`, `unknown` ohne Status-Schalter. `RoutingClient` fragt zusätzlich das Path Detail
  `railway_class` ab; `route_sections` teilt nach (Status, Gleisart); `class_km` je Gleisart;
  der Cache-Schlüssel enthält `track_classes`, sobald sie von der Vorgabe abweichen.
  REST `POST /routes/calculate`: `networks: {construction, proposed, track_classes}`; MCP
  `route_project_geometry`: Parameter `track_classes` (Vorgabe `["rail"]`).
- **Haltestellen:** Migration (Expand): `operational_point.source` und `.network`, beide mit
  Server-Default (`rinf`, `rail`). Importer `scripts/import_osm_stops.py` (Overpass-Abfrage,
  Auswahl und Zusammenfassen in reinen Funktionen, unit-getestet), Makefile-Ziele
  `import-osm-stops` / `docker-import-osm-stops`.
- **Hinweise zu OSM-Tags** (Anleitung `GeometrieGuidePage`, Tool-Beschreibung): Berliner und
  Hamburger S-Bahn sind `light_rail`, Münchner, Stuttgarter, Frankfurter und Rhein-Ruhr-S-Bahn
  `rail`; Stadtbahnen teils `tram`, teils `light_rail` → beide wählen.
- **Prüfung:** Testnetz `test/planned-tracks.osm` um ein paralleles `light_rail`-Gleis, eine
  U-Bahn, eine Straßenbahn, ein Schmalspurgleis und ein typloses geplantes Gleis erweitert;
  `smoke.sh`: ohne Auswahl nie auf diesen Gleisen und nie dorthin eingerastet; jede Gleisart
  einzeln wählbar und nur sie wird benutzt (auch beim Einrasten neben einem parallelen
  Vollbahngleis); `light_rail` + `tram`; Kombination mit „geplant“; `unknown` nur mit Haken.
  Unit-Tests der Query-Statements, der Validierung, der Abschnitte und des Haltestellen-Imports.

### Folgen für den Betrieb

- Nach dem Deploy baut GraphHopper den Graphen neu (neues Basismodell, typlose Planungen im
  Graphen). Bis dahin ist das Routing nicht verfügbar; `/healthz` hängt nicht davon ab.
- Die Migration fügt zwei Spalten mit Default hinzu (rückwärtskompatibel). Die OSM-Haltestellen
  kommen erst mit `make docker-import-osm-stops` nach dem Deploy (einmalig, später bei Bedarf).

### Entscheidungen (Jonas, 2026-11-19)

Stapel EKS-2026-051 im Vault; die letzten beiden aus der Rückfrage in der Umsetzungssitzung.

- **Gleisarten exklusiv** (EK-2026-355, C): Vollbahn ist Vorgabe, jede andere gewählte
  Gleisart schaltet sie ab; andere Gleisarten untereinander kombinierbar, kein
  Bevorzugungsfaktor. Verworfen: Bevorzugung ×0,1; gleich gewichten. Die in #363 genannte
  Kombination Eisenbahn + U-Bahn ist damit überholt. Ergänzt 2026-11-23 durch den
  Kombimodus (EK-2026-389): Mit eigenem Schalter dürfen andere Gleisarten Lücken
  überbrücken; ohne Schalter gilt die Exklusivität unverändert.
- **Fünf Gleisarten inkl. Schmalspur** (EK-2026-356). Verworfen: ohne Schmalspur; Vollbahn
  immer an.
- **Linien speichern die Gleisart** (EK-2026-357, A), km je Gleisart in Editor und MCP.
  Verworfen: nur Status.
- **Planungen ohne Gleistyp: eigener Haken** „Gleisart unbekannt (nur Planungen)“, mit jeder
  Auswahl kombinierbar, wirkt nur mit einem Status-Schalter. Verworfen: automatisch mit dem
  Status-Schalter; nur zusammen mit der Vollbahn.
- **Haltestellen von U-Bahn, S-Bahn/Stadtbahn und Straßenbahn aus OSM importieren** und in der
  Suche nach Netz unterscheiden. Verworfen: nur Doku und Folge-Issue; Wegpunkte per Klick auf
  die Karte.
- Weiter gültig: W1 (GraphHopper in `make test`), W3 (Bevorzugung geplanter Gleise).

### Akzeptanzkriterien

- [ ] Ohne Auswahl: Route wie bisher, nie auf S-Bahn-, U-Bahn-, Straßenbahn-, Schmalspur- oder
      typlosen Gleisen, auch nicht beim Einrasten (Smoke-Test).
- [ ] S-Bahn/Stadtbahn, U-Bahn, Straßenbahn, Schmalspur einzeln und untereinander kombiniert
      wählbar; Vollbahn nie zusammen mit ihnen (Editor schaltet um, Backend lehnt ab);
      Kombination mit „geplant“/„im Bau“ möglich.
- [ ] Typlose Planungen nur mit Haken „Gleisart unbekannt“ und Status-Schalter.
- [x] Treptower Park → Sonnenallee mit S-Bahn rund 2 km über den Ring (Prod-Probe nach dem
      Deploy: 2,41 km, nur `light_rail`; Vollbahn unverändert 7,05 km, 2026-11-23).
- [ ] Linien tragen `railway_class`; Editor und MCP zeigen km je Gleisart.
- [ ] Nach `make docker-import-osm-stops` findet die Suche U-Bahn- und Straßenbahnhalte mit
      Netz-Kürzel; Filter nach Netz in REST und MCP.
- [x] GraphHopper startet nach dem Deploy mit neu gebautem Graphen von selbst.

### Abgleich nach dem Deploy

1. `make docker-import-osm-stops`.
2. Prod-Probe Treptower Park → Sonnenallee mit `track_classes: ["light_rail"]`, ohne `apply`.
3. i2030-S-Bahn-Projekte mit S-Bahn-Gleisart neu routen, erst ohne `apply`, dann ersetzen
   (Muster W2/EK-2026-151); dabei die von Hand gezeichneten Ring-Stücke Treptower Park –
   Sonnenallee („Skizze, OSM-Lücke im Routing“) entfernen: 3227 Südring, 3226 Ostring,
   3228 Nordkreuz (Wendeschleife), 3229 Ostkreuz – Erkner, 3213 Hoppegarten – Strausberg,
   3215 Buch – Bernau, 3224 Frohnau – Oranienburg, 3190 S25 Nord, 3199 S25 Süd (Teltow Stadt –
   Stahnsdorf mit „geplant“, falls in OSM). 3198 Südlicher Innenring bleibt auf der Vollbahn
   (Regionalverkehr); dessen Skizzen-Stück wird über Vollbahngleise ersetzt, sofern routbar.
4. Neubaustrecken aus dem Abgleich von #364 mit „Gleisart unbekannt“ erneut prüfen
   (Dashboard-Aufgaben #94, #95, #97–#103).
5. U-Bahn-Projekte (u. a. 2284, 2537) und die schematischen Stadtbahn-Trassen (EK 6-09)
   prüfen.

#### Ergebnis (2026-11-23)

1. Haltestellen-Import noch nicht gelaufen (`search_operational_points` „Hermannplatz“ mit
   `networks: ["subway"]` leer) – Handschritt auf dem Server.
2. Prod-Probe: S-Bahn 2,41 km über den Ring, Vollbahn 7,05 km über Baumschulenweg.
3. i2030-S-Bahn (Deckung = Anteil der Route im 100-m-Korridor des Bestands):

| Projekt | Ergebnis |
|---|---|
| 3226 Ostring | ersetzt: Gesundbrunnen – Treptower Park – Neukölln, 14,07 km `light_rail`, 96 %, max. 361 m; Skizze entfernt. Mit Wegpunkt Ostkreuz entsteht eine Schleife (Einrasten am Stadtbahn-Gleis), daher ohne |
| 3227 Südring | ersetzt: Neukölln – Südkreuz (Ringbahn) – Westkreuz, 12,58 km `light_rail`, 100 %, max. 69 m. Endpunkt als Koordinate auf dem Ring; der Westkreuz-Wegpunkt rastet sonst auf dem Stadtbahn-Gleis ein (1 km Umweg) |
| 3199 S25 Süd | Teltow Stadt – Stahnsdorf aus OSM-Planung angehängt (3,96 km geplant, `light_rail`), Länge 2,85 → 6,90 km |
| 3229, 3213, 3215 | waren schon mit S-Bahn geroutet (2026-11-22) |
| 3224, 3190 | siehe Kombimodus unten; Ersetzen offen (EK-2026-400) |
| 3228 Nordkreuz | nicht ersetzt: am Kreuzungsbahnhof Gesundbrunnen wendet jede Route hinter dem Ziel (EK-2026-402) |
| 3198 Innenring | Skizze Sonnenallee – Treptower Park über Vollbahn nicht routbar (7 km Umweg); mit Kombimodus 2,41 km über das S-Bahn-Gleis (EK-2026-401) |

4. Neubaustrecken mit „Gleisart unbekannt“: siehe Ergebnis im Abschnitt zu #364 oben.
5. U-Bahn: 2537 ersetzt (U5 22,09 km, 86 %; U8 18,06 km, 90 %; Länge 40,15 km). 2284 (U2/U5/U8)
   nur 57–67 % im Korridor der groben Skizzen, U2 endet rund 1 km vor Pankow (EK-2026-400).
   Stadtbahn-Trassen aus EK 6-09: 2937 deckt sich mit der OSM-Planung auf 3 m und ist ersetzt
   (Linie jetzt `light_rail`, geplant); 2936 hat in OSM eine abweichende Planung (EK-2026-403);
   2917 und 2938 ohne Planung in OSM.

## Kombimodus: Lücken über andere Gleisarten überbrücken (2026-11-23)

Anlass: Nach dem Deploy von #363 meldete `route_project_geometry` für zwei Berliner
S-Bahn-Projekte mit `track_classes: ["light_rail"]` „Kein Pfad im Schienennetz“: 3224
„S-Bahn Berlin: Streckenausbau Frohnau – Oranienburg“ und 3190 „S25 Nord“ (Schönholz –
Hennigsdorf). Ostkreuz – Erkner, Buch – Bernau und Hoppegarten – Strausberg liefen.

### Befund (Proben im Produktions-Routing ohne `apply`, 2026-11-23)

- **Frohnau – Oranienburg:** `light_rail` geht durch von Frohnau bis Birkenwerder und ab
  etwa 700 m nördlich davon bis Oranienburg (Borgsdorf – Lehnitz – Oranienburg geprüft).
  Dazwischen findet der Router mit keiner Stadt-Gleisart einen Pfad, auch nicht mit „im Bau“,
  „geplant“ und „unbekannt“. Dort teilen sich S-Bahn und Regionalbahn das Gleis, OSM führt
  es als `railway=rail`. Mit Vollbahn allein kommt man durch das Stück, aber nicht nach
  Frohnau (dort liegt nur S-Bahn-Gleis).
- **S25 Nord:** `light_rail` endet westlich von Alt-Reinickendorf (13,348° O) und beginnt erst
  etwa 350 m nördlich von Tegel wieder. Die Kremmener Bahn dazwischen (Karl-Bonhoeffer-
  Nervenklinik, Eichborndamm, Tegel) ist `railway=rail`. Über das flexible Profil mit Vollbahn
  findet der Router sie (6,7 km, nur `rail`). Das Standardprofil `rail_default` findet sie
  nicht: Das Stück hängt nur über S-Bahn-Gleise am übrigen Vollbahnnetz und fällt als
  Teilnetz unter `prepare.min_network_size` (200) heraus. Daher kam der Umweg von 31 km mit
  der Vollbahn.
- **Kein Einrast-Problem:** `snap_preventions_default` (Tunnel, Brücke, Fähre) verschiebt
  höchstens den Startpunkt auf das nächste Gleis daneben, trennt aber keine Strecke.
- **Quelle der Tags:** OpenRailRouting setzt `railway_class` allein aus `railway=*`. Overpass
  und Geofabrik waren aus der Sandbox nicht erreichbar, die Tags sind indirekt über das
  Routing belegt.

### Verhalten

- **Schalter „Lücken über andere Gleisarten überbrücken“** (Editor, REST
  `networks.bridge_gaps`, MCP `bridge_gaps`), Vorgabe aus. Ist er an, bekommen die nicht
  gewählten Gleisarten (`rail`, `light_rail`, `subway`, `tram`, `narrow_gauge`) Priorität
  ×0,01 statt 0. Die Route bleibt auf den gewählten Gleisarten, solange es einen Weg gibt,
  und nimmt fremde Gleise nur dort, wo die gewählten eine Lücke haben. Der Faktor liegt weit
  unter den in EK-2026-355 verworfenen 0,1: Eine parallele schnellere Vollbahn gewinnt nur,
  wenn der Weg auf den gewählten Gleisen über hundertmal teurer wäre.
- **Planungen ohne Gleisart** (`unknown`) kommen nie über den Kombimodus herein, nur über
  ihren eigenen Haken. Die Status-Schalter gelten unverändert (kein geplantes Gleis ohne
  „geplant“).
- **Auch mit Vollbahn:** Mit Vollbahn und Kombimodus läuft die Route auf `rail_flex`. Damit sind
  Vollbahnstücke erreichbar, die nur über S-Bahn-Gleise angebunden sind (Kremmener Bahn).
- **Ergebnis:** `bridged_km` = km auf nicht gewählten Gleisarten; `foreign_waypoints` = Indizes
  der Wegpunkte, die auf ein Gleis einer anderen Gleisart eingerastet sind (im Kombimodus
  rastet ein Wegpunkt am nächsten zugelassenen Gleis ein, das kann die parallele Vollbahn
  sein). Gespeicherte Linien tragen ihre tatsächliche Gleisart; ein überbrücktes Stück ist
  also als `rail` gespeichert. Die Editor-Vorschau nennt beides.
- **Ohne Schalter** ändert sich nichts; bei „Kein Pfad“ mit Stadt-Gleisarten weisen Editor und
  MCP auf den Schalter hin.

### Betriebsstellensuche

- **Wortsuche:** Jedes Wort der Suche muss in Name oder `op_id` vorkommen. RINF füllt Namen mit
  Leerzeichen auf („Berlin Westkreuz␣␣␣…S-Bahn“), deshalb fand „Westkreuz S-Bahn“ vorher
  nichts. Exakte Treffer vergleichen mit zusammengezogenen Leerzeichen; auch ein Wegpunkt per
  exaktem Namen („Berlin-Schönholz S-Bahn“) wird so aufgelöst. Gilt für REST und MCP.
- **Netzfilter bleibt streng** (EK-2026-390): Berliner und Hamburger S-Bahnhöfe stehen nur als
  RINF-Betriebsstelle unter `rail` (der OSM-Import überspringt sie). Findet MCP
  `search_operational_points` mit `networks` nichts, nennt `hint` die Netze mit Treffern und
  `other_networks` die Treffer. Für das Routing ist das Netz des Wegpunkts egal, die
  Koordinate rastet am nächsten Gleis der gewählten Gleisart ein.
- **Gartenfeld** fehlt zu Recht: Die Siemensbahn ist seit 1980 stillgelegt, RINF kennt den Halt
  nicht, OSM führt keinen aktiven.

### Technik

- `services/routing_networks.py`: `normalize_networks` kennt `bridge_gaps`; `routing_request`
  setzt für nicht gewählte Gleisarten `BRIDGE_PRIORITY` (`"0.01"`) statt `"0"`, außer für
  `unknown`; `is_default_networks` ist mit Kombimodus falsch (→ `rail_flex`). `bridged_km` und
  `foreign_waypoints` (Wegpunkt ist fremd, wenn alle anliegenden Routensegmente einer nicht
  gewählten Gleisart angehören; aus GraphHoppers `snapped_waypoints`). `cache_networks` nimmt
  `bridge_gaps` nur in den Cache-Schlüssel, wenn es an ist (alte Schlüssel bleiben).
- `crud/operational_points.py`: Wortsuche und `collapse_spaces` (verschachteltes `replace`,
  läuft auf PostgreSQL und SQLite). MCP `search_operational_points` nutzt die CRUD-Funktion.
- GraphHopper: keine Änderung an Konfiguration, Custom Models oder Patch, also **kein
  Graph-Neubau**. Testnetz `test/planned-tracks.osm` um eine S-Bahn parallel zur Vollbahn
  (50,08) und eine S-Bahn mit Vollbahn-Lücke (50,09) erweitert; `smoke.sh` prüft: Kombimodus
  bleibt auf der parallelen S-Bahn, `light_rail` allein endet an der Lücke, Kombimodus
  überbrückt sie, Vollbahn mit Kombimodus überbrückt ein S-Bahn-Stück.
- Tests: `tests/unit/test_routing_networks.py` (Query-Statements, Vorgabeprofil, Cache-Schlüssel,
  `bridged_km`, `foreign_waypoints`), `tests/api/test_mcp_geometry.py` (Kombimodus, Hinweis bei
  „Kein Pfad“, Wortsuche, Hinweis bei leerem Netzfilter, Wegpunkt per aufgefülltem Namen).

### Entscheidungen (Jonas, 2026-11-23)

- **Kombimodus als eigener Schalter** (EK-2026-389, A), Faktor ×0,01, Ergebnis mit
  `bridged_km` und Warnung bei fremd eingerasteten Wegpunkten; EK-2026-355 bleibt der
  Grundfall. Verworfen: automatisch beim Scheitern (B); exklusiv bleiben und nur das
  Standardprofil reparieren (C); gemeinsame Gleise im Router als `light_rail` umdeuten (D).
- **Netzfilter der Betriebsstellensuche bleibt streng, leere Treffer bekommen einen Hinweis**
  (EK-2026-390, B). Verworfen: RINF-Punkte in den Filter `light_rail` einschließen (A);
  S-Bahnhöfe zusätzlich aus OSM importieren (C).

### Akzeptanzkriterien

- [x] Ohne Schalter: Query-Modell und Ergebnis wie bisher (Unit-Tests, Smoke-Test).
- [x] Mit Schalter: nicht gewählte Gleisarten ×0,01, `unknown` weiter ×0; Route bleibt auf
      paralleler S-Bahn und überbrückt eine Vollbahn-Lücke (Smoke-Test).
- [x] Ergebnis nennt `bridged_km` und `foreign_waypoints`; Editor-Vorschau zeigt beides.
- [x] „Westkreuz S-Bahn“ findet „Berlin Westkreuz␣␣␣S-Bahn“; leerer Netzfilter nennt Treffer
      in anderen Netzen.
- [x] Nach dem Deploy: 3224 und 3190 mit `light_rail` + `bridge_gaps` routbar (Abgleich unten;
      Ersetzen offen, EK-2026-400).

### Abgleich nach dem Deploy

Kein Graph-Neubau, keine Migration. Danach 3224 (op 525 Frohnau → op 644 Oranienburg S-Bahn)
und 3190 (op 707 Schönholz → op 4949 Hennigsdorf S-Bahn) mit `track_classes: ["light_rail"]`
und `bridge_gaps: true` ohne `apply` routen; `route.bridged_km` sollte nur die bekannten
Stücke enthalten (Birkenwerder, Kremmener Bahn), `foreign_waypoints` leer sein. Bei mindestens
85 % Deckung mit dem Bestand `mode: "replace"`, `apply: true`, danach
`compute_project_length(apply=true)`.

#### Ergebnis (2026-11-23)

- **3224:** 14,16 km, `bridged_km` 0,76 (nur Birkenwerder), `foreign_waypoints` leer; 80 % im
  Korridor, mittlere Abweichung 64 m, max. 342 m. Unter 85 %, weil der Bestand eine Skizze
  Frohnau – Hohen Neuendorf enthält → nicht ersetzt, EK-2026-400.
- **3190:** Schönholz – Hennigsdorf 15,22 km, `bridged_km` 4,91 (Kremmener Bahn), `foreign_waypoints`
  leer, 58 % im Korridor der Halte-Skizze. Das Projekt reicht bis Velten; in einem Zug entsteht eine
  Wende in Hennigsdorf, daher Hennigsdorf – Velten getrennt mit Vollbahn (6,17 km, 99 %). Mit
  Kombimodus rastet Hennigsdorf auf dem S-Bahn-Gleis ein (51 km, `foreign_waypoints: [0]`) – der
  Hinweis wirkt wie vorgesehen. Nicht ersetzt, EK-2026-400.
- Betriebsstellensuche: „Gesundbrunnen S-Bahn“ findet den aufgefüllten RINF-Namen; „Westkreuz“
  heißt in RINF „Berlin Westkreuz (Ringbahn)“ bzw. „(Stadtbahn)“, ohne „S-Bahn“.
