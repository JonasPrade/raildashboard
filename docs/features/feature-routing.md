# Feature: Routenvorschlag per GrassHopper

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

## Voraussetzungen

Backend-Infrastruktur ist vollständig implementiert (GraphHopper HTTP client, `RouteService`, Endpoints, ORM model, CRUD, caching, Tests). Docker-Service ist konfiguriert. **Human task**: OSM-PBF-Datei unter `data/graphhopper/map.osm.pbf` ablegen.

## Verhalten

- Nur für `editor` / `admin` sichtbar
- Fehlerfall 502 → "Routing-Dienst nicht erreichbar"
- Fehlerfall 422 → "Kein Pfad gefunden"
- Accept: schreibt Route in DB und aktualisiert `geojson_representation` des Projekts
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
