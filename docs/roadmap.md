# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.

---

## Short-Term Features

- [ ] make the "Schienenprojekte-Dashboard" clickable -> return to Start Page
- [ ] Show Button Haushalt in menu for all - not only logged in users
- [ ] integrate the new design described in `docs/DESIGN.md`

This tasks must be done by human:
- [ ] Import of the Haushalt Berichte 2020 - 2025
- [ ] Update time slots Hochleistungskorridore

---

## Mid-Term Features

### Vervollständigung und Automatisierung Tests

**Status:** API- und Unit-Tests implementiert (Steps 1–4 abgeschlossen). CI-Automatisierung offen.

- [x] Backend conftest erweitert (`AppSettings`, `ProjectTextType`, `ProjectText`)
- [x] API-Tests: `test_projects.py`, `test_auth.py`, `test_finves.py`, `test_project_texts.py`, `test_settings.py`
- [x] Unit-Tests: `test_finve_matching.py` (Fuzzy-Matching), `test_file_storage.py` (Path-Traversal, MIME)
- [x] Frontend: `@testing-library/react` Setup + Tests für `projectFeatureConfig` und `useAuth` (17 Tests)
- [ ] `tests/unit/test_haushalt_parser.py` — Parser-Fixture-Tests *(aufwändig, späteres Ticket)*
- [ ] CI: `pytest` + `pnpm test` als GitHub-Actions-Steps mit Coverage-Report

- [ ] **Special view of Generalsanierung. Timeline when which Generalsanierung is started and when it is finished**

---

### Routenvorschlag per GrassHopper *(Backend + Frontend)*

Backend-Infrastruktur vollständig implementiert (GraphHopper HTTP client, RouteService, Endpoints, ORM, CRUD, Tests, Docker). Offen: Frontend-Workflow + OperationalPoints-Endpoint.

**Prerequisite (human task):** OSM-PBF unter `data/graphhopper/map.osm.pbf` ablegen.

Siehe: `docs/features/feature-routing.md`

#### ✅ Done — Docker infrastructure
- `docker/graphhopper/config.yml` — GraphHopper config with `rail_default` profile
- `docker-compose.yml` (prod) — `graphhopper` service added; starts automatically with the stack
- `docker-compose.dev.yml` — `graphhopper` service added behind `--profile routing` (opt-in)
- `.env.example` — `ROUTING_BASE_URL=http://graphhopper:8989` (was broken `localhost`)
- `docs/production_setup.md` — GraphHopper setup section (PBF placement, first start, cache invalidation)

#### Step 1 — Expose OperationalPoints as a searchable API endpoint *(Backend)*
- Add `GET /api/v1/operational-points?q=<name_or_id>&limit=20` in a new file `api/v1/endpoints/operational_points.py`
- Pydantic response schema: `OperationalPointRef { id, op_id, name, type, latitude, longitude }`
- CRUD function `search_operational_points(db, query, limit)` — `ILIKE` filter on `name` and `op_id`
- Register router in `api/v1/router.py` (public, no auth required)
- Run `make gen-api` to sync the frontend client

#### Step 2 — Route calculation dialog *(Frontend)*
New component `RouteCalculatorModal.tsx` inside `features/routing/`:
- Visible in `ProjectDetail` only for `editor` / `admin` roles; triggered by a button "Route berechnen"
- Two `Combobox` / `Select` inputs (searchable via the new endpoint) for start and end OperationalPoint
- "Berechnen"-button → `POST /api/v1/routes/calculate` with `{ waypoints: [{lat, lon}, {lat, lon}], profile: "rail_default", options: {} }`
- Loading state, error handling (502 → "Routing-Dienst nicht erreichbar", 422 → "Kein Pfad gefunden")
- On success: store the returned `RoutePreviewOut` GeoJSON Feature in local state

#### Step 3 — Route preview on map *(Frontend)*
- In `ProjectDetail` (or a dedicated `RoutePreviewMap`), add a temporary MapLibre `LineLayer` sourced from the preview GeoJSON
- Style: dashed blue line, distinct from the solid project geometry
- Show distance (km) and duration (min) from `properties.distance_m` / `properties.duration_ms`

#### Step 4 — Accept / Reject flow *(Frontend)*
- **Accept** → `POST /api/v1/projects/{id}/routes` with `{ feature: <RoutePreviewOut> }` → invalidate `projectRoutesQuery`; additionally `PATCH /api/v1/projects/{id}` to update `geojson_representation` so the route appears on the main map
- **Reject** → clear preview state; no API call
- After accept: show success notification, close modal, map re-renders with persisted route

