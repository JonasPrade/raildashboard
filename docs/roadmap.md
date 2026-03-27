# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.

---

## Mid-Term Features


---

### PDF Preview on Demand (in-page, react-pdf) ✅

PDF attachments currently force a browser download. Goal: "Vorschau"-button opens the PDF rendered inside a Mantine `Modal` using `react-pdf` (PDF.js wrapper).

#### Backend — inline serving endpoint

Add query param `inline: bool = False` to the existing download endpoint (`GET /api/v1/projects/texts/{text_id}/attachments/{attachment_id}/download`):
- If `inline=true` **and** `mime_type == "application/pdf"`: set `Content-Disposition: inline; filename*=...` instead of `attachment`
- All other files (Word, Excel, images) keep forced download regardless of param
- Keep `X-Content-Type-Options: nosniff`

#### Frontend — `PdfPreviewModal` component

New file: `apps/frontend/src/features/projects/PdfPreviewModal.tsx`

- Add dependency: `react-pdf` (`pnpm add react-pdf`) — ships its own PDF.js worker
- Configure worker once in `main.tsx`: `pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()`
- Props: `{ opened, onClose, attachmentUrl, filename }`
- `attachmentUrl` = existing download URL + `?inline=true`
- Renders inside `<Modal size="xl" title={filename}>`:
  - `<Document>` from `react-pdf` loading from `attachmentUrl`
  - Page navigation: previous / next `ActionIcon` buttons + `"{page} / {total}"` counter
  - Loading state: centered `Loader`
  - Error state: "PDF konnte nicht geladen werden" with download fallback link
- Modal is lazy — PDF only fetches when `opened === true`

#### Integration in `AttachmentList`

In `ProjectTextsSection.tsx`, next to each PDF attachment row:
- Add a "Vorschau" `ActionIcon` (eye icon) — only shown when `mime_type === "application/pdf"`
- Click → set `previewAttachment` state → renders `<PdfPreviewModal opened ... />`
- Existing download anchor remains unchanged

**Steps:**
- [x] Backend: add `inline` param to download endpoint
- [x] Frontend: `pnpm add react-pdf`; configure worker in `main.tsx`
- [x] Frontend: `PdfPreviewModal.tsx` component
- [x] Frontend: integrate eye-icon button + modal state into `AttachmentList` in `ProjectTextsSection.tsx`

### Sonstiges

- [ ] **ProjectProgress** *(Backend + Frontend)*
  Fortschrittsstand eines Projekts (Planungs-, Genehmigungs-, Bauphase). Speist sich aus mehreren Quellen (z. B. Bundestag-Drucksachen, Pressemitteilungen, manuelle Eingabe). Benötigt Validierungslogik für Konflikte zwischen Quellen.
  - Backend: `ProjectProgress`-Modell implementieren (Status, Datum, Quelle, Kommentar)
  - Frontend: Zeitleiste/Meilenstein-Ansicht in `ProjectDetail`

- [ ] **BVWP-Datenimport** — Übernahme der BVWP-Daten aus der Legacy-Datenbank. Voraussetzung für die Anzeige der BVWP-Bewertung (Display-Feature bereits implementiert).

- [ ] **Vervollständigung und Automatisierung Tests**
- [ ] **Special view of Generalsanierung. Timeline when which Generalsanierung is started and when it is finished**

---

## Long-Term Features

### Routenvorschlag per GrassHopper *(Backend + Frontend)*

The backend infrastructure is fully implemented (GraphHopper HTTP client, `RouteService`, endpoints `POST /routes/calculate`, `POST /projects/{id}/routes`, `PUT /projects/{id}/routes/{route_id}`, `GET /projects/{id}/routes`, ORM model `routes`, CRUD, caching, tests). What is missing is the frontend workflow and one small backend addition.

#### ✅ Done — Docker infrastructure
- `docker/graphhopper/config.yml` — GraphHopper config with `rail_default` profile
- `docker-compose.yml` (prod) — `graphhopper` service added; starts automatically with the stack
- `docker-compose.dev.yml` — `graphhopper` service added behind `--profile routing` (opt-in)
- `.env.example` — `ROUTING_BASE_URL=http://graphhopper:8989` (was broken `localhost`)
- `.env.example` — added note about dev compose profile command
- `docs/production_setup.md` — GraphHopper setup section (PBF placement, first start, cache invalidation)
- **Prerequisite (human task):** place OSM PBF at `data/graphhopper/map.osm.pbf` before first start

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

- [ ] **Netzzustandsbericht** — PDF-Import, Extraktion relevanter Kennzahlen in die Datenbank

- [ ] **Beschleunigungskommission Schiene** — Datentransfer aus öffentlichen Quellen + automatische Updates

