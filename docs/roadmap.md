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

### Verkehrsinvestitionsbericht (VIB) Import

Jährlicher Import des Bundestagsdrucksache-PDFs (Abschnitt B: Schienenwege). Vollständig implementiert: DB-Modelle, Mistral-OCR-Pipeline, Parser, KI-Inhaltsextraktion, Review-UI, API-Endpunkte, Import-UI und ProjectDetail-Anzeige.

Siehe: `docs/features/feature-vib-import.md`

**Phase 1 — Parser-Fixes (kein LLM):**
- [x] Per-Seite Spaltentyp-Erkennung (bimodal x0-Analyse statt festem COL_BOUNDARY)
- [x] TOC-verankerte Blockgrenzen (Sektionsnummer als Anker)
- [x] Debug-Script `scripts/dump_vib_parse_result.py`
- [x] `project_status` aus Planungsstand-Block extrahieren

**Phase 2 — LLM-Inhaltsextraktion:**
- [x] Celery-Task `extract_vib_blocks` + Endpoint
- [x] `VibStructurePreviewPage`: Strukturvorschau nach Parse → direkt "Weiter zum Review" (kein Batch-KI-Schritt mehr)
- [x] Nach Parse → Redirect zu Preview (statt direkt zu Review)
- [x] KI-Badge auf extrahierten Karten
- [x] **KI-Extraktion pro Vorhaben**: Im Review "KI extrahieren"-Button pro Eintrag (single-entry endpoint); ersetzt den früheren Batch-KI-Schritt. Begründung: Mistral OCR Qualität ist hoch genug, dass Batch-KI redundant ist; KI bleibt als optionales Werkzeug für einzelne Einträge verfügbar.

**Phase 3 — Review-UI:**
- [x] Sub-Block-Felder editierbar (Textareas)
- [x] PFA-Tabelle inline editierbar

**Phase 4 — Mistral OCR Pipeline:**
- [x] `tasks/vib_ocr.py`: Mistral OCR API integration (`mistral-ocr-latest`); pymupdf fallback when no API key
- [x] `_inline_tables()`: Resolves `[tbl-N.md](tbl-N.md)` placeholders in `page.markdown` with `page.tables[i].content` — ensures PFA tables and all other markdown tables are present in `raw_text`
- [x] `_page_to_text()`: Strips `page.header` / `page.footer` (API-separated fields) when `strip_headers_footers=True`; strips `![img-N.*](img-N.*)` image references via regex
- [x] `extract_pages_as_pdf()`: Extracts sub-PDF for a given page range (1-indexed, pymupdf); sent to Mistral OCR instead of full PDF
- [x] Import-UI: optional "von Seite / bis Seite" inputs (page range for OCR); "Kopf- und Fußzeilen ignorieren" checkbox (default on); PDF preview (iframe); timezone Europe/Berlin
- [x] Parser: `_VORHABEN_SECTION_RE` extended to match both plain `B.4.1.3` and markdown heading `# B.4.1.3` formats; `_RAW_TEXT_MAX_CHARS` raised to 30,000; "Termine" added to `_BLOCK_LABELS`; `_parse_pfa_table_markdown()` for pipe-table PFA parsing
- [x] `VibStructurePreviewPage`: richer raw text display — sub-section detection badges, char-count quality indicator, expandable rows with stats; removed false-positive alerts; raw text rendered as Markdown (`react-markdown` + `remark-gfm`) so pipe tables, headings, and bold text are displayed properly instead of as raw characters
- [x] `_collect_images()`: collects `{page_index, id, image_base64}` from `page.images` for all OCR pages; stored as JSON in `vib_draft_report.ocr_images_json`
- [x] API endpoints `GET /draft/{task_id}/images` (list metadata) and `GET /draft/{task_id}/image/{image_id}` (serve bytes) — base64-decoded, correct content-type for jpeg/png/webp

---

