# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.

> **Steuerung läuft über das GitHub-Projects-Board** (`docs/github-projects.md`),
> nicht über diese Datei. Diese Roadmap ist eine Lese-Übersicht; verbindliche
> Reihenfolge und Status stehen im Board. Lose Ideen → `docs/user-backlog.md`.

---

## Short-Term Features

- [x] integrate the new design described in `docs/DESIGN.md`
- [x] **Smartphone-Tauglichkeit** — die ganze Anwendung ist auf Bildschirmen ab 360 px bedienbar:
  geteilte Breakpoints + Layout-Tokens, Burger-Navigation ab 62em, Karte im Vollbild mit
  Bottom-Sheet für Filter/Ebenen, Tabellen scrollen in ihrer Karte statt die Seite zu verbreitern,
  Dialoge und Seitenleisten in voller Breite. See: `docs/features/feature-mobile-usability.md`
- [ ] **IDT-Design** — Umstellung des Dashboards auf das Design der Initiative Deutschlandtakt
  (Design-System-Tokens, Anwendungsebene des Studios, Inter, Lucide, optionale Dunkelfassung,
  Kopf mit Bildmarke, Fußzeile mit Impressum/Datenschutz, Register auf der Projektseite); löst
  Richtung F vollständig ab. Vier Stufen als Issues: Fundament · Shell und Zustände ·
  Farbzuordnungen, Diagramme, Karte · Bausteine und Sweep. Stufen 1–4 umgesetzt; offen: Abnahme sowie
  Folgearbeiten (Seitenlayouts, dunkle BKG-Kacheln, Vektorlogo, Impressum-/Datenschutztexte als Human Task).
  See: `docs/features/feature-idt-design.md`
  - [x] **IDT-Design Stufe 1** — Tokens, Schrift, Theme, Dunkelfassung, Icons
  - [x] **IDT-Design Stufe 2** — Kopf, Fuß, Impressum/Datenschutz, Register, Zustände
  - [x] **IDT-Design Stufe 3** — Farbzuordnungen, Diagramme, Karte
  - [x] **IDT-Design Stufe 4** — Bausteine nach Anwendungsebene, Chronicle löschen, Sweep

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
  > mit Quellentyp + Vertrauen (Phase 4). Die Phasenliste unten beschreibt die ältere Timeline-Skizze.
  >
  > **Nachgezogen in v0.0.5 (2026-06-27):** die drei **automatischen Quellen-Importer**
  > (Issues #46/#47/#48) — Akquise/Format inzwischen geklärt:
  > - **DB-Bauportal (#47):** offene JSON-API `GET bauprojekte.deutschebahn.com/api/getProjectsList`
  >   (Status via `icon_title`, Bauzeitraum via `projecttime`), Fuzzy-Match auf `shorttitle`. Trust 0.8.
  > - **Fulda-Runde (#46):** Kleine Anfragen (PDF) → OCR+LLM (VIB-Pipeline wiederverwenden),
  >   Lph→Phase-Mapping wie Sammel-FinVe. Trust 0.7. **Abgelöst 2026-10-17** durch MCP + Skill,
  >   Trust 0.55, Ist/Prognose getrennt — siehe `docs/features/feature-fulda-import.md`.
  > - **Medien/Presse (#48):** halb-automatisch — URL/Text → LLM-Extraktion → Mensch-im-Loop. Trust 0.4.
  >
  > **Listen-/Karten-Integration umgesetzt (#9/#10):** die schlanke Projektgruppen-Liste liefert
  > pro Projekt `headline_phase` + `lifecycle_status` aus der gespeicherten `project_progress`-Zeile
  > (gebündelt geladen, ohne Lazy-Resync); auf `/` gibt es für Karte und Liste den Filter
  > „Planungsphase" (`?phase=BAU,…`, inkl. „Unbekannt") und in der Listenansicht einen
  > Phasen-Badge je Projektkarte. Zurückgestellt: `ProjectGroup.default_phase_filter`.
  > Details: `docs/features/feature-project-progress.md` → *Liste & Karte*.

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
  - [x] Performance: in der Listen-API gebündelt laden, **nicht** N+1 — umgesetzt als `selectinload` der gespeicherten `project_progress`-Zeile (#9).
  - [x] Frontend: Phase-Badge in `ProjectCard` der Listenansicht (#10; Karten-Popup zeigt bereits `ProgressMini`, Palette aus `phaseMeta.ts` statt eigener Tokens). Ursprüngliche Skizze: Phase-Badge in `ProjectCard` (Liste + Karten-Popup) und ProjectDetail-Header. Farbschema in `tokens.css`: Vorplanung=neutral, Bau=Gold (Direction-F-Akzent), Inbetriebnahme=Preußenblau, abgeschlossen=grün.
  - [ ] Akzeptanzkriterium: Listenansicht mit 800+ Projekten lädt in <500 ms (kein N+1 in `pg_stat_statements` sichtbar).

  **Phase 4 — Filterung & Übersicht**
  - [x] Filter "Planungsphase" auf `/` (Karten- und Listenansicht); URL-Param `?phase=BAU,…` inkl. `UNBEKANNT`. Mehrfach-Auswahl möglich (#10).
  - [ ] *(zurückgestellt)* In `ProjectGroup` neues Feld `default_phase_filter` (optional) — z. B. eine Gruppe "Im Bau" preselektiert `phase=bau`. Migration + Admin-UI.
  - [ ] Akzeptanzkriterium: `?phase=bau` zeigt nur Projekte mit `current_phase=bau`; Phase-Chip ist mit ProjectGroup-Wechsel kompatibel.

  **Phase 5 — Aggregation auf Parent-Projekte**
  - [ ] Für übergeordnete Projekte (mit `subprojects`): Phasen-Verteilung der direkten Kinder berechnen und als Mini-Stacked-Bar in der ProjectCard anzeigen ("3 Bau · 1 Planung · 1 Inbetrieb"). Read-only, keine eigene DB-Spalte.
  - [ ] Akzeptanzkriterium: ein Parent-Projekt mit 5 Sub-Projekten in unterschiedlichen Phasen zeigt den korrekten Stacked-Bar; Klick auf Segment filtert die Sub-Projekt-Liste.

  **Phase 6 — Auto-Extraktion aus VIB** — entfällt (2026-10-20): bestätigte VIB-Einträge materialisieren bereits als abgeleitete Beobachtungen; siehe `feature-vib-import.md` → Phase 7.

  **Out-of-Scope für v0.0.5:**
  - Auto-Extraktion aus Pressemitteilungen (eigenes Feature, Long-Term).
  - Gantt-Übersicht über mehrere Projekte (eigenes Feature, Long-Term).
  - Deduplizierung zwischen Quellen — alle Einträge bleiben sichtbar. (Konfliktauflösung der
    Headline-Phase ist seit 2026-10-22 umgesetzt: neuester Bericht gewinnt, Rückstufungen als
    Konflikt unter Admin → „Planungsstand-Konflikte“, `feature-project-progress.md`.)

- [x] **Add stations to GeoJSON beim Routenakzeptieren** — *Priorität: mittel*
  `RouteCalculatorForm.onResult` reicht jetzt die Start/Via/End-Stationen ans `GeometryManagementModal` mit. `buildNewGeometry` packt sie als Point-Features in die FeatureCollection — dedupliziert per `op.id` gegen die manuell über „Betriebsstellen hinzufügen" gewählten Punkte, sodass dieselbe OP nicht zweimal landet. Properties: `name`, `op_id`, `feature_type: "operational_point"`.

- [x] **Selective GeoJSON object removal** — *Priorität: niedrig*
  Im Geometrie-Management neuer Toggle „Einzelne Features auswählen & löschen". Aktiv → existing-line/existing-points-circle-Layer reagieren auf Klicks; ausgewählte Features werden via maplibre-`case`-Paint-Expression rot eingefärbt (statt blau). Selection-State lebt im Modal (`Set<number>` der Feature-Indizes aus der ursprünglichen FeatureCollection). „Auswahl löschen"-Button rebuildet die FC ohne die selektierten Indizes und PATCHt sie via `useUpdateProjectGeometry` (oder löscht die Geometrie ganz, wenn nichts übrig bleibt). Dedupliziert nicht mit „Bestehende Geometrie löschen" — die beiden Toggles sind gegenseitig disabled.

### Out-of-Scope für v0.0.5 (bewusst auf später)

- BVWP-Datenimport (zu groß)
- ~~VIB-OCR-Bilder im Review~~ — entfällt (2026-10-20, VIB über MCP + Skill)
- Passwort-Reset per E-Mail (eigener Block)
- ~~ProjectProgress: Gantt-Übersicht über mehrere Projekte (Long-Term)~~ — umgesetzt als
  Zeitstrahl-Ansicht, siehe `docs/features/feature-project-timeline.md`
  - *Hinweis: die automatischen Quellen-Importer (Fulda-Runde/Bauportal/Medien) wurden am
    2026-06-27 in den v0.0.5-Scope nachgezogen — siehe oben.*

---

## Wahlkreise und Abgeordnete auf Projekten

Verschneidung der Projektgeometrien mit den 299 Bundestagswahlkreisen, dazu die
zuständigen Abgeordneten aus der abgeordnetenwatch-API. Beantwortet vor jedem Gespräch
dieselbe Frage: Was verbindet diese Abgeordnete konkret mit diesem Vorhaben?

Siehe: `docs/features/feature-abgeordnete.md`. Issue-Codes: „Abgeordnete Phase 1–5".

- [x] **Phase 1 — Datenmodell + Import**: `parliament_period`, `constituency` (MULTIPOLYGON
  + GiST), `politician`, `mandate`, `committee`, `committee_membership`,
  `parliament_import_run`; Geometrie-Import als Skript, Abgeordneten-Import als
  Celery-Task (idempotent); Recht `parliament.import`.
- [x] **Phase 2 — Verschneidung**: `project_to_constituency` mit Kilometern, Anteil und
  Überlappungsart; `ST_Intersection` auf `geography`, gepflegt an der Geojson-Kaskade;
  vollständiger Neuaufbau als Task.
- [x] **Phase 3 — Projektdetail**: Block „Wahlkreise und Abgeordnete", Direktmandat
  sichtbar abgesetzt von „über Liste, hier angetreten".
- [x] **Phase 4 — Seite `/abgeordnete`**: Namenssuche, Ausschuss- und Fraktionsfilter,
  Projekte je Person nach Kilometern.
- [x] **Phase 5 — Kartenlayer**: zuschaltbare Wahlkreisgrenzen, Auswahl zeigt Projekte
  und Abgeordnete.
- [ ] **Erstbefüllung** (human task): Wahlkreis-GeoJSON beschaffen und importieren,
  danach den Abgeordnetenstand einmal ziehen.

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
- [x] **Geometrie-Modus für Überprojekte** — Ein Projekt mit Unterprojekten wählt über den Kippschalter „Geometrie automatisch aus Unterprojekten zusammensetzen" (`project.geojson_from_subprojects`, Default `true`), ob seine Kartengeometrie aus den Unterprojekten aggregiert oder selbst gepflegt wird. Im Selbst-Modus stoppt die Aufwärts-Kaskade an dem Projekt; das direkte Schreiben der Geometrie im Automatik-Modus lehnt die API mit HTTP 400 ab. See: `docs/features/feature-parent-geometry-mode.md`
- [x] **Manuelle Geometrie zeichnen** — Linien und Punkte direkt auf der Karte zeichnen (Neubaustrecken, Tram/U-Bahn ohne routbaren Pfad). `GeometryPreviewMap` integriert `terra-draw` (+ `terra-draw-maplibre-gl-adapter`); der geteilte `GeometryEditor` bietet „Linie zeichnen / Punkt setzen / Bearbeiten / Fertig". Gezeichnetes wird gemischt oder ersetzt die bestehende Geometrie und über `useUpdateProjectGeometry` gespeichert. Reines Frontend, keine Backend-Änderung. See: `docs/features/feature-manual-geometry.md` (Issue #27)
- [x] **Bestehende Geometrie bearbeiten** — Schalter „Bestehende Geometrie bearbeiten" lädt die gespeicherten Linien/Punkte in terra-draw: Stützpunkte verschieben, Zwischenpunkte einfügen, Stützpunkte löschen; nur geänderte Teile werden zurückgeschrieben, Properties bleiben erhalten. See: `docs/features/feature-manual-geometry.md` → „Erweiterung"

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
  Zusätzlich hat jede Zeile (FinVe, VIB, GVFG) den Link „Projekt fehlt?“: legt das Projekt als Entwurf an und weist den Eintrag direkt zu — wie in den Import-Reviews.

### Neues Projekt anlegen *(Backend + Frontend)*

- [x] 5-step wizard at `/admin/projects/new`: Stammdaten → Geometrie → Projekteigenschaften → FinVes → VIB. Step 1 is required; steps 2–5 are skippable. Uses `POST /api/v1/projects`, `POST /projects/{id}/finves`, `GET /import/vib/entries`, and the extracted `ProjectEditFields`.

Siehe: `docs/features/feature-new-project-wizard.md`

### MCP-Server & API-Keys *(Backend + Frontend)*

- [x] **API-Keys als Auth-Weg** — persönliche Bearer-Tokens neben Session-Cookie und HTTP Basic, mit Widerruf, Ablauf und optionaler Rechte-Einschränkung pro Key. Eigenständig nützlich, Voraussetzung für den MCP-Server.

- [x] **MCP-Server** — Streamable-HTTP-Endpunkt `/mcp` im Backend, der Projekte, Finanzierung und Planungsstand als MCP-Tools für KI-Assistenten bereitstellt. Rechte kommen aus dem bestehenden Capability-Katalog; Importe dürfen seit 2026-10-17 eigene Tools bekommen (Fulda-Runde, Infraplan). OAuth folgt erst mit dem Authentik-Umzug, die Key-Auth bleibt danach bestehen. Zugriff vorerst nur für Admins (`mcp.access`), Keys laufen nach 90 Tagen ab. Geometrie-Tools inkl. GraphHopper-Routing und Zeichnen aus Koordinaten ergänzt. FinVe frei suchbar (`list_finves`, `get_finve`), auch ohne Projektzuordnung; falsche FinVe-Zuordnungen lassen sich mit `unlink_finve` lösen. Skills kommen vom Server (`list_skills`, `get_skill`) — immer passend zum deployten Stand; in claude.ai liegt nur der Einstiegs-Skill `schienendashboard`.
  Siehe: `docs/features/feature-mcp-server.md`

- [x] **Projekte zusammenführen** — MCP-Tool `merge_projects` und `POST /projects/merge`: Dublette in das bleibende Projekt überführen (Verknüpfungen, Historie, Unterprojekte), alte id leitet um. Vorstufe zur GVFG-Datenpflege.
  Siehe: `docs/features/feature-project-merge.md`
- [x] **Projekte archivieren** — eigenes Kennzeichen „Archiviert“ mit Pflicht-Begründung für ersetzte/überholte Projekte: zählt nirgends mehr (Listen, Karte, Summen, Eltern-Aggregation), bleibt per URL erreichbar, Admin-Seite „Archiv“, MCP `archive_project`/`unarchive_project`.
  Siehe: `docs/features/feature-project-archive.md`

### GVFG-Bundesprogramm *(Backend + Frontend)*

- [x] **GVFG-Import (Etappe 1)** — Parser, Datenmodell, Import mit Review unter `/admin/gvfg-import`, Lese-API.
- [x] **GVFG-Anzeige** — Menü „Finanzen“ mit „Bedarfsplan Schiene“ und „GVFG“, Übersicht `/finanzen/gvfg`, Abschnitt „GVFG“ auf der Projektseite (inkl. Teilprojekte), offene Zuordnungen im Admin.
- [x] **GVFG-MCP-Tools** — `list_gvfg_programs`, `list_gvfg_entries`, `get_gvfg_entry` (Verlauf über die Ausgaben), `list_project_gvfg` und das Zuordnungs-Tool `assign_gvfg_entry`.
- [x] **GVFG als Planungsstand-Quelle** — Die neueste GVFG-Ausgabe liefert Lph, Baubeginn und Inbetriebnahme als Quelle `GVFG` in Planungsstand und Prognose; ein jüngerer Infraplan-Eintrag gewinnt. Siehe `docs/features/feature-project-progress.md` → „Planungsstand aus dem GVFG-Bundesprogramm“.
- [ ] **GVFG-Vergleich** — Reiter „Änderungen zur Vorausgabe“. Vorher Dubletten im GVFG-Bestand bereinigen.
  Siehe: `docs/features/feature-gvfg-import.md`

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

- ~~**VIB-Review: Original-PDF-Anzeige**~~ — entfällt (2026-10-20): Der empfohlene Weg ist das Einlesen über MCP + Skill, der Agent liest das PDF selbst (`feature-vib-import.md` → Phase 7). Bisheriger Plan: Im Review-Schritt das hochgeladene PDF parallel zum Formular anzeigen, auf die passende Seite gesprungen. Erfordert: PDF-Speicherung serverseitig (z.B. temporär an draft_id geknüpft), Seitennummer-Tracking im Parser (pro Eintrag), Serve-Endpoint `GET /import/vib/pdf/{task_id}`, Frontend-Integration mit `react-pdf` oder ähnlichem.

- ~~**VIB-Review: OCR-Bilder anzeigen**~~ — entfällt (2026-10-20, siehe oben). Bisheriger Plan: Im Review und in `VibStructurePreviewPage` extrahierte Mistral-OCR-Bilder (Diagramme, Karten, Fortschrittsbalken) pro Vorhaben anzeigen. Backend-Infrastruktur bereits implementiert: `ocr_images_json` auf `VibDraftReport`, `GET /draft/{task_id}/images` (Metadaten) und `GET /draft/{task_id}/image/{id}` (Bytes). Offen: pro-Eintrag-Zuordnung der Bilder (page_index-Matching gegen entry block_start/end-Seiten) und Frontend-Komponente (Galerie oder Inline-Thumbnails in der Strukturvorschau).

- [ ] **PDF-Import vereinheitlichen** — Die OCR-Stufe der VIB-Pipeline (PDF → Markdown, dann Zuordnung aufs Zielformat) als gemeinsamen Service für alle PDF-Quellen bereitstellen; Haushalt-Spaltenlayout per LLM auf das kanonische Schema mappen statt pro Jahrgang neue Heuristiken. Evaluation und empfohlene Reihenfolge: `docs/features/feature-pdf-import-unification.md`. Umgesetzt: Schritt 1 (`services/document_ocr.py` mit `OcrResult`), Schritt 2 (OCR-Persistenz-Mixin), Schritt 4 (OCR-Pfad des Haushalts parallel über `HAUSHALT_EXTRACTION=compare` inkl. Vergleichsskript) und Schritt 5 (Spaltenzuordnung). Offen: Schritt 3 (Medien-PDF-Upload) und Schritt 6 — die Umschaltung auf `ocr` setzt einen Vergleichslauf gegen die echte OCR-API voraus (`docs/manual-tests-backlog.md`).

- [x] **Fulda-Runde über MCP + Skill** — Antworten der Bundesregierung zur Fulda-Runde liest ein Agent selbst (Skill `.claude/skills/fulda-runde/`) und schreibt sie über MCP-Tools: Dokument mit Antwortstand, feinere Kategorien (Ist / ohne Folgephase / Prognose / Neuaufnahme), Fundstelle und Wortlaut je Eintrag. Ist-Aussagen setzen die Phase, Prognosen nur einen erwarteten Termin; Termine VIB-PFA vs. Fulda nach Glaubwürdigkeit × Aktualität. Trust 0.55, Recht `fulda.import`, OCR+LLM-Upload entfällt.
  Siehe: `docs/features/feature-fulda-import.md`

- [x] **Infraplan-Import** — Jährlicher Import des Infraplans (BMV, Fünfjahresplan Schiene): Maßnahmentabellen aus Kapitel 2.3 (Bedarfsplan Teil A–D, GVFG, InvKG) mit Realisierungsstand, Befassung, geplanter Inbetriebnahme und Gesamtkostenprognose sowie alle Steuerungs- und Informationskennzahlen als Zeitreihe über die Jahrgänge. Zwei Wege mit gleichem Ergebnis: manuell im Frontend oder per MCP + Skill (`.claude/skills/infraplan-import/`). Neue Fortschrittsquelle `INFRAPLAN`, öffentliche Seite `/infraplan`. Stufen: Infraplan – Stufe 1 (Parser + Datenmodell), Stufe 2 (manueller Weg), Stufe 3 (Fortschritt + Kosten), Stufe 4 (Kennzahlen + Seite), Stufe 5 (MCP + Skill). Ausbau für 2027: Sammelaufrufe, kompakte Übersicht, Aliase am Projekt, Kontext- und Vorjahresmatching, Seitentext für Kennzahlen, Prüftool `check_project_data`.
  Siehe: `docs/features/feature-infraplan-import.md`

- [ ] **Netzzustandsbericht** — PDF-Import, Extraktion relevanter Kennzahlen in die Datenbank

- [ ] **Beschleunigungskommission Schiene** — Datentransfer aus öffentlichen Quellen + automatische Updates

- [ ] **RINF-Daten evaluieren** — Für Bahnhofs-/Stationsverbindungen ggf. weiterhin benötigt

- [ ] **GeoLine-Erstellung** — Möglichkeit, neue Streckengeometrien zu erzeugen, wenn vorhandene unvollständig/ungültig sind. Ansatz noch offen (Zeichentool auf Karte vs. automatische Vervollständigung).

- [ ] **Automatisierung Preisniveau** — Tool zum Berechnen von Preisen gemäß Inflation/Baukostenentwicklung auf das aktuelle Jahr

- [ ] **Passwort zurücksetzen per E-Mail** *(Backend + Frontend)*
  Reset-Link per E-Mail, Token-basiert (UUID4, 1h gültig). Admin hinterlegt E-Mail in Benutzerverwaltung.
  Siehe: `docs/features/feature-password-reset.md`

- [ ] **VIB/Haushalt-Matching: Lernen aus manuellen Zuordnungen**
  *VIB: gelöst (2026-10-20) — `add_vib_entries` schlägt zuerst die bestätigte Zuordnung desselben Vorhabens aus früheren Berichten vor (`feature-vib-import.md` → Phase 7). Offen bleibt Haushalt/FinVe.*
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
- [x] Tags (m:n, Tag „@LLM“ für Aufgaben an das LLM), Tag-Filter und Textsuche, eigener Aufgaben-Verlauf; „Tags verwalten“ (umbenennen, beschreiben, löschen), zweites Tag „@Jonas“ für den Teil vor dem LLM; MCP `list_todos` mit `tag`/`search`/`offset`, `list_todo_tags`, `update_todo_tag` (Migration `20261022003`, „@LLM“ aus Titeln ins Tag übernommen)

### Claude Code Setup
- [x] Hooks (pre-edit `.env` guard, post-edit reminders for `make gen-api`, Alembic, roadmap sync, macOS notifications)
- [x] Skills: `/commit`, `/gen-api`, `/update-roadmap`, `/new-api-route`
- [x] Plugins: `feature-dev`, `frontend-design`, `pyright-lsp`, `typescript-lsp`

### Verkehrsinvestitionsbericht (VIB) Import

Jährlicher Import des VIB-PDFs (Abschnitt B: Schienenwege). Vollständig implementiert über Phases 1–4.

Siehe: `docs/features/feature-vib-import.md`

- [x] **Parser** — per-page column detection (bimodal x0), TOC-anchored block boundaries, `_VORHABEN_SECTION_RE` for plain and Markdown headings, PFA pipe-table parsing, debug script `scripts/dump_vib_parse_result.py`
- [x] **Mistral OCR Pipeline** — `services/document_ocr.py` (bis v0.0.12 `tasks/vib_ocr.py`, jetzt gemeinsame Stufe 1 aller PDF-Importe): `mistral-ocr-latest` API + pymupdf fallback; inline table resolution; header/footer stripping; page-range extraction; image collection stored as JSON in `vib_draft_report.ocr_images_json`
- [x] **API** — Celery task `extract_vib_blocks`; image endpoints `GET /draft/{task_id}/images` + `/image/{id}`; single-entry AI extraction endpoint
- [x] **Review-UI** — `VibStructurePreviewPage` with Markdown rendering, quality indicators, sub-section badges; `VibReviewPage` with editable sub-block fields and inline PFA table; per-entry "KI extrahieren" button; m:n project assignment (`project_ids`)
- [ ] **VIB über MCP + Skill (Vorrang vor dem Upload)** — Agent liest den VIB selbst (Skill `.claude/skills/vib-import/`) und schreibt Bericht, Vorhaben, PFA-Tabelle und Zuordnungen mit Begründung über MCP-Tools (Recht `vib.import`); `vib_entry.confirmed` — nur bestätigte Einträge materialisieren; Prüfmodus für vorhandene Jahrgänge; Upload bleibt als zweiter Weg. Siehe `feature-vib-import.md` → Phase 7.
- [x] **VIB-PFA → Teilprojekte** — Vorschlag aus dem ganzen Teilbaum (Vorjahr → Abschnittsnummer → Ortsname, mit Grund), starke Vorschläge per Tool übernehmen, Teilprojekt-Entwürfe je Abschnitt auf Anforderung anlegen. Geometrie-Abgleich vorgemerkt. Siehe `feature-vib-import.md` → Phase 8.

### Rebrand · Richtung F (Bahnhofshalle Tag)

Brand-Wechsel weg vom FAZ-/Chronicle-Editorial hin zum Bahnsteig-Tafel-Idiom: warmweiße Flächen, Anthrazit, **Gold (#c98a00)** als Akzent, **Preußenblau (#0f2347)** als Gewicht, Archivo Narrow + IBM Plex Sans/Mono, scharfe Kanten, kein globaler Dark-Mode (dunkle Flächen nur in der `Tafel`-Komponentenfamilie). Ausgeliefert in v0.0.4.

Quelle: `docs/DESIGN.md` (am 2026-04-25 auf Richtung F neu geschrieben). Vollständiger Plan: `docs/features/feature-rebrand-direction-f.md`.
**Abgelöst am 2026-10-21** durch das IDT-Design (`docs/features/feature-idt-design.md`); `docs/DESIGN.md` beschreibt seitdem das IDT-Design.

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
- [x] Kurzansicht als Hover-Vorschau an allen Projektlinks (`ProjectHoverCard`, nur bei Maus/Trackpad)
- [x] Datum-/Zeitanzeige auf Zeitzone Europe/Berlin; Login per Enter-Taste; Burger-Menü bei schmalen Fenstern
- [x] SV-FinVes in Projektdetailseite als kompakter Tag dargestellt

### Texte & Kommentare
- [x] Projekttexte anzeigen (über übergeordnetes Projekt), erstellen, bearbeiten
- [x] Sichtbarkeit von Texten: eingeloggt-only oder öffentlich (bis 2026-10 nur abgehakt, tatsächlich umgesetzt mit den Textkategorien)
- [x] **Textkategorien** (Info, Warnung, erweiterbar) mit festen Darstellungsstilen — See: docs/features/feature-text-categories.md
- [x] Versionshistorie und Bearbeitungsformular nur für eingeloggte Nutzer sichtbar
- [x] **Dateianhänge an Projekttexten** — Upload, Download, Delete; PDF-Inline-Preview; MIME-Validierung; Path-Traversal-Guard

### Change Tracking (vollständig)
- [x] DB-Modelle `change_log` + `change_log_entry` + Alembic-Migration
- [x] `PATCH /api/v1/projects/{id}` — schreibt ChangeLog-Einträge je geändertem Feld (Rolle: editor/admin)
- [x] `GET /api/v1/projects/{id}/changelog` — öffentlich lesbar
- [x] Bearbeitungsformular in `ProjectDetail` (editor/admin); alle Felder bearbeitbar
- [x] Übergeordnetes Projekt im Bearbeiten-Drawer setzbar (`superior_project_id`) — durchsuchbare Projektauswahl (umlaut-/bindestrich-tolerant, relevanzsortiert), eigener Teilbaum ausgeblendet; Backend lehnt Selbstzuordnung und Zyklen mit HTTP 400 ab und rechnet die Geometrie von altem und neuem Dachprojekt neu
- [x] Abschnitt „Stammbaum" auf der Projektseite (Recht `project.edit`, vor der Versionshistorie): übergeordnete Projekte darüber, Geschwister daneben, der ganze Teilbaum darunter — als eingerückter Baum mit Links, gebaut aus `/projects/options`
- [x] Projekt löschen auf der Detailseite (Recht `project.delete`) mit zweistufiger Bestätigung inkl. Hinweis auf mitgelöschte Unterprojekte
- [x] Versionshistorie-Timeline in `ProjectDetail` (`ProjectHistorySection.tsx`); nur für eingeloggte Nutzer
- [x] „Zurücksetzen"-Button pro `ChangeLogEntry` (editor/admin) via `useRevertProjectField` hook

### Benutzerverwaltung
- [x] Login-UI: httpOnly-Cookie-Session (HMAC-signed), Authorization-Header bei API-Requests, 401/403-Interceptor
- [x] Rollenbasierte Bearbeitung: Schreiboperationen nur für editor/admin sichtbar
- [x] User-Management-Seite `/admin/users` (nur admin): Nutzer anlegen, Rolle/Passwort ändern, löschen

### Haushaltsberichte-Import (vollständig)

Jährlicher Import der Anlage VWIB, Teil B (Bundeshaushalt) als PDF. Enthält alle Bedarfsplanmaßnahmen des Schienenwegeinvestitionsprogramms mit FinVe-Nummern, Kostenschätzungen und Jahresansätzen.

Siehe: `docs/features/feature-haushalt-import.md`

- [x] Celery-Task `parse_haushalt_pdf` (`tasks/haushalt.py`) mit `pdfplumber`; Parser für zusammengeführte Spalten, mehrzeilige Zellen, Haushaltstitel-Lookup auto-erweiterbar via `get_or_create`
- [x] **Spaltenzuordnung statt fester Indizes** (`tasks/haushalt_columns.py`) — die Kopfzeile der Tabelle wird einmal pro Dokument auf das kanonische Schema gemappt (deterministisch, LLM als Rückfallebene, festes 2026-Layout als letzte Stufe); Werte werden immer deterministisch übertragen. Im Review sichtbar
- [x] **Alle fünf Tabellen von Teil B** — Segmentierung über die Seitenüberschrift `Tabelle <N> - <Titel>`; jede Tabelle wird als eigener Abschnitt mit eigener Spaltenzuordnung eingelesen und im Review als eigener Block angezeigt (2027: 83 + 58 Zeilen)
- [x] **Identität ohne FinVe-Nummer** (`finve.finve_key`, `tasks/haushalt_keys.py`) — die Tabellen 2–5 drucken keine FinVe-Nummer; ihre Maßnahmen werden über die Kennung des Berichts (`t2:SV 52/2017`, `t5:B0094`) jahresübergreifend wiedererkannt
- [x] **Zeilen-Rekonstruktion** — auf Seiten ohne waagerechte Trennlinien (ERTMS) baut der Parser die Zeilen aus den Textzeilen neu auf und korrigiert das rechtsbündige Spaltenraster, damit ein „–"-Platzhalter nicht als Vorzeichen der Nachbarspalte gelesen wird
- [x] **Herkunft je Lauf gespeichert** — `haushalts_parse_result.ocr_*` (gemeinsames `OcrSourceMixin`) und `column_map_*`
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
- [x] Performance Karte: schlanke Projektgruppen-Liste, vereinfachte Geometrien je Gruppe nachgeladen, gzip im Backend, ETag — See: docs/features/feature-slim-project-groups.md