#### Step 5 — Saved routes list *(Frontend)*
- Small section in `ProjectDetail` (editor/admin only) listing saved routes via `GET /api/v1/projects/{id}/routes`
- Each row: date, distance, duration, "Als aktive Geometrie setzen"-button (PATCH geojson_representation) and "Ersetzen"-button (PUT replace)
- Mutation hooks: `useConfirmRoute`, `useReplaceRoute`, `useSetProjectGeometry`

#### Step 6 — Frontend query hooks *(Frontend)*
Add to `queries.ts`:
- `useOperationalPointSearch(query)` — debounced, enabled when `query.length >= 2`
- `useCalculateRoute()` — mutation
- `useConfirmRoute(projectId)` — mutation
- `useReplaceRoute(projectId)` — mutation

---

### Admin: Offene Zuordnungen (BudgetFinVe & VIB)

- [ ] In der Admin-Übersicht anzeigen, welche importierten Datensätze noch kein Projekt zugeordnet haben:
  - **Haushalt / BudgetFinVe**: FinVes ohne verknüpftes Projekt (aus `finve_to_project`-Tabelle)
  - **VIB-Einträge**: bestätigte VIB-Einträge (`vib_entry`) ohne `project_id`
  - Darstellung als kompakte Warnsektionen auf einer Admin-Seite (z.B. `/admin/unassigned`) oder eingebettet in die jeweilige Import-Übersicht; direkter Link zum Bearbeiten des Eintrags

### Sonstiges

- [ ] **ProjectProgress** *(Backend + Frontend)*
  Fortschrittsstand eines Projekts (Planungs-, Genehmigungs-, Bauphase) aus mehreren Quellen (VIB, manuell, Pressemitteilungen).
  Siehe: `docs/features/feature-project-progress.md`

- [ ] **BVWP-Datenimport** — Übernahme der BVWP-Daten aus der Legacy-Datenbank. Voraussetzung für die Anzeige der BVWP-Bewertung (Display-Feature bereits implementiert).

- [ ] Cleanup Database structure. Evaluate
- [ ] Bug-Report: A Button in the right corner where everybody can report Bugs or Problems (logged in users dont have to add there contact information). Bugs should be collect in fitting tool and solved by ai
- [ ] Kennzahlen Marktuntersuchungsbericht Bundesnetzagentur -> wichtigsten Entwicklungskennzahlen online stellen
- [ ] Integration API Bauinfoportal zu Dashboard
- [ ] In the FinVe calculation show if the cost development is inside the normal price inflation
- [ ] Integrate a feed for newsletter und updates from websites to roadmap.md
---

## Long-Term Features

- [ ] **VIB-Review: Original-PDF-Anzeige** — Im Review-Schritt das hochgeladene PDF parallel zum Formular anzeigen, auf die passende Seite gesprungen. Erfordert: PDF-Speicherung serverseitig (z.B. temporär an draft_id geknüpft), Seitennummer-Tracking im Parser (pro Eintrag), Serve-Endpoint `GET /import/vib/pdf/{task_id}`, Frontend-Integration mit `react-pdf` oder ähnlichem.

- [ ] **VIB-Review: OCR-Bilder anzeigen** — Im Review und in `VibStructurePreviewPage` extrahierte Mistral-OCR-Bilder (Diagramme, Karten, Fortschrittsbalken) pro Vorhaben anzeigen. Backend-Infrastruktur bereits implementiert: `ocr_images_json` auf `VibDraftReport`, `GET /draft/{task_id}/images` (Metadaten) und `GET /draft/{task_id}/image/{id}` (Bytes). Offen: pro-Eintrag-Zuordnung der Bilder (page_index-Matching gegen entry block_start/end-Seiten) und Frontend-Komponente (Galerie oder Inline-Thumbnails in der Strukturvorschau).

- [ ] **Netzzustandsbericht** — PDF-Import, Extraktion relevanter Kennzahlen in die Datenbank

- [ ] **Beschleunigungskommission Schiene** — Datentransfer aus öffentlichen Quellen + automatische Updates

- [ ] **RINF-Daten evaluieren** — Für Bahnhofs-/Stationsverbindungen ggf. weiterhin benötigt

- [ ] **GeoLine-Erstellung** — Möglichkeit, neue Streckengeometrien zu erzeugen, wenn vorhandene unvollständig/ungültig sind. Ansatz noch offen (Zeichentool auf Karte vs. automatische Vervollständigung).

- [ ] **Automatisierung Preisniveau** — Tool zum Berechnen von Preisen gemäß Inflation/Baukostenentwicklung auf das aktuelle Jahr