### Vervollständigung und Automatisierung Tests

**Status:** Implementiert (Steps 1–6 abgeschlossen)

#### Analyse Ist-Zustand

**Backend** (`apps/backend/tests/`)
- Abgedeckt: `route`, `project_groups`, `project_routes_api`, `users`, `tasks`, routing-Service, Route-Domain
- **Nicht abgedeckt (7 Endpoint-Module):**
  - `projects.py` — GET list/detail, POST, PATCH, changelog, revert (größte Lücke)
  - `auth.py` — Session-Login (POST /auth/session), Logout (DELETE), Cookie-Handling
  - `finves.py` — GET /finves/ Listenendpunkt
  - `haushalt_import.py` — POST /parse, GET /parse-result, POST /confirm, PATCH /unmatched
  - `project_texts.py` — CRUD Texte, Anhänge (Upload/Download/Delete), Dokument-Verknüpfungen
  - `settings.py` — GET/PATCH Settings
  - `operational_points.py` (geplant, Step 1 Routing) — noch nicht implementiert
- **Nicht abgedeckte Business-Logik:**
  - `tasks/haushalt.py` — Parser-Funktionen (`_parse_combined_id_cell`, `_extract_project_name`, `_extract_inline_titel_entries`, `_build_sv_raw_lookup`, Seitenumbruch-Recovery)
  - `tasks/finve_matching.py` — Fuzzy-Matching-Logik
  - `tasks/vib.py` + `tasks/vib_matching.py` — VIB-Parser und Matching
  - `utils/file_storage.py` — Path-Traversal-Guard, MIME-Validierung

**Frontend** (`apps/frontend/src/`)
- Konfiguriert: Vitest + jsdom (vite.config.ts), `pnpm test` funktioniert — aber **0 eigene Tests vorhanden**
- Testbare Einheiten:
  - `features/projects/projectFeatureConfig.ts` — pure Data-Konfiguration (featureGroups, trainCategoryLabels)
  - `lib/auth.ts` — AuthProvider, useAuth-Hook (mit @testing-library/react)
  - `shared/api/queries.ts` — Query-Hooks (mit msw + React Query)
  - Utility-Funktionen falls vorhanden

#### Plan

**Schritt 1 — Backend: Konftest erweitern**
- [x] `tests/api/conftest.py` um weitere Tabellen ergänzen: `AppSettings`, `ProjectTextType`, `ProjectText`

**Schritt 2 — Backend: fehlende API-Tests**
- [x] `tests/api/test_projects.py` — GET /projects/, GET /projects/{id}, PATCH (editor), PATCH unauth (401/403), changelog GET, revert POST
- [x] `tests/api/test_auth.py` — POST /auth/session success/fail, DELETE /auth/session, Cookie wird gesetzt
- [x] `tests/api/test_finves.py` — GET /finves/ gibt Liste zurück (monkeypatch CRUD)
- [x] `tests/api/test_project_texts.py` — CRUD Texte, Visibility-Prüfung (öffentlich vs. auth-only), Delete
- [x] `tests/api/test_settings.py` — GET/PATCH Settings, Rolle-Guard, Roundtrip

**Schritt 3 — Backend: Parser-Unit-Tests**
- [x] `tests/unit/test_finve_matching.py` — `_normalize`, `_score`, `suggest_projects_for_finve`, `suggest_per_erlaeuterung_project`, `suggest_projects_for_sv_erlaeuterung`
- [x] `tests/unit/test_file_storage.py` — Path-Traversal-Guard, erlaubte MIME-Types, `delete_attachment_file` silent on missing
- [ ] `tests/unit/test_haushalt_parser.py` — Fixtures aus realen PDF-Zeilen (als String), Tests für `_parse_combined_id_cell`, `_extract_project_name`, etc. *(aufwändig, späteres Ticket)*

