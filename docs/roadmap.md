# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.

---


## Short-Term Features

Bug:
- [ ] Switch Map <-> List overlaps with header menu

- [x] make the "Schienenprojekte-Dashboard" clickable -> return to Start Page

This tasks must be done by human:
- [x] Import of the Haushalt Berichte 2020 - 2025

### Security Problems

- [x] **[Critical] Basic Auth token stored in `localStorage`** (`auth.ts:22–36`) — Credentials now stored in memory only; `localStorage` persistence removed.
- [x] **[Critical] SQL f-string injection pattern in pgRouting** (`routing/core.py:49–62`) — SQL moved to module-level string constants; f-string eliminated. All dynamic values passed as bound parameters.
- [x] **[High] Changelog endpoint unauthenticated** (`projects.py:139–148`) — Added `Depends(require_roles())` to the GET handler; any authenticated user required.
- [x] **[High] PDF upload lacks content-type check** (`haushalt_import.py:44–57`) — Added `content_type == "application/pdf"` check; request rejected with 400 if not a PDF. (Size limit skipped: Haushalt PDFs are intentionally large.)
- [x] **[High] Revert endpoint bypasses field allowlist** (`projects.py:151–183`) — Replaced `hasattr` guard with `field_name in ProjectUpdate.model_fields.keys()`.
- [x] **[Medium] Route write endpoints lack explicit role requirement** (`project_routes.py:48–70`) — `POST /routes/calculate` now requires `editor` or `admin` role.
- [x] **[Medium] CORS allows all methods and headers with credentials** (`main.py:10–16`) — Restricted to `["GET","POST","PUT","PATCH","DELETE","OPTIONS"]` and `["Content-Type","Authorization"]`.
- [x] **[Medium] Dev Redis exposed without password** (`docker-compose.dev.yml`) — Added `--requirepass devpassword`; Celery URLs in `.env.example` updated accordingly.
- [x] **[Low] `unmatched_action` accepts unconstrained string** (`schemas/haushalt_import.py`) — Changed to `Literal["save", "discard"]`.
- [x] **[Low] RINF credentials silently accept empty strings** (`core/config.py`) — Changed to `Optional[str] = None`.

---

## Mid-Term Features

### Secure Session Cookies (replace in-memory Basic Auth token)

Currently credentials are held in memory only (no `localStorage`), which means users must log in again after every page reload. The proper fix is to have the backend issue a signed `httpOnly` session cookie — inaccessible to JavaScript, survives reloads, and expires automatically.

#### Backend

**1. `config.py`** — add `session_secret_key: str` (required, read from `.env`). Used to HMAC-sign session tokens.

**2. `core/security.py`** — add three helpers:
- `create_session_token(user_id: int) -> str` — builds `"{user_id}:{timestamp}"`, signs with HMAC-SHA256 using `session_secret_key`, returns `"{payload}.{signature}"` (base64url-encoded)
- `verify_session_token(token: str) -> int | None` — verifies signature, checks expiry (e.g. 7 days), returns `user_id` or `None`
- `require_session()` — FastAPI dependency: reads the `session` cookie, calls `verify_session_token`, loads user from DB, raises 401 if missing/invalid. Mirrors the interface of `require_roles()`.

**3. New file `api/v1/endpoints/auth.py`** — two endpoints:
- `POST /api/v1/auth/session` — JSON body `{ username, password }`, validates via existing `_authenticate()` logic, calls `response.set_cookie(key="session", value=token, httponly=True, secure=True, samesite="strict", max_age=604800)`
- `DELETE /api/v1/auth/session` — clears the cookie (`response.delete_cookie("session")`); requires valid session

**4. `api/v1/router.py`** — register the new auth router.

**5. `GET /api/v1/users/me`** — accept both `require_roles()` (Basic Auth) and `require_session()` so both auth methods work during the transition. Long-term, Basic Auth can be removed from non-admin endpoints.

**6. Run `make gen-api`** to sync the frontend client.

#### Frontend