- [ ] **Passwort zurücksetzen per E-Mail** *(Backend + Frontend)*
  Reset-Link per E-Mail, Token-basiert (UUID4, 1h gültig). Admin hinterlegt E-Mail in Benutzerverwaltung.
  Siehe: `docs/features/feature-password-reset.md`

---

## Database Transfer

Bestehende Daten aus der alten Datenbank können per CSV-Export + Importscript übernommen werden.

Siehe `apps/backend/docs/Transfer DB for Project.md` und `apps/backend/docs/Connection between DB Open Data and ERA Rinf.md`.

Priorität:
- **project data** — primäres Transferziel _finished_ 
- **finve and budgets** — aus Originalquellen neu aufbauen
- **bks** — niedrige Priorität
- **infrastructure data** — wird nicht übertragen
- **d-takt data** — ignoriert
- **texts** — kein Transfer

---

## Finished

### Claude Code Setup
- [x] Hooks (pre-edit `.env` guard, post-edit reminders for `make gen-api`, Alembic, roadmap sync, macOS notifications)
- [x] Skills: `/commit`, `/gen-api`, `/update-roadmap`, `/new-api-route`
- [x] Plugins: `feature-dev`, `frontend-design`, `pyright-lsp`, `typescript-lsp`

### Verkehrsinvestitionsbericht (VIB) Import

Jährlicher Import des VIB-PDFs (Abschnitt B: Schienenwege). Vollständig implementiert über Phases 1–4.

Siehe: `docs/features/feature-vib-import.md`

- [x] **Parser** — per-page column detection (bimodal x0), TOC-anchored block boundaries, `_VORHABEN_SECTION_RE` for plain and Markdown headings, PFA pipe-table parsing, debug script `scripts/dump_vib_parse_result.py`
- [x] **Mistral OCR Pipeline** — `tasks/vib_ocr.py`: `mistral-ocr-latest` API + pymupdf fallback; inline table resolution; header/footer stripping; page-range extraction; image collection stored as JSON in `vib_draft_report.ocr_images_json`
- [x] **API** — Celery task `extract_vib_blocks`; image endpoints `GET /draft/{task_id}/images` + `/image/{id}`; single-entry AI extraction endpoint
- [x] **Review-UI** — `VibStructurePreviewPage` with Markdown rendering, quality indicators, sub-section badges; `VibReviewPage` with editable sub-block fields and inline PFA table; per-entry "KI extrahieren" button; m:n project assignment (`project_ids`)

### UI / UX
- [x] **Chronicle design system rollout** — Noto Serif font (self-hosted), design tokens CSS, 4 components (ChronicleHeadline, ChronicleDataChip, ChronicleCard, ChronicleButton); showcase pages: Projects page + MapControls glassmorphic panel. See `docs/features/feature-design-system.md`
- [x] **BVWP-Bewertung in Projektdetail** — `GET /api/v1/projects/{id}/bvwp`; `BvwpDataSection.tsx` mit 11 Tab-Gruppen; NKV als Badge; Sektion ausgeblendet wenn kein BVWP-Datensatz vorhanden
- [x] Projektsuche auf Karte und Listenansicht — client-seitiger Filter nach Name/Nummer/Beschreibung; `?search=` URL-Param mit Debounce
- [x] Admin-konfigurierbare ProjectGroup-Sichtbarkeit (`is_visible`, `is_default_selected`) und Kartenmodus (`map_group_mode`: `preconfigured` / `all`)
- [x] Inhaltsverzeichnis in Projektdarstellung (links, ausklappbar)
- [x] Karte/Liste als Tab-Toggle auf `/` (`?view=map` / `?view=list`); Gruppen-Persistenz als `?group=`-Param
- [x] Toggle „Nur übergeordnete Projekte"; Kartenauswahl zeigt Projektnummer + Beschreibung
- [x] Kartengeometrie: einstellbare Liniendicke/Punktgröße, `line-cap: round` für Lückenbehebung, separater Circle-Layer für GeoJSON-Punkte
- [x] Projektdetail: Projekteigenschaften-Box, Kurzansicht-Komponente für Unter-/Oberprojekte, Zentrierung auf Projektmittelpunkt
- [x] Datum-/Zeitanzeige auf Zeitzone Europe/Berlin; Login per Enter-Taste; Burger-Menü bei schmalen Fenstern
- [x] SV-FinVes in Projektdetailseite als kompakter Tag dargestellt

### Texte & Kommentare
- [x] Projekttexte anzeigen (über übergeordnetes Projekt), erstellen, bearbeiten
- [x] Sichtbarkeit von Texten: eingeloggt-only oder öffentlich
- [x] Versionshistorie und Bearbeitungsformular nur für eingeloggte Nutzer sichtbar
- [x] **Dateianhänge an Projekttexten** — Upload, Download, Delete; PDF-Inline-Preview; MIME-Validierung; Path-Traversal-Guard