**Schritt 4 — Frontend: Basis-Setup + erste Tests**
- [x] `@testing-library/react`, `@testing-library/user-event`, `jsdom` als Dev-Dependencies hinzugefügt
- [x] `src/features/projects/projectFeatureConfig.test.ts` — featureGroups enthält alle erwarteten Keys, keine Duplikate, trainCategoryLabels korrekt
- [x] `src/lib/auth.test.tsx` — useAuth Login/Logout-Flow mit gemocktem fetch (17 Tests)

**Schritt 5 — Automatisierung (CI)**
- [ ] Backend-Tests in CI: `pytest apps/backend/tests/` als GitHub-Actions-Step
- [ ] Frontend-Tests in CI: `pnpm test` in `apps/frontend/`
- [ ] Coverage-Report generieren (`pytest --cov`, `vitest --coverage`) und als Artefakt speichern

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

- [ ] **Vervollständigung und Automatisierung Tests**
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
- [x] **Hooks**: Pre-edit guard `.env`, post-edit reminders für `make gen-api`, Alembic-Migration und roadmap sync, macOS-Notification bei Bedarf
- [x] **Skills**: `/commit` (Conventional Commit helper), `/gen-api`, `/update-roadmap`, `/new-api-route` (Route-Scaffold-Wizard)
- [x] **Plugins**: `feature-dev`, `frontend-design`, `pyright-lsp` (Python Code Intelligence), `typescript-lsp`

### UI / UX
- [x] **BVWP-Bewertung in Projektdetail** — `GET /api/v1/projects/{id}/bvwp` endpoint; `BvwpProjectDataSchema` (Pydantic) + `get_bvwp_data` CRUD; `BvwpDataSection.tsx` in `ProjectDetail` with 11 tab groups (Grunddaten, Kosten, Prognose PV/GV, Nutzen PV/GV, Weitere Nutzenwirkungen, Umwelt, Raumordnung, Kapazität, Sonstiges); NKV shown as badge; tabs hidden when all fields are null; section hidden for projects without BVWP data
- [x] Project search on map and list view — client-side substring filter by name / project number / description; search input in `MapControls` overlay (map) and list header; `?search=` URL param with 200 ms debounce; result count, clear button, and empty-state messages
- [x] Admin-configurable ProjectGroup visibility (`is_visible`) and default selection (`is_default_selected`) on map; group filter drawer redesigned as clickable button list
- [x] Admin-configurable map group mode (`AppSettings.map_group_mode`: `preconfigured` / `all`) in `/admin/project-groups`
- [x] Zoom initial map view on project detail page reduced (zoom 7 → 6)
- [x] Login via Enter-Taste (nicht nur Button-Klick) — `LoginModal.tsx`: `PasswordInput.onKeyDown` → `doLogin()`
- [x] Inhaltsverzeichnis in Projektdarstellung (links, ausklappbar; klappt Abschnitte beim Anklicken auf)
- [x] Header-Menü kollabiert zu Burger-Menü bei schmalen Fenstern (Kollaps-Schwellwert angepasst)
- [x] Projektkarte zentriert beim Laden auf den Projektmittelpunkt (Koordinate in `project`-Tabelle)
- [x] Karte/Liste als Tab-Toggle auf Route `/` (`?view=map` / `?view=list`); `/projects` → Redirect
- [x] Gruppen-Persistenz als URL-Param (`?group=id1,id2`) zwischen Karte und Liste
- [x] Toggle „Nur übergeordnete Projekte" (filtert auf `superior_project_id IS NULL`)
- [x] Kartenauswahl zeigt Projektnummer + Beschreibung (nicht nur Name)
- [x] Liniendicke (4 px Standard) und Punktgröße auf Karte einstellbar
- [x] Lücken zwischen Liniensegmenten behoben (MultiLineString + `line-cap: round`)
- [x] Punkte aus GeoJSON auf Karte (separater Circle-Layer)
- [x] Projektdetails + Beschreibung neben Karte (Karte rechts, 2/3 Breite bei ausreichend Platz)
- [x] Projekteigenschaften (inkl. Verkehrsarten, Merkmale) in Box „Projektdetails"; alte ID entfernt
- [x] Kurzansicht-Komponente für Projekte auf Karte und in Projektdetail (Unter-/Oberprojekte)
- [x] Datum-/Zeitanzeige durchgehend auf Zeitzone Europe/Berlin umgestellt (Changelog, Import, Nutzerverwaltung)
- [x] Nach Bestätigung des Haushalt-Reviews automatische Weiterleitung zur Import-Übersicht
- [x] SV-FinVes in Projektdetailseite als kompakter Tag dargestellt (kein Diagramm)

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

