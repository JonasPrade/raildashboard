# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.

---

## Short-Term Features

- [x] integrate the new design described in `docs/DESIGN.md`

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

### ✅ Routenvorschlag per GrassHopper *(Backend + Frontend)*

Vollständig implementiert. Backend-Infrastruktur (GraphHopper HTTP client, RouteService, Endpoints, ORM, CRUD, Tests, Docker) und Frontend-Workflow ("Geometrie verwalten" Modal in ProjectDetail) sind abgeschlossen.

**Prerequisite (human task):** OSM-PBF unter `data/graphhopper/map.osm.pbf` ablegen.

#### Open Routing Tasks
- [ ] **Add stations to GeoJSON** — When a route is confirmed, add the start/via/end stations as GeoJSON Point features to the geometry, consistent with how other points are already stored.
- [ ] **Selective GeoJSON object removal** — In the geometry management UI, let the user select individual GeoJSON features (e.g. segments or points) and remove only those, instead of deleting the entire geometry.
- [x] **Parent GeoJSON auto-merge** — When a sub-project's `geojson_representation` changes, automatically recompute all ancestor projects' geometry as a FeatureCollection of their children's features (arbitrary depth, synchronous, no migration needed). See: `docs/features/feature-parent-geojson-merge.md`

Siehe: `docs/features/feature-routing.md`

#### ✅ Done — Docker infrastructure
- `docker/graphhopper/config.yml` — GraphHopper config with `rail_default` profile
- `docker-compose.yml` (prod) — `graphhopper` service added; starts automatically with the stack
- `docker-compose.dev.yml` — `graphhopper` service added behind `--profile routing` (opt-in)
- `.env.example` — `ROUTING_BASE_URL=http://graphhopper:8989` (was broken `localhost`)
- `docs/production_setup.md` — GraphHopper setup section (PBF placement, first start, cache invalidation)

#### ✅ Done — Frontend routing UI (Steps 1–6)
- `GET /api/v1/operational-points?q=&limit=20` — `OperationalPointRef` schema, CRUD, endpoint registered
- `features/routing/GeometryManagementModal.tsx` — full-screen modal ("Geometrie verwalten" button in ProjectDetail, editor/admin only)
- `features/routing/RouteCalculatorForm.tsx` — start / via (dynamic) / end station comboboxes with debounced search
- `features/routing/GeometryPreviewMap.tsx` — MapLibre map: solid blue (existing) + dashed orange (preview); auto-fits bounds
- Accept flow: confirm route in DB (`POST /projects/{id}/routes`) + PATCH `geojson_representation`; delete = PATCH with null; upload = PATCH with uploaded GeoJSON
- Query hooks in `queries.ts`: `useOperationalPointSearch`, `useCalculateRoute`, `useConfirmRoute`, `useUpdateProjectGeometry`

---

### Admin: Offene Zuordnungen (BudgetFinVe & VIB)

- [x] In der Admin-Übersicht anzeigen, welche importierten Datensätze noch kein Projekt zugeordnet haben:
  - **Haushalt / BudgetFinVe**: FinVes ohne verknüpftes Projekt (aus `finve_to_project`-Tabelle)
  - **VIB-Einträge**: bestätigte VIB-Einträge (`vib_entry`) ohne `project_id`
  - Seite `/admin/unassigned` mit zwei Sektionen (FinVe + VIB); Inline-Zuweisung per durchsuchbarem MultiSelect direkt in der Tabellenzeile
  - Header-Badge zeigt Gesamtzahl offener Zuordnungen für editor/admin

- [ ] **Neues Projekt aus Zuordnungsseite anlegen** — Auf `/admin/unassigned` einen "Neues Projekt anlegen"-Button bereitstellen, damit unzugeordnete FinVes/VIB-Einträge direkt einem neu angelegten Projekt zugeordnet werden können, ohne die Seite wechseln zu müssen.

### Neues Projekt anlegen *(Backend + Frontend)*

- [ ] 5-step wizard at `/admin/projects/new`: Stammdaten → Geometrie → Projekteigenschaften → FinVes → VIB. Only step 1 is required; steps 2–5 are skippable. Requires `POST /api/v1/projects` (missing) and `ProjectEditFields` extraction from `ProjectEdit.tsx`.

Siehe: `docs/features/feature-new-project-wizard.md`

### Sonstiges

- [ ] **ProjectProgress** *(Backend + Frontend)*
  Fortschrittsstand eines Projekts (Planungs-, Genehmigungs-, Bauphase) aus mehreren Quellen (VIB, manuell, Pressemitteilungen).
  Siehe: `docs/features/feature-project-progress.md`

- [ ] **BVWP-Datenimport** — Übernahme der BVWP-Daten aus der Legacy-Datenbank. Voraussetzung für die Anzeige der BVWP-Bewertung (Display-Feature bereits implementiert).

- [ ] Cleanup Database structure. Evaluate
- [ ] **New Design** — Integrate a new design layout created by the user via Claude Design. Replace/extend the current Chronicle design system based on the provided layout.
- [ ] **Design Bug: "Abmelden" button** — Font color and background color are nearly identical, making the button unreadable. Fix contrast in header/auth button styles.
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

- [ ] **VIB/Haushalt-Matching: Lernen aus manuellen Zuordnungen**
  Der aktuelle Fuzzy-Matching-Algorithmus (`vib_matching.py`, `finve_matching.py`) berechnet Vorschläge einmalig beim Import und hat kein Gedächtnis. Bestätigte Zuordnungen aus vergangenen Importen (Tabellen `vib_entry_project`, `finve_to_project`) könnten als Trainingsgrundlage dienen: Wenn ein Vorhaben-/FinVe-Name bereits früher manuell einem Projekt zugeordnet wurde, sollte diese Entscheidung als starker Hinweis in zukünftigen Importen gewertet werden. Mögliche Ansätze: (a) Exact-/Near-Match gegen historische `(name_raw, project_id)`-Paare vor dem Fuzzy-Scoring; (b) Boost des Fuzzy-Scores für Projekte, die für ähnliche Namen bereits gewählt wurden. Kein Modell-Training nötig — reine Datenbankabfrage zur Parse-Zeit.

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
- [x] **Chronicle design system — full rollout** — Tokens at `:root` (global); Mantine `defaultRadius: "xs"`; dark header bar; `ChronicleHeadline`/`ChronicleCard`/`ChronicleDataChip`/`ChronicleButton` applied to all pages. See `docs/features/feature-design-system.md`
- [x] Header title ("Schienenprojekte-Dashboard") links back to start page; Haushalt nav item visible to all users (no auth gate)
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
