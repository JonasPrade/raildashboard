# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.

> **Steuerung läuft über das GitHub-Projects-Board** (`docs/github-projects.md`),
> nicht über diese Datei. Diese Roadmap ist eine Lese-Übersicht; verbindliche
> Reihenfolge und Status stehen im Board. Lose Ideen → `docs/user-backlog.md`.

---

## Short-Term Features

- [x] integrate the new design described in `docs/DESIGN.md`

This tasks must be done by human:
- [ ] Import of the Haushalt Berichte 2020 - 2025
- [ ] Update time slots Hochleistungskorridore

---

## v0.0.5 — geplant: Operations & Resilience

Themenschwerpunkt: die im v0.0.4-Rollout aufgedeckten Stabilitäts- und Tooling-Lücken schließen, plus zwei kleinere User-Features. Bewusst überschaubarer Scope, damit die Version zügig ausgeliefert werden kann.

### Operations (alle aus dem v0.0.4-Rollout)

- [x] **Backup um Docker-Volumes erweitern** — *Priorität: hoch*
  `scripts/backup_db.sh` erzeugt jetzt pro Lauf paarig `raildashboard_<ts>.dump` + `uploads_<ts>.tar.gz` (tar.gz des Volumes `raildashboard_uploads`, via `docker run alpine`). 14-Tage-Retention für beide Datei-Typen separat. Steuerung per `SKIP_UPLOADS_BACKUP=1` / `UPLOADS_VOLUME=…`. `scripts/restore_db.sh` findet das paarige Tar automatisch und restored es (Volume wird vor extract geleert); `UPLOADS=none` / `UPLOADS=<pfad>` als Overrides. Makefile-Target `docker-backup-db` analog erweitert. Doku in `docs/production_setup.md` (Sektionen "Tägliches Backup via Docker", "Uploads-Volume", "Backup-System"). Systemd-Service bleibt unverändert, da er bereits `scripts/backup_db.sh` aufruft.

- [x] **Migrations-Race zwischen `backend` und `worker` beheben** — *Priorität: hoch*
  Entrypoint `apps/backend/docker-entrypoint.sh` respektiert jetzt `"$@"` (statt hardcoded `exec uvicorn`) und überspringt den Alembic-Schritt wenn `SKIP_MIGRATIONS=1`. Dockerfile bekommt ein `CMD` mit dem Standard-Uvicorn, damit das Backend unverändert läuft. Worker-Service in `docker-compose.yml` setzt `SKIP_MIGRATIONS=1` und `depends_on.backend.condition: service_started`. Damit migriert nur noch das Backend, der Worker exec()t seine `command: celery ...`-Zeile (was vorher übrigens auch nicht passierte — siehe Doku-Update in `apps/backend/README.md`).

- [x] **`scripts/transfer_db.sh` robust machen** — *Priorität: mittel*
  Skript komplett umgebaut: Non-empty-Verifikation lokal+remote, Pre-Restore-Safety-Backup von prod (`prod_BEFORE_dev_overwrite_<ts>.dump`), Backend+Worker werden vorm Restore gestoppt und am Ende immer wieder gestartet, `pg_terminate_backend`, `grep -v '^SET transaction_timeout'`, `psql -v ON_ERROR_STOP=1 --single-transaction`, `COUNT(*)`-Vergleich auf `project`/`finve`/`change_log`. Gilt für beide Richtungen (`dev-to-prod` und `prod-to-dev`). Doku in `docs/production_setup.md` aktualisiert; manueller Pfad bleibt als Debug-Fallback dokumentiert.

### Features