Jährlicher Import der Anlage VWIB, Teil B (Bundeshaushalt) als PDF.
Die Tabelle enthält alle Bedarfsplanmaßnahmen des Schienenwegeinvestitionsprogramms
mit FinVe-Nummern, Kostenschätzungen und Jahresansätzen je Haushaltskonto.

**PDF-Spalten-Mapping** (Werte in €1.000, außer %):

| Spalte | Header | Ziel-Feld |
|--------|--------|-----------|
| 1 | Lfd. Nr. | `Budget.lfd_nr` (z.B. "B0080") |
| 2 | Nr. FinVe | `Finve.id` (Integer, Matching-Schlüssel) |
| 3 | Nr. Bedarfsplan Schiene | `Budget.bedarfsplan_number` |
| 4 | Bezeichnung der Investitionsmaßnahme | `Finve.name` |
| 5 | Aufnahme Jahr | `Finve.starting_year` |
| 6 | Gesamtausgaben ursprünglich | `Budget.cost_estimate_original` |
| 7 | Gesamtausgaben Vorjahr | `Budget.cost_estimate_last_year` |
| 8 | Gesamtausgaben aktuell | `Budget.cost_estimate_actual` |
| 9 | Δ zum Vorjahr (€1.000) | `Budget.delta_previous_year` |
| 10 | Δ zum Vorjahr (%) | `Budget.delta_previous_year_relativ` |
| 11 | Gründe | `Budget.delta_previous_year_reasons` |
| 12 | Verausgabt bis Y-2 | `Budget.spent_two_years_previous` |
| 13 | Bewilligt Y-1 | `Budget.allowed_previous_year` |
| 14 | Übertragene Ausgabereste | `Budget.spending_residues` |
| 15 | Veranschlagt Y | `Budget.year_planned` |
| 16 | Vorhalten Y+1 ff. | `Budget.next_years` |

Titelunterzeilen (Spalten 7, 8, 12–16) → `BudgetTitelEntry` verknüpft mit `HaushaltTitel`.
Nachrichtlich-Zeilen (kursiv) werden ebenfalls als `is_nachrichtlich=True` gespeichert.

**Haushaltstitel im PDF 2026** (Lookup-Tabelle `haushalt_titel`, auto-erweiterbar):
- `891_01` → Kap. 1202, Titel 891 01
- `891_03` → Kap. 1202, Titel 891 03
- `891_04` → Kap. 1202, Titel 891 04
- `891_52` → Kap. 1408, Titel 891 52
- `891_91` → Kap. 1202 (alt), Titel 891 91 – IIP Schiene
- `891_11` → Kap. 1202 (alt), Titel 891 11 – LUFV (alt)

Neue Titel in künftigen PDFs werden automatisch per `get_or_create` registriert.