**`auth.ts`**
- `login()`: call `POST /api/v1/auth/session` with `{ username, password }` as JSON body instead of setting credentials manually. On success the browser stores the cookie automatically.
- `logout()`: call `DELETE /api/v1/auth/session`.
- Remove `setCredentials` / `getCredentials` entirely.
- The existing `useEffect` on mount that calls `GET /api/v1/users/me` already handles session restore — if the cookie is valid the user is populated transparently.

**`client.ts`** (the API fetch wrapper)
- Remove the `Authorization: Basic ...` header injection.
- Add `credentials: "include"` to all `fetch` calls so the browser sends the cookie cross-origin (needed because frontend dev server runs on a different port than the backend).

#### .env changes

Add to `.env.example` and `.env.example`:
```
SESSION_SECRET_KEY=<random 32-byte hex string>
```
Document in `docs/environment.md`.

#### Security properties after this change

- Cookie is `httpOnly` → JavaScript can never read the session token
- `SameSite=Strict` → CSRF is not possible (browser won't send cookie on cross-site requests)
- `Secure` flag → cookie is only sent over HTTPS (set conditionally: `secure=settings.environment == "production"`)
- 7-day expiry → automatic session invalidation

#### Implementation order

1. [x] `config.py` — add `session_secret_key`
2. [x] `core/security.py` — add `create_session_token`, `verify_session_token`, `require_session`
3. [x] `api/v1/endpoints/auth.py` — `POST` + `DELETE /api/v1/auth/session`
4. [x] Register router + update `GET /users/me` to accept session auth
5. [x] Run `make gen-api`
6. [x] `auth.ts` + `client.ts` — swap credential header for cookie flow


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
- [x] **FinVe-Diagramme überarbeitet**: Kostenentwicklung zeigt jetzt eine einzelne Linie (`cost_estimate_actual`) je Haushaltsbericht mit korrekter Y-Achse (Breite 130 px, Domain +10 % über Maximum); Budgetverteilung als DonutChart des aktuellsten Berichts (statt Balkendiagramm über Jahre); Diagrammtitel zeigt Berichtsjahr; Tabs umbenannt zu „Haushaltbericht {Jahr}". Fehlerbehebung: `@mantine/charts/styles.css` in `main.tsx` ergänzt (fehlte → DonutChart hatte Höhe 0).
- [x] **FinVe-Übersicht öffentlich zugänglich**: `/finves`-Route und Backend-Endpunkt `GET /api/v1/finves/` waren bereits ohne Auth, aber das Menü und die Seitenkomponente haben eingeloggte Nutzer verlangt. Jetzt für alle sichtbar.

### Texte & Kommentare
- [x] Projekttexte anzeigen (über übergeordnetes Projekt), erstellen, bearbeiten
- [x] Sichtbarkeit von Texten: eingeloggt-only oder öffentlich
- [x] Versionshistorie und Bearbeitungsformular nur für eingeloggte Nutzer sichtbar

### Change Tracking (vollständig)
- [x] DB-Modelle `change_log` + `change_log_entry` + Alembic-Migration
- [x] `PATCH /api/v1/projects/{id}` — schreibt ChangeLog-Einträge je geändertem Feld (Rolle: editor/admin)
- [x] `GET /api/v1/projects/{id}/changelog` — öffentlich lesbar
- [x] Bearbeitungsformular in `ProjectDetail` (editor/admin); alle Felder bearbeitbar
- [x] Versionshistorie-Timeline in `ProjectDetail` (`ProjectHistorySection.tsx`); nur für eingeloggte Nutzer
- [x] „Zurücksetzen"-Button pro `ChangeLogEntry` (editor/admin) via `useRevertProjectField` hook

### Benutzerverwaltung
- [x] Login-UI: Modal im Header, Credentials im React-Context, Authorization-Header bei API-Requests, 401/403-Interceptor
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
- [x] **Docker Compose GitHub Build**: `docker-compose.yml` baut alle Services direkt aus dem GitHub-Repository am angegebenen Release-Tag (`APP_VERSION`). Server benötigt nur `docker-compose.yml` + `.env` — kein Source-Upload nötig. Update = `APP_VERSION` in `.env` ändern + `make docker-prod-build`.
- [x] Docker: Dev (nur DB + Redis), Prod (DB + Backend + Frontend/nginx + Worker); Entrypoint-Skript mit Alembic-Migration, Makefile-Targets
- [x] Celery Task Queue mit Redis-Broker; Task-Status-Endpoint `GET /api/v1/tasks/{task_id}`
- [x] Backup & Restore: `scripts/backup_db.sh`, `scripts/restore_db.sh`, Makefile-Targets; Doku in `docs/production_setup.md`
- [x] Backend-Authentifizierung: HTTP Basic Auth, PBKDF2, Rollen viewer/editor/admin
- [x] Routing-Algorithmus implementiert (pgRouting / GrassHopper-Microservice)
- [x] Docs bereinigt: `docs/architecture.md` als zentrale Architekturdokumentation

### Verkehrsinvestitionsbericht (VIB) Import (vollständig)

Jährlicher Import des Bundestagsdrucksache-PDFs „Verkehrsinvestitionsbericht für das Berichtsjahr XXXX". Nur **Abschnitt B** (Schienenwege der Eisenbahnen des Bundes) wird importiert; Abschnitte C (Straße) und D (Wasserstraße) werden ignoriert.

Der vollständige Text jedes Vorhabens wird gespeichert und in `ProjectDetail` angezeigt. Optional können per LLM automatisch Schlüsselinformationen extrahiert und als Einträge in das `ProjectProgress`-Datenmodell geschrieben werden (VIB ist eine von mehreren Quellen des ProjectProgress-Systems).

---

#### Dokumentstruktur (Referenz: VIB 2023, Drucksache 21/125)

Jedes Schienenvorhaben (`B.4.x.x`) belegt 1–6 Seiten:

| Block | Inhalt | Extraktion |
|-------|--------|------------|
| Überschrift | Abschnittsnr., Name (z.B. „ABS Lübeck–Rostock–Stralsund (VDE Nr. 1)"), Kategorie | Regex |
| Streckenmap | Kartenbild | ignorieren |
| Verkehrliche Zielsetzung | Fließtext / Bullets | Freitext |
| Durchgeführte / Geplante Maßnahmen | Bullets | Freitext |
| Noch umzusetzende Maßnahmen | Bullets (optional) | Freitext |
| Projektkenndaten | Streckenlänge (km), Geschwindigkeit (km/h), Gesamtkosten (Mio. €) | Regex |
| **PFA-Tabelle** | Nr. PFA, Örtlichkeit, Entwurfsplanung, Abschluss FinVe, Datum PFB, Baubeginn, Inbetriebnahme | pdfplumber table |
| **Teilinbetriebnahmen [Jahr]** | Was im Berichtsjahr in Betrieb ging | Label + Bullets |
| **Bauaktivitäten [Jahr]** | Was im Berichtsjahr gebaut wurde (primärer Fortschrittsindikator) | Label + Bullets |

Kategorien: `laufend` (B.4.1), `neu` (B.4.2), `potentiell` (B.4.3), `abgeschlossen` (Kurzerwähnung).

---

#### Phase 1 — Datenbankmodell

```
vib_report
  id, year (int, unique), drucksache_nr (str), report_date (date),
  imported_at, imported_by_user_id (FK users)

vib_entry
  id, vib_report_id (FK), project_id (FK projects, nullable – nach Mapping),
  vib_section (str, z.B. "B.4.1.1"), vib_lfd_nr (str),
  vib_name_raw (str),
  category (enum: laufend | neu | potentiell | abgeschlossen),
  raw_text (text),                  -- vollständiger Plain-Text des Vorhabens
  bauaktivitaeten (text),           -- Abschnitt "Bauaktivitäten [Jahr]"
  teilinbetriebnahmen (text),       -- Abschnitt "Teilinbetriebnahmen [Jahr]"
  verkehrliche_zielsetzung (text),
  durchgefuehrte_massnahmen (text),
  noch_umzusetzende_massnahmen (text),
  strecklaenge_km (float), gesamtkosten_mio_eur (float), entwurfsgeschwindigkeit (str),
  ai_extracted (bool, default False)

vib_pfa_entry
  id, vib_entry_id (FK), abschnitt_label (str, z.B. "1. Baustufe"),
  nr_pfa (str), oertlichkeit (str), entwurfsplanung (str),
  abschluss_finve (str), datum_pfb (str), baubeginn (str), inbetriebnahme (str)
```

Alembic-Migration für alle drei Tabellen.

---

#### Phase 2 — PDF-Parser

Celery-Task `parse_vib_pdf` in `tasks/vib.py` (pdfplumber, bereits vorhanden).

1. **Sektionsgrenzen**: Seite für Seite; Start bei Heading „B Schienenwege", Stop bei „C Bundesfernstraßen".
2. **Vorhaben-Grenzen**: Regex `^B\s*\.4\.[123]\.\d+` in fettem/blauem Heading → neuer Entry; Text akkumulieren über Seitenumbrüche.
3. **Strukturierte Felder**: Regex auf `Streckenlänge:`, `Gesamtkosten:`, `Entwurfsgeschwindigkeit:`.
4. **Freitextblöcke**: Label-Suche auf `Bauaktivitäten \d{4}:` und `Teilinbetriebnahmen \d{4}:`, Bullets bis nächstes Hauptlabel.
5. **PFA-Tabelle**: `pdfplumber.extract_tables()`, Spaltenköpfe als Erkennungsmerkmal, Zwischenzeilen als `abschnitt_label`.
6. **raw_text**: gesamter akkumulierter Plain-Text des Vorhabens — wird unverändert gespeichert.
7. **Abgeschlossene Vorhaben** (1–2 Sätze, keine PFA-Tabelle): `category=abgeschlossen`, nur `raw_text` + `vib_name_raw`.

---

#### Phase 3 — Projektmapping (interaktiv wie Haushalt-Import)

**Auto-Matching:**
1. **VDE-Nummer** aus `vib_name_raw` extrahieren → gegen DB-Projektfeld matchen (höchste Konfidenz)
2. **Fuzzy-Name-Matching** auf bereinigtem Streckennamen (SequenceMatcher + Token-Overlap, Threshold 0.5) — analog `finve_matching.py`
3. Bisherige Mappings aus früheren Imports als Lookup-Cache

**Admin-Review-UI** (`/admin/vib-import`):
- **Upload-Schritt**: PDF hochladen → Celery-Task → Polling (identisches Muster wie Haushalt-Import)
- **Review-Tabelle**: eine Zeile pro extrahiertem Vorhaben
  - VIB-Abschnitt, Name, Kategorie-Badge
  - Vorgeschlagenes Projekt mit Konfidenz-Chip (grün ≥ 0.7, gelb 0.5–0.7, rot < 0.5 / kein Treffer)
  - Freitext-Projektsuche als manuelle Override
  - Aufklappbarer Preview: extrahierte Felder + raw_text-Snippet
- **Confirm-Button**: schreibt alle Einträge in DB; bei aktivierter KI optional LLM-Extraktion starten

---

#### Phase 4 — Optionale LLM-Extraktion → ProjectProgress

Nach dem Confirm kann der Admin optional „KI-Extraktion starten" wählen. Der Task `extract_vib_progress` läuft asynchron (Celery).

**API-Design (provider-agnostisch):**

```python
# settings: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
# Unterstützt jeden OpenAI-kompatiblen Endpunkt:
#   OpenAI: api.openai.com/v1
#   Anthropic (via compatibility layer)
#   Ollama: localhost:11434/v1
#   Azure OpenAI, Mistral, etc.

POST {LLM_BASE_URL}/chat/completions
{
  "model": "{LLM_MODEL}",
  "messages": [{"role": "user", "content": "<kompakter Prompt>"}],
  "response_format": { "type": "json_object" }
}
```

**Token-Minimierung** — der Prompt enthält nur bereits extrahierte Kurzfelder, NICHT `raw_text`:

```
Analysiere dieses Bahnprojekt und antworte als JSON.

Projekt: {vib_name_raw}
Gesamtkosten: {gesamtkosten_mio_eur} Mio. €
Bauaktivitäten {year}: {bauaktivitaeten}          # meist 3–8 Sätze
Inbetriebnahmen {year}: {teilinbetriebnahmen}     # meist 1–3 Zeilen
Offene PFA-Abschnitte (Baubeginn/IBM noch offen): {kompakte_pfa_liste}

Antworte ausschließlich als JSON:
{
  "cost_total_mio": <float|null>,
  "construction_start_next": "<MM/YYYY|null>",   // frühester offener Baubeginn
  "commissioning_next": "<MM/YYYY|null>",        // früheste offene Inbetriebnahme
  "progress_summary": "<max 2 Sätze DE>",
  "key_events": ["<event1>", "<event2>"]         // max 3 Einträge
}
```

Typischer Prompt: ~300–500 Token. KI-Extraktion läuft nur wenn `LLM_BASE_URL` konfiguriert ist; ohne Konfiguration ist der Button ausgegraut.

**Ergebnis** wird als `ProjectProgress`-Eintrag gespeichert (`source="vib_{year}"`). Definition des `ProjectProgress`-Modells ist eine eigenständige Roadmap-Aufgabe — VIB-Import bereitet das Feld vor, schreibt aber noch nicht direkt in das Modell bis dieses implementiert ist. Bis dahin: Extraktion in `vib_entry.ai_result` (JSON-Feld) speichern.

---

#### Phase 5 — API-Endpunkte

- `POST /api/v1/import/vib` — PDF-Upload → Task → `{ task_id }`
- `GET /api/v1/import/vib/{task_id}/result` — Parse-Ergebnis + Mapping-Vorschläge
- `POST /api/v1/import/vib/{task_id}/confirm` — Mapping bestätigen + DB schreiben
- `POST /api/v1/import/vib/{task_id}/extract-ai` — optionaler LLM-Task starten
- `GET /api/v1/vib/reports` — Liste aller importierten Berichte
- `GET /api/v1/projects/{id}/vib` — alle VIB-Einträge eines Projekts (alle Jahre)

Schemas in `schemas/vib.py`, CRUD in `crud/vib.py`, Router in `api/v1/endpoints/vib_import.py`.

---

#### Phase 6 — Frontend-Anzeige in ProjectDetail

Sektion **„Verkehrsinvestitionsberichte"** (nur eingeloggte Nutzer, analog Changelog):

- Tab-Leiste pro Berichtsjahr (absteigend)
- Je Tab: Bauaktivitäten-Text, Teilinbetriebnahmen-Text, aufklappbarer Volltext (`raw_text`), aufklappbare PFA-Tabelle
- KI-Badge wenn `ai_extracted=True`, verlinkt zu ProjectProgress (sobald implementiert)

---

#### Umgebungsvariablen (neu)

| Variable | Beschreibung | Beispiel |
|----------|-------------|---------|
| `LLM_BASE_URL` | OpenAI-kompatibler Endpunkt (leer = KI deaktiviert) | `https://api.openai.com/v1` |
| `LLM_API_KEY` | API-Key für den Endpunkt | `sk-...` |
| `LLM_MODEL` | Modellname | `gpt-4o-mini` |

---

- [x] DB-Modelle + Alembic-Migration
- [x] Parser `tasks/vib.py` + Debug-Script `scripts/dump_vib_parse_result.py`
- [x] Auto-Matching `tasks/vib_matching.py`
- [x] API-Endpunkte + Schemas + CRUD + `make gen-api`
- [x] Frontend Import-Flow `features/vib-import/`
- [x] LLM-Extraktions-Task `tasks/vib_ai_extraction.py` (optionaler Schritt)
- [x] Frontend Projektdetail-Sektion `features/vib/VibSection.tsx`