### Change Tracking (vollständig)
- [x] DB-Modelle `change_log` + `change_log_entry` + Alembic-Migration
- [x] `PATCH /api/v1/projects/{id}` — schreibt ChangeLog-Einträge je geändertem Feld (Rolle: editor/admin)
- [x] `GET /api/v1/projects/{id}/changelog` — öffentlich lesbar
- [x] Bearbeitungsformular in `ProjectDetail` (editor/admin); alle Felder bearbeitbar
- [x] Versionshistorie-Timeline in `ProjectDetail` (`ProjectHistorySection.tsx`); nur für eingeloggte Nutzer
- [x] „Zurücksetzen"-Button pro `ChangeLogEntry` (editor/admin) via `useRevertProjectField` hook

### Benutzerverwaltung
- [x] Login-UI: httpOnly-Cookie-Session (HMAC-signed), Authorization-Header bei API-Requests, 401/403-Interceptor
- [x] Rollenbasierte Bearbeitung: Schreiboperationen nur für editor/admin sichtbar
- [x] User-Management-Seite `/admin/users` (nur admin): Nutzer anlegen, Rolle/Passwort ändern, löschen

### Haushaltsberichte-Import (vollständig)

Jährlicher Import der Anlage VWIB, Teil B (Bundeshaushalt) als PDF. Enthält alle Bedarfsplanmaßnahmen des Schienenwegeinvestitionsprogramms mit FinVe-Nummern, Kostenschätzungen und Jahresansätzen.

Siehe: `docs/features/feature-haushalt-import.md`

- [x] Celery-Task `parse_haushalt_pdf` (`tasks/haushalt.py`) mit `pdfplumber`; Parser für 2026-Format (zusammengeführte Spalten, mehrzeilige Zellen, Haushaltstitel-Lookup auto-erweiterbar via `get_or_create`)
- [x] DB-Modelle: `HaushaltTitel`, `BudgetTitelEntry`, `HaushaltsParseResult`, `FinveChangeLog`, `BudgetChangeLog`, `UnmatchedBudgetRow`
- [x] API: `POST /parse`, `GET /parse-result`, `POST /confirm`, `GET/PATCH /unmatched`
- [x] Frontend: Upload-Flow mit Celery-Polling, Review-Tabelle (neu/geändert/unmatched), Projektzuordnung per MultiSelect, Import-Anleitung unter `/admin/haushalt-import/guide`
- [x] Fuzzy-Matching (`tasks/finve_matching.py`, SequenceMatcher + Token-Overlap, Threshold 0.45); FinVe → mehrere Projekte (bidirektionale Sync beim Confirm)
- [x] **SV-FinVes**: Erkennung via Regex, `is_sammel_finve`-Flag, flat-table-Ansatz für Seitenumbruch-Recovery, eigene Review-Sektion mit per-Projekt-Unterzeilen + Fuzzy-Vorschlägen; `finve_to_project.haushalt_year` für Jahrestracking
- [x] **FinVe-Übersicht** (`/finves`): Kartenansicht aller FinVes, Suche, Typ-Filter, ausklappbare Budget-Diagramme (BarChart/LineChart/Detailtabelle), verknüpfte Projekt-Mini-Cards

### Tests (Phases 1–4)
- [x] Backend API-Tests: `test_projects`, `test_auth`, `test_finves`, `test_project_texts`, `test_settings`; conftest mit `AppSettings`, `ProjectTextType`, `ProjectText`
- [x] Backend Unit-Tests: `test_finve_matching` (Fuzzy-Matching), `test_file_storage` (Path-Traversal, MIME)
- [x] Frontend: `@testing-library/react` Setup + `projectFeatureConfig.test.ts` + `auth.test.tsx` (17 Tests)

### Infrastruktur
- [x] Docker: Dev (DB + Redis), Prod (DB + Backend + Frontend/nginx + Worker); Entrypoint mit Alembic-Migration
- [x] Celery Task Queue mit Redis-Broker; Task-Status-Endpoint `GET /api/v1/tasks/{task_id}`
- [x] Backup & Restore: `scripts/backup_db.sh` / `restore_db.sh`; Doku in `docs/production_setup.md`
- [x] Backend-Auth: httpOnly-Cookie-Session (HMAC-signed); Rollen viewer/editor/admin
- [x] Routing-Microservice (GraphHopper/pgRouting) Docker-Integration
- [x] `docs/architecture.md` als zentrale Architekturdokumentation