- [x] DB-Modelle: `HaushaltTitel`, `BudgetTitelEntry`, `HaushaltsParseResult`, `FinveChangeLog`, `BudgetChangeLog`, `UnmatchedBudgetRow` + Alembic-Migration
- [x] Pydantic-Schemas (`haushalt_import.py`), CRUD-Funktionen (`crud/haushalt_import.py`)
- [x] Celery-Task `parse_haushalt_pdf` (`tasks/haushalt.py`) mit `pdfplumber`; Parser-Fixes für 2026-Format (zusammengeführte Spalten, mehrzeilige Zellen, `_KAP_TITEL_RE` mit `(alt)`-Zusatz, `_BHO_NOTE_RE`)
- [x] API unter `/api/v1/import/haushalt`: `POST /parse`, `GET /parse-result`, `POST /confirm`, `GET/PATCH /unmatched`
- [x] Frontend `features/haushalt-import/`: Upload-Flow mit Celery-Polling, Review-Tabelle (neu/geändert/unmatched), Projektzuordnung per MultiSelect, Unmatched-Nachbearbeitung
- [x] Fuzzy-Matching (`tasks/finve_matching.py`, SequenceMatcher + Token-Overlap, Threshold 0.45) für automatische Projektzuordnungs-Vorschläge
- [x] FinVe → mehrere Projekte (bidirektionale Sync beim Confirm; MultiSelect auch bei update-Rows)
- [x] FinVe-Anzeige in `ProjectDetail`: `GET /api/v1/projects/{id}/finves`, `FinveSection.tsx` mit 3 Tabs (Budgetverteilung BarChart, Kostenentwicklung LineChart, Detailtabelle); `@mantine/charts` + `recharts`
- [x] **Sammelfinanzierungsvereinbarungen (SV-FinVes)**: Erkennung via Regex im Parser, `is_sammel_finve`-Flag in DB (`finve`-Tabelle) + Alembic-Migration, eigene Review-Sektion "Sammel-FinVes (Phase 2)" in der UI, per-Projekt-Unterzeilen mit Fuzzy-Vorschlägen aus dem Erläuterungstext, Erkennung mehrseitiger Erläuterungen (flat-table-Ansatz + Continuation-Detection), Wiederherstellung von Zeilen mit fehlendem YYY-Identifier via Raw-Text-Lookup. `finve_to_project` um `haushalt_year`-Spalte erweitert: reguläre FinVes nutzen `NULL` (permanente Zuordnung), SV-FinVes speichern Mitgliedschaft pro Jahr → historische Projektzu-/abgänge bleiben erhalten.
- [x] **FinVe-Übersicht** (`/finves`): Neue Seite mit Kartenansicht aller Finanzierungsvereinbarungen, Volltextsuche, Typ-Filter (Alle / Regulär / Sammel-FinVes). Jede Karte zeigt Kenndaten, verknüpfte Projekte als anklickbare Mini-Cards (Link → Projektdetailseite) sowie ausklappbare Budget-Diagramme (Stacked BarChart, LineChart, Detailtabelle) analog zu `FinveSection.tsx`. Backend: `GET /api/v1/finves` (auth required) + CRUD mit Eager-Load Budgets + Titel.
- [x] **Import-Anleitung** (`/admin/haushalt-import/guide`): Schritt-für-Schritt-Dokumentation für Endnutzer; verlinkt von Import- und Review-Seite.

### Infrastruktur
- [x] Docker: Dev (nur DB + Redis), Prod (DB + Backend + Frontend/nginx + Worker); Entrypoint-Skript mit Alembic-Migration, Makefile-Targets
- [x] Celery Task Queue mit Redis-Broker; Task-Status-Endpoint `GET /api/v1/tasks/{task_id}`
- [x] Backup & Restore: `scripts/backup_db.sh`, `scripts/restore_db.sh`, Makefile-Targets; Doku in `docs/production_setup.md`
- [x] Backend-Authentifizierung: httpOnly-Cookie-Session (HMAC-signed token); Rollen viewer/editor/admin
- [x] Routing-Algorithmus implementiert (pgRouting / GrassHopper-Microservice)
- [x] Docs bereinigt: `docs/architecture.md` als zentrale Architekturdokumentation
- [x] Comprehensive test coverage: backend API tests, parser unit tests, frontend component tests