- [ ] **RINF-Daten evaluieren** — Für Bahnhofs-/Stationsverbindungen ggf. weiterhin benötigt

- [ ] **GeoLine-Erstellung** — Möglichkeit, neue Streckengeometrien zu erzeugen, wenn vorhandene unvollständig/ungültig sind. Ansatz noch offen (Zeichentool auf Karte vs. automatische Vervollständigung).

- [ ] **Automatisierung Preisniveau** — Tool zum Berechnen von Preisen gemäß Inflation/Baukostenentwicklung auf das aktuelle Jahr

- [ ] **Passwort zurücksetzen per E-Mail** *(Backend + Frontend)*
  → Vollständiger technischer Plan: [`docs/email_password_reset_plan.md`](email_password_reset_plan.md)
  Backend:
  - Feld `email` zum User-Modell ergänzen + Migration
  - Tabelle `password_reset_token` (Token, User-ID, Ablaufzeitpunkt) + Migration
  - SMTP-Konfiguration in Settings (Host, Port, Credentials)
  - `POST /api/v1/auth/request-reset` — nimmt E-Mail, sendet Reset-Link per Mail
  - `POST /api/v1/auth/reset-password` — nimmt Token + neues Passwort, invalidiert Token
  Frontend:
  - „Passwort vergessen?"-Link im Login-Modal → E-Mail-Eingabeformular
  - Reset-Formular (neues Passwort, Token aus URL-Param des Mail-Links)

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

### Security
- [x] **httpOnly session cookies** — `POST /api/v1/auth/session` issues a signed HMAC-SHA256 cookie; `DELETE` logs out. `require_auth` and `require_roles` accept both cookie and HTTP Basic Auth. `WWW-Authenticate` header removed to prevent browser native login dialog.
- [x] Basic Auth token removed from `localStorage`; credentials held in memory only
- [x] SQL f-string injection pattern in pgRouting fixed
- [x] Changelog endpoint authentication enforced
- [x] PDF upload content-type check added
- [x] Revert endpoint field allowlist enforced
- [x] Route write endpoints require explicit role
- [x] CORS restricted to allowed methods/headers
- [x] Dev Redis password-protected

### UI / UX
- [x] **Edit ProjectGroup membership in ProjectEdit form** — `ProjectGroupRef` added to `ProjectSchema`; `project_group_ids` in `ProjectUpdate`; CRUD replaces many-to-many association; `MultiSelect` in `ProjectEdit.tsx` populated via `useProjectGroups()`
- [x] **Sticky Save/Cancel footer in ProjectEdit drawer** — buttons moved out of the scroll area into a fixed footer (`Box` with top border); drawer body uses flex-column layout so footer is always visible
- [x] **BVWP-Bewertung in Projektdetail** — `GET /api/v1/projects/{id}/bvwp` endpoint; `BvwpProjectDataSchema` (Pydantic) + `get_bvwp_data` CRUD; `BvwpDataSection.tsx` in `ProjectDetail` with 11 tab groups; NKV shown as badge
- [x] Project search on map and list view — client-side substring filter; `?search=` URL param with 200 ms debounce
- [x] Admin-configurable ProjectGroup visibility and default selection; group filter drawer redesigned
- [x] Admin-configurable map group mode (`preconfigured` / `all`) in `/admin/project-groups`
- [x] Login via Enter-Taste — `LoginModal.tsx`
- [x] Inhaltsverzeichnis in Projektdarstellung (links, ausklappbar)
- [x] Header-Menü kollabiert zu Burger-Menü bei schmalen Fenstern; Kollaps-Schwellwert auf 100em erhöht
- [x] Projektkarte zentriert beim Laden auf den Projektmittelpunkt
- [x] Karte/Liste als Tab-Toggle auf Route `/` (`?view=map` / `?view=list`); `/projects` → Redirect
- [x] Gruppen-Persistenz als URL-Param (`?group=id1,id2`)
- [x] Toggle „Nur übergeordnete Projekte"
- [x] Liniendicke und Punktgröße auf Karte einstellbar
- [x] FinVe-Diagramme überarbeitet (Kostenentwicklung, DonutChart)
- [x] FinVe-Übersicht (`/finves`) öffentlich zugänglich
- [x] SV-FinVes in Projektdetailseite als kompakter Tag dargestellt
- [x] Hilfe-Popover (?) neben Karte/Liste-Toggle — erklärt Suche, Gruppenfilter und „Nur Hauptprojekte"-Schalter
- [x] Lade-Overlay auf der Karte während Projektgruppen initial geladen werden