- [ ] **ProjectProgress — Fortschrittsanzeige End-to-End** *(Backend + Frontend)* — *Priorität: hoch, das große Thema von v0.0.5*

  Strukturierte Erfassung und Visualisierung des Projektfortschritts (Vorplanung → Entwurfsplanung → Genehmigungsplanung/PFA → Ausführungsplanung → Bau → Inbetriebnahme → abgeschlossen). Mehrere Quellen schreiben in dasselbe Modell (manuell, VIB, später Haushalt/Presse). Ziel: in jeder Projektsicht (Detail, Liste, Karte, Übersicht) sofort erkennbar machen, in welcher Phase ein Projekt steht und wann der nächste Meilenstein erreicht wurde.

  Bestehendes Feature-Doc: `docs/features/feature-project-progress.md` — Datenmodell, Endpoints und Komponentenname sind dort bereits skizziert; **dieser Roadmap-Eintrag erweitert den Scope um Aggregation, Listen-/Karten-Anzeige und Filterung**, weil reine Timeline allein zu wenig ist.

  > **Hinweis (Stand v0.0.5):** Die Umsetzung folgt dem **überarbeiteten** Modell im Feature-Doc
  > (Mehrquellen-*Beobachtungen* + Hybrid-Ableitung mit Untergrenzen, Parallelspuren PF /
  > parl. Befassung, Lebenszyklus-Overlay, Unterprojekt-Spanne, Dokument-Verknüpfung) statt der
  > einfacheren Timeline-Skizze in der Phasenliste unten. **Phasen 1–4 sind implementiert**
  > (Issues #41/#43/#44/#45): Tabellen/Enums, CRUD, GET/PATCH/Observation-/Dokument-Endpoints,
  > Permission `progress.edit`, Ableitungs-Service und „Planungsstand"-Block in ProjectDetail
  > (Phase 1); VIB/FinVe-Materialisierung mit Lazy-Resync (Phase 2); Prognose-Panel aus
  > BVWP-Dauern + VIB-PFA-Terminen + Fulda-Beobachtungen (Phase 3); reichere manuelle Erfassung
  > mit Quellentyp + Vertrauen (Phase 4). Offen bleiben nur **automatische** externe Importer
  > (keine APIs vorhanden). Die Phasenliste unten beschreibt die ältere Timeline-Skizze.

  **Phase 1 — Foundation (Daten + API)**
  - [ ] Enum `ProjectProgressStatus` (`vorplanung`, `entwurfsplanung`, `genehmigungsplanung`, `ausfuehrungsplanung`, `bau`, `inbetriebnahme`, `abgeschlossen`) — als Python-Enum **und** Postgres-Check-Constraint, damit die Anzeige konsistent bleibt.
  - [ ] Tabelle `project_progress` (id, project_id, status, date, source, comment, created_at, created_by_user_id) + Alembic-Migration.
  - [ ] Schemas `ProjectProgressCreate` / `ProjectProgressRead`; CRUD `crud/project_progress.py`.
  - [ ] Endpoints unter `api/v1/endpoints/project_progress.py`: `GET /projects/{id}/progress` (public), `POST /projects/{id}/progress` (editor/admin), `DELETE /projects/{id}/progress/{entry_id}` (editor/admin). `make gen-api` nach Fertigstellung.
  - [ ] Akzeptanzkriterium: API-Tests (`apps/backend/tests/api/test_project_progress.py`) für Create/Read/Delete + Rollen-Check.

  **Phase 2 — Detail-View: Timeline pro Projekt**
  - [ ] `features/projects/components/ProjectProgressSection.tsx` — Mantine-`Timeline` mit chronologischer Sortierung; pro Eintrag: Status-Badge, Datum, Quelle (`vib_2024`, `manual`, …) als sekundäres Tag, Kommentar als Fließtext.
  - [ ] Inline-Formular zum Anlegen (Mantine-Form, Date-Picker, Status-Select, Quelle = `manual` automatisch); nur für editor/admin sichtbar.
  - [ ] Lösch-Button pro Eintrag (editor/admin), mit Confirm-Modal.
  - [ ] Akzeptanzkriterium: ProjectDetail zeigt für ein Projekt mit ≥2 Einträgen aus verschiedenen Quellen eine korrekt sortierte Timeline; Anlegen + Löschen funktioniert.

  **Phase 3 — Aktueller Phasen-Status auf Projekt-Ebene**
  - [ ] Helper `compute_current_phase(project_id)` (Backend-Side, in `crud/project_progress.py`) — gibt jüngsten Eintrag oder `None` zurück. Verwendung: in `ProjectListItemSchema` als optionales Feld `current_phase: ProjectProgressStatus | None` mitliefern.
  - [ ] Performance: in der Listen-API per `joinedload` / Aggregat-Subquery laden, **nicht** N+1.
  - [ ] Frontend: Phase-Badge in `ProjectCard` (Liste + Karten-Popup) und ProjectDetail-Header. Farbschema in `tokens.css`: Vorplanung=neutral, Bau=Gold (Direction-F-Akzent), Inbetriebnahme=Preußenblau, abgeschlossen=grün.
  - [ ] Akzeptanzkriterium: Listenansicht mit 800+ Projekten lädt in <500 ms (kein N+1 in `pg_stat_statements` sichtbar).

  **Phase 4 — Filterung & Übersicht**
  - [ ] Filter-Chip "Phase" auf `/` (Karten- und Listenansicht); URL-Param `?phase=bau`. Mehrfach-Auswahl möglich.
  - [ ] In `ProjectGroup` neues Feld `default_phase_filter` (optional) — z. B. eine Gruppe "Im Bau" preselektiert `phase=bau`. Migration + Admin-UI.
  - [ ] Akzeptanzkriterium: `?phase=bau` zeigt nur Projekte mit `current_phase=bau`; Phase-Chip ist mit ProjectGroup-Wechsel kompatibel.

  **Phase 5 — Aggregation auf Parent-Projekte**
  - [ ] Für übergeordnete Projekte (mit `subprojects`): Phasen-Verteilung der direkten Kinder berechnen und als Mini-Stacked-Bar in der ProjectCard anzeigen ("3 Bau · 1 Planung · 1 Inbetrieb"). Read-only, keine eigene DB-Spalte.
  - [ ] Akzeptanzkriterium: ein Parent-Projekt mit 5 Sub-Projekten in unterschiedlichen Phasen zeigt den korrekten Stacked-Bar; Klick auf Segment filtert die Sub-Projekt-Liste.

  **Phase 6 — Auto-Extraktion aus VIB**
  - [ ] In `tasks/vib_ai_extraction.py` zusätzlich `planungsstand` → `ProjectProgressStatus` mappen (LLM-Output normalisieren). Beim Confirm eines VIB-Imports: pro zugeordnetem Projekt einen Eintrag mit `source="vib_{year}"` erzeugen, **nur wenn nicht bereits identischer Status+Quelle+Datum vorhanden** (Idempotenz).
  - [ ] Akzeptanzkriterium: erneuter VIB-Import desselben Berichts erzeugt keine Duplikate; ein neuer Bericht mit anderem Planungsstand erzeugt einen zusätzlichen Timeline-Eintrag.

  **Out-of-Scope für v0.0.5:**
  - Auto-Extraktion aus Pressemitteilungen (eigenes Feature, Long-Term).
  - Gantt-Übersicht über mehrere Projekte (eigenes Feature, Long-Term).
  - Konfliktauflösung / Deduplizierung zwischen Quellen — alle Einträge bleiben vorerst sichtbar.

- [x] **Add stations to GeoJSON beim Routenakzeptieren** — *Priorität: mittel*
  `RouteCalculatorForm.onResult` reicht jetzt die Start/Via/End-Stationen ans `GeometryManagementModal` mit. `buildNewGeometry` packt sie als Point-Features in die FeatureCollection — dedupliziert per `op.id` gegen die manuell über „Betriebsstellen hinzufügen" gewählten Punkte, sodass dieselbe OP nicht zweimal landet. Properties: `name`, `op_id`, `feature_type: "operational_point"`.

- [x] **Selective GeoJSON object removal** — *Priorität: niedrig*
  Im Geometrie-Management neuer Toggle „Einzelne Features auswählen & löschen". Aktiv → existing-line/existing-points-circle-Layer reagieren auf Klicks; ausgewählte Features werden via maplibre-`case`-Paint-Expression rot eingefärbt (statt blau). Selection-State lebt im Modal (`Set<number>` der Feature-Indizes aus der ursprünglichen FeatureCollection). „Auswahl löschen"-Button rebuildet die FC ohne die selektierten Indizes und PATCHt sie via `useUpdateProjectGeometry` (oder löscht die Geometrie ganz, wenn nichts übrig bleibt). Dedupliziert nicht mit „Bestehende Geometrie löschen" — die beiden Toggles sind gegenseitig disabled.

### Out-of-Scope für v0.0.5 (bewusst auf später)

- BVWP-Datenimport (zu groß)
- VIB-OCR-Bilder im Review (eigener Long-Term-Block)
- Passwort-Reset per E-Mail (eigener Block)
- ProjectProgress: Pressemitteilungs-Auto-Extraktion + Gantt-Übersicht (Long-Term)

---

## Mid-Term Features

### Vervollständigung und Automatisierung Tests

**Status:** API- und Unit-Tests implementiert (Steps 1–4 abgeschlossen). CI-Automatisierung offen.
- [x] Backend conftest erweitert (`AppSettings`, `ProjectTextType`, `ProjectText`)
- [x] API-Tests: `test_projects.py`, `test_auth.py`, `test_finves.py`, `test_project_texts.py`, `test_settings.py`
- [x] Unit-Tests: `test_finve_matching.py` (Fuzzy-Matching), `test_file_storage.py` (Path-Traversal, MIME)
- [x] Frontend: `@testing-library/react` Setup + Tests für `projectFeatureConfig` und `useAuth` (17 Tests)
- [ ] `tests/unit/test_haushalt_parser.py` — Parser-Fixture-Tests *(aufwändig, späteres Ticket)*
- CI-Automatisierung: nach Long-Term verschoben (siehe Long-Term → **CI: Tests in GitHub Actions**)

- [ ] **Special view of Generalsanierung. Timeline when which Generalsanierung is started and when it is finished**

---

### ✅ Routenvorschlag per GrassHopper *(Backend + Frontend)*

Vollständig implementiert. Backend-Infrastruktur (GraphHopper HTTP client, RouteService, Endpoints, ORM, CRUD, Tests, Docker) und Frontend-Workflow ("Geometrie verwalten" Modal in ProjectDetail) sind abgeschlossen.

**Prerequisite (human task):** OSM-PBF unter `data/graphhopper/map.osm.pbf` ablegen.

#### Open Routing Tasks
- [x] **Add stations to GeoJSON** — When a route is confirmed, add the start/via/end stations as GeoJSON Point features to the geometry, consistent with how other points are already stored. *(done 2026-05-21; siehe v0.0.5-Eintrag oben)*
- [x] **Selective GeoJSON object removal** — In the geometry management UI, let the user select individual GeoJSON features (e.g. segments or points) and remove only those, instead of deleting the entire geometry. *(done 2026-05-21; siehe v0.0.5-Eintrag oben)*
- [x] **Parent GeoJSON auto-merge** — When a sub-project's `geojson_representation` changes, automatically recompute all ancestor projects' geometry as a FeatureCollection of their children's features (arbitrary depth, synchronous, no migration needed). See: `docs/features/feature-parent-geojson-merge.md`
- [x] **Manuelle Geometrie zeichnen** — Linien und Punkte direkt auf der Karte zeichnen (Neubaustrecken, Tram/U-Bahn ohne routbaren Pfad). `GeometryPreviewMap` integriert `terra-draw` (+ `terra-draw-maplibre-gl-adapter`); der geteilte `GeometryEditor` bietet „Linie zeichnen / Punkt setzen / Bearbeiten / Fertig". Gezeichnetes wird gemischt oder ersetzt die bestehende Geometrie und über `useUpdateProjectGeometry` gespeichert. Reines Frontend, keine Backend-Änderung. See: `docs/features/feature-manual-geometry.md` (Issue #27)

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

- [x] **Neues Projekt aus Zuordnungsseite anlegen** — "Neues Projekt anlegen"-Button auf `/admin/unassigned` öffnet den Wizard.

### Neues Projekt anlegen *(Backend + Frontend)*

- [x] 5-step wizard at `/admin/projects/new`: Stammdaten → Geometrie → Projekteigenschaften → FinVes → VIB. Step 1 is required; steps 2–5 are skippable. Uses `POST /api/v1/projects`, `POST /projects/{id}/finves`, `GET /import/vib/entries`, and the extracted `ProjectEditFields`.

Siehe: `docs/features/feature-new-project-wizard.md`

### Sonstiges

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

- [ ] **VIB/Haushalt-Matching: Lernen aus manuellen Zuordnungen**
  Der aktuelle Fuzzy-Matching-Algorithmus (`vib_matching.py`, `finve_matching.py`) berechnet Vorschläge einmalig beim Import und hat kein Gedächtnis. Bestätigte Zuordnungen aus vergangenen Importen (Tabellen `vib_entry_project`, `finve_to_project`) könnten als Trainingsgrundlage dienen: Wenn ein Vorhaben-/FinVe-Name bereits früher manuell einem Projekt zugeordnet wurde, sollte diese Entscheidung als starker Hinweis in zukünftigen Importen gewertet werden. Mögliche Ansätze: (a) Exact-/Near-Match gegen historische `(name_raw, project_id)`-Paare vor dem Fuzzy-Scoring; (b) Boost des Fuzzy-Scores für Projekte, die für ähnliche Namen bereits gewählt wurden. Kein Modell-Training nötig — reine Datenbankabfrage zur Parse-Zeit.

- [ ] **CI: Tests in GitHub Actions** *(aus v0.0.5 hierher verschoben)*
  `pytest` (Backend) + `pnpm test` (Frontend) als GitHub-Actions-Steps; Coverage-Report als Artifact. Trigger: Push auf `master` und Pull-Requests. Backend-Job startet einen Postgres-Service-Container; Frontend-Job führt `pnpm install --frozen-lockfile && pnpm test`. Akzeptanzkriterium: roter CI-Status bei fehlschlagenden Tests blockiert Merge in `master`.

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

### Aufgaben (To-Dos)

Leichtgewichtiges Aufgaben-System für angemeldete Nutzer, um die wiederkehrende Überarbeitung von Projekten zu koordinieren.

Siehe: `docs/features/feature-tasks.md`

- [x] Backend: Tabellen `todo` / `todo_assignee` (m:n), Enums `TodoStatus`/`TodoPriority`, CRUD, Endpunkte `/api/v1/todos` (GET login-gated, Mutationen via `todo.create`/`todo.edit`/`todo.delete`), Helfer `GET /users/options`
- [x] Capabilities `todo.create`/`todo.edit`/`todo.delete` (Gruppe „Aufgaben"), in editor-Systemrolle geseedet (Migration `e4a1b2c3d5f6`)
- [x] Frontend: zentrale Seite `/tasks` (Spalten Offen/In Arbeit/Erledigt, Schnell-Erfassung, Filter), Edit-Drawer, Aufgaben-Sektion auf der Projektdetailseite; Nav-Link „Aufgaben" (login-gated)
- [x] Optionaler Projektbezug (`project_id` nullable, `ON DELETE SET NULL`), Mehrfachzuweisung, Priorität + Fälligkeit (überfällig hervorgehoben)

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

### Rebrand · Richtung F (Bahnhofshalle Tag)

Brand-Wechsel weg vom FAZ-/Chronicle-Editorial hin zum Bahnsteig-Tafel-Idiom: warmweiße Flächen, Anthrazit, **Gold (#c98a00)** als Akzent, **Preußenblau (#0f2347)** als Gewicht, Archivo Narrow + IBM Plex Sans/Mono, scharfe Kanten, kein globaler Dark-Mode (dunkle Flächen nur in der `Tafel`-Komponentenfamilie). Ausgeliefert in v0.0.4.

Quelle: `docs/DESIGN.md` (am 2026-04-25 auf Richtung F neu geschrieben). Vollständiger Plan: `docs/features/feature-rebrand-direction-f.md`.

- [x] **Phase 1 — Foundations**: Archivo Narrow + IBM Plex Sans/Mono via Google Fonts, `tokens.css` neu geschrieben, `theme.ts` auf `preussen` als primary umgestellt.
- [x] **Phase 2 — Chronicle-Komponenten umbauen**: `ChronicleHeadline`/`Card`/`Button`/`DataChip` an F angepasst (Public Props erhalten).
- [x] **Phase 3 — Tafel-Familie neu**: `apps/frontend/src/components/tafel/` mit `Wordmark`, `Signet`, `MiniBoard`, `FlapDigit`, `Ticker`, `KpiCard`, `SectionHead`, `Eyebrow`. Header trägt Wordmark + Signet.
- [x] **Phase 4 — Sweep**: Noto Serif + Work Sans entfernt; alle alten `--c-*`-Tokens, `petrol`, `Schienengrün`-Referenzen aus Source eliminiert. Abmelden-Kontrast durch neue Token-Logik (Anthrazit auf Weiß) gelöst.
- [x] **Phase 5 — Visual QA**: Review-Checkliste neu geschrieben (`docs/review-checklist.md`); Klick-Pfade aller Top-Level-Routen am 2026-04-26 manuell verifiziert.

### UI / UX
- [x] **Chronicle design system — full rollout** — Tokens at `:root` (global); Mantine `defaultRadius: "xs"`; dark header bar; `ChronicleHeadline`/`ChronicleCard`/`ChronicleDataChip`/`ChronicleButton` applied to all pages. See `docs/features/feature-design-system.md` *(superseded by Direction F)*
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
