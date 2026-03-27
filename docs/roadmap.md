# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.

---

## Mid-Term Features


### Dokumente verknüpfen mit Projekttext *(Backend + Frontend)*

Editors can link richly-described **Document** records to individual `ProjectText` entries.
Unlike `TextAttachment` (inline 1:1 file dump), a `Document` is a reusable entity with metadata
(title, description, date, source, visibility) that can be linked to multiple texts and projects.

The `document` and `document_to_project` tables already exist in the DB. Missing is:
- `document_to_text` association
- Full CRUD API for documents
- Frontend management UI

#### Step 1 — DB: `document_to_text` association + migration *(Backend)*
New association table `document_to_text` (many-to-many `Document` ↔ `ProjectText`):
- `document_id` (FK → `document.id`, ondelete=CASCADE, PK)
- `text_id` (FK → `project_text.id`, ondelete=CASCADE, PK)
- `UniqueConstraint('document_id', 'text_id', name='uq_document_to_text')`

Also extend the `Document` model (`models/projects/document.py`):
- Add `texts` relationship: `relationship("ProjectText", secondary="document_to_text", back_populates="documents")`
- Add `uploaded_by_user_id` (FK → `users`, ondelete=SET NULL, nullable) — tracks who created the document
- Add `created_at` (DateTime, default=utcnow)
- Make `file_path` nullable (documents may reference an external URL; field comment says "ggf. als URL oder lokaler Pfad")

Add to `ProjectText` model:
- `documents = relationship("Document", secondary="document_to_text", back_populates="texts")`

Alembic migration: `<date>001_add_document_to_text.py`
- `op.create_table("document_to_text", ...)` with both FKs and UniqueConstraint
- `op.alter_column("document", "file_path", nullable=True)` — make nullable

#### Step 2 — Pydantic schemas *(Backend)*
New schemas in `schemas/projects/document_schema.py`:
- `DocumentSchema`: `id, title, description, file_path, date, source, is_public, created_at, uploaded_by_user_id`
- `DocumentCreate`: `title` (required), `description?, date?, source?, is_public=True, file_path?` (URL; omit when uploading a file)
- `DocumentUpdate`: all fields optional (PATCH semantics)

Update `ProjectTextSchema` to include `documents: list[DocumentSchema] = []`.
Update `get_texts_for_project` CRUD to `selectinload(ProjectText.documents)` alongside the existing `selectinload(ProjectText.attachments)`.

#### Step 3 — CRUD *(Backend)*
New file `crud/projects/documents.py`:
- `create_document(db, data, user_id, stored_filename?, file_size?)` → Document
- `get_document(db, id)` → Document | None
- `list_documents(db)` → list[Document] — for the document picker
- `update_document(db, id, update_data)` → Document | None
- `delete_document(db, id)` → bool — also returns stored_filename so the endpoint can delete the file
- `link_document_to_text(db, document_id, text_id)` — inserts into `document_to_text`; no-op if already linked
- `unlink_document_from_text(db, document_id, text_id)` — deletes row
- `get_documents_for_text(db, text_id)` → list[Document]

#### Step 4 — File storage for documents *(Backend)*
Extend `utils/file_storage.py` (or add a small wrapper) to support a `documents/` subdirectory under `UPLOAD_DIR`:
- Same path-traversal guard and python-magic MIME check as for TextAttachments
- Sub-path: `{UPLOAD_DIR}/documents/{document_id}/{uuid}{ext}`

#### Step 5 — API endpoints *(Backend)*
New file `api/v1/endpoints/documents.py`, registered in `api/v1/api.py`:

| Method | Route | Auth | Notes |
|--------|-------|------|-------|
| GET | `/documents` | public | List all documents (for picker); filter `?is_public=true` for unauthenticated |
| POST | `/documents` | editor+ | Create document; accepts either JSON body (`DocumentCreate` + optional `file: UploadFile`) or JSON-only if `file_path` URL is provided |
| GET | `/documents/{id}` | public* | Get single document |
| PATCH | `/documents/{id}` | editor+ | Update metadata fields |
| DELETE | `/documents/{id}` | editor+ | Delete document + file from disk; fails if linked to any text or project (or cascade — decide at implementation time) |
| GET | `/documents/{id}/download` | public* | Stream file; same security headers as TextAttachment download (Content-Disposition: attachment, RFC 5987, nosniff) |
| POST | `/projects/texts/{text_id}/documents/{document_id}` | editor+ | Link existing document to text |
| DELETE | `/projects/texts/{text_id}/documents/{document_id}` | editor+ | Unlink document from text |

*public only if `document.is_public = true`; require viewer+ auth for non-public documents.

**[Security]** same constraints as TextAttachment: MIME via `python-magic`, path traversal guard, `Content-Disposition: attachment`, RFC 5987 filename, `X-Content-Type-Options: nosniff`, write DB row first then file.
Run `make gen-api` after adding the router.

#### Step 6 — Frontend queries *(Frontend)*
Add to `queries.ts`:
```ts
export type Document = {
    id: number; title: string; description: string | null;
    file_path: string | null; date: string | null; source: string | null;
    is_public: boolean; created_at: string; uploaded_by_user_id: number | null;
};
// useDocuments() — GET /documents
// useCreateDocument() — POST /documents (FormData with optional file)
// useUpdateDocument() — PATCH /documents/{id}
// useDeleteDocument() — DELETE /documents/{id}
// useLinkDocumentToText(textId, projectId) — POST link
// useUnlinkDocumentFromText(textId, projectId) — DELETE unlink
```
Update `ProjectText` type: add `documents: Document[]`.

#### Step 7 — Frontend UI *(Frontend)*
Changes in `features/projects/ProjectTextsSection.tsx`:

**`DocumentList` sub-component** (below `AttachmentList` in `TextCard`):
- Renders each linked document as a row: title + optional date + optional source badge + `is_public` indicator
- If `file_path` starts with `http`: shows external link icon → opens in new tab
- If `file_path` is a stored file: shows download icon → `/documents/{id}/download`
- Unlink button (editor/admin only) with `openConfirmModal` guard; calls `useUnlinkDocumentFromText`

**`DocumentPickerModal` component** (new file `features/projects/DocumentPickerModal.tsx`):
- Searchable list of all documents (from `useDocuments()`)
- Each row: title, date, source badge
- Click → calls `useLinkDocumentToText`; closes on success
- Footer: "Neues Dokument erstellen" button → opens `DocumentFormModal`

**`DocumentFormModal` component** (new file `features/projects/DocumentFormModal.tsx`):
- Fields: Titel (required), Beschreibung, Datum, Quelle, Sichtbarkeit (`is_public` toggle)
- Attachment: either file upload (re-uses file input pattern from `AttachmentUploadArea`) OR URL input — toggled by a radio/segment
- On submit: calls `useCreateDocument`; if `linkAfterCreate=true` also calls `useLinkDocumentToText`

Add "Dokument verknüpfen" button (editor/admin only) to `TextCard` → opens `DocumentPickerModal`.

#### Step 8 — Documentation
- Update `docs/architecture.md` / `docs/models.md` with `DocumentToText` association
- Update `DocumentationPage.tsx` to mention document library and text linking
- Mark this roadmap section done

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