### Texte & Dateianhänge
- [x] Projekttexte anzeigen, erstellen, bearbeiten
- [x] Sichtbarkeit von Texten: eingeloggt-only oder öffentlich
- [x] Versionshistorie und Bearbeitungsformular nur für eingeloggte Nutzer sichtbar
- [x] **Dateianhänge für Projekttexte** — Editors können PDFs, Word, Excel und Bilder (max. 50 MB) an Projekttexte anhängen, direkt beim Erstellen oder nachträglich. `TextAttachment`-Modell + Migration `20260326001`; `utils/file_storage.py` mit Pfad-Traversal-Guard + MIME-Validierung via `python-magic`; API: POST/GET/DELETE/Download; Docker-Volume `uploads`; `UPLOAD_DIR` env var (lokal in `.env` setzen)
- [x] **Dokumente verknüpfen mit Projekttext** — Editors können wiederverwendbare `Document`-Einträge (Titel, Beschreibung, Datum, Quelle, Sichtbarkeit, optionaler Datei-Upload oder URL) mit einzelnen `ProjectText`-Einträgen verknüpfen. `document_to_text`-Assoziationstabelle + Migration; vollständiges CRUD-API (`/documents`, Link/Unlink-Endpunkte); `DocumentPickerModal`, `DocumentFormModal`, `DocumentList` in `ProjectTextsSection.tsx`

### Change Tracking
- [x] DB-Modelle `change_log` + `change_log_entry` + Alembic-Migration
- [x] `PATCH /api/v1/projects/{id}` — schreibt ChangeLog-Einträge je geändertem Feld
- [x] `GET /api/v1/projects/{id}/changelog`
- [x] Bearbeitungsformular in `ProjectDetail` (editor/admin)
- [x] Versionshistorie-Timeline in `ProjectDetail` — nur für eingeloggte Nutzer
- [x] „Zurücksetzen"-Button pro `ChangeLogEntry` via `useRevertProjectField` hook

### Benutzerverwaltung
- [x] Login-UI: Modal im Header, Credentials im React-Context, 401/403-Interceptor
- [x] Rollenbasierte Bearbeitung: Schreiboperationen nur für editor/admin sichtbar
- [x] User-Management-Seite `/admin/users` (nur admin): Nutzer anlegen, Rolle/Passwort ändern, löschen

### Haushaltsberichte-Import
- [x] DB-Modelle + Alembic-Migration
- [x] Celery-Task `parse_haushalt_pdf` mit `pdfplumber`; Parser-Fixes für 2026-Format
- [x] API unter `/api/v1/import/haushalt`: `POST /parse`, `GET /parse-result`, `POST /confirm`, `GET/PATCH /unmatched`
- [x] Frontend Upload-Flow mit Celery-Polling, Review-Tabelle, Projektzuordnung per MultiSelect
- [x] Fuzzy-Matching (`tasks/finve_matching.py`) für automatische Projektzuordnungs-Vorschläge
- [x] FinVe → mehrere Projekte (bidirektionale Sync beim Confirm)
- [x] FinVe-Anzeige in `ProjectDetail` mit 3 Tabs (Budgetverteilung, Kostenentwicklung, Detailtabelle)
- [x] **Sammelfinanzierungsvereinbarungen (SV-FinVes)**: Erkennung, `is_sammel_finve`-Flag, Review-UI, Fuzzy-Vorschläge, `haushalt_year`-Spalte für Jahrestracking
- [x] **FinVe-Übersicht** (`/finves`): Kartenansicht, Suche, Filter, Budget-Diagramme
- [x] **Import-Anleitung** (`/admin/haushalt-import/guide`)

### Verkehrsinvestitionsbericht (VIB) Import
- [x] DB-Modelle (`vib_report`, `vib_entry`, `vib_pfa_entry`) + Alembic-Migration
- [x] Parser `tasks/vib.py` + Debug-Script
- [x] Auto-Matching `tasks/vib_matching.py`
- [x] API-Endpunkte + Schemas + CRUD + `make gen-api`
- [x] Frontend Import-Flow `features/vib-import/`
- [x] LLM-Extraktions-Task `tasks/vib_ai_extraction.py` (optionaler Schritt)
- [x] Frontend Projektdetail-Sektion `features/vib/VibSection.tsx`

### Infrastruktur
- [x] **Docker Compose GitHub Build**: baut alle Services aus GitHub-Repository am Release-Tag
- [x] Docker: Dev (nur DB + Redis), Prod (DB + Backend + Frontend/nginx + Worker)
- [x] Celery Task Queue mit Redis-Broker; Task-Status-Endpoint
- [x] Backup & Restore: `scripts/backup_db.sh`, `scripts/restore_db.sh`
- [x] Routing-Algorithmus implementiert (pgRouting / GrassHopper-Microservice)
