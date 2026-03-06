# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.


---

## Short-Term Features
- [x] Erstelle ein Inhaltsverzeichnis für die Projektdarstellung, das an der linken Seite ausgeklappt werden kann, dadurch ist eine schnellere Orientierung möglich. Bei Elementen die eingeklappt sind, sind diese auszuklappen wenn das Element über das seitliche Inhaltsverzeichnis aufgerufen wird.
- [x] if the window is to small, collaps the header menu to burger menu
- [x] Clean up the docs files. Focus on architecture.md
- [ ] Verstehe wie das neue Plugin feature-dev funktioniert
- [ ] if you load the project view - center the map on the center of the project. There should be a fitting variable in the database of table `project`

### Claude Hooks
- [x] **Pre-edit guard on `.env`** — Hook that warns before any edit to `.env` files (AGENT.md rule: never modify `.env`)
- [x] **Post-edit: `make gen-api` reminder** — After editing backend schemas or endpoints, remind to run `make gen-api` if the OpenAPI contract changed
- [x] **Post-edit: migration reminder** — After editing `apps/backend/dashboard_backend/models/**`, remind to create an Alembic migration
- [ ] **Post-edit: roadmap sync reminder** — After editing features or API endpoints, remind to update `docs/roadmap.md`
- [x] Create a hook that pushes MacBook Reminder if you need something. This is explained here osascript -e 'display notification "Claude Code needs your attention" with title "Claude Code"' https://code.claude.com/docs/en/hooks-guide#get-notified-when-claude-needs-input

### Claude Skills
- [ ] **`/commit`** — Conventional Commit helper: reads staged diff, proposes a commit message in `type(scope): description` format, asks for confirmation
- [x] **`/gen-api`** — Regenerate frontend API client: verifies backend is running, runs `make gen-api`, reports changed files
- [x] **`/update-roadmap`** — Mark a completed feature: finds the matching `[ ]` item in `docs/roadmap.md` and marks it `[x]`. Check if the implemented tasks are documentated. Therefore have in mind that there are different possibilitys for documentation: Root, backend and frontend.
- [ ] **`/new-api-route`** — New backend route scaffold: walks through the checklist (endpoint → schema → CRUD → test → `make gen-api`)

### Other Plugins
- [ ] Install the Plugin for Python for Code Intelligence (https://code.claude.com/docs/en/discover-plugins#code-intelligence). Also for Typescript
- [x] Implement this feature: https://github.com/anthropics/claude-code/tree/main/plugins/feature-dev
- [ ] Implement https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design
  

#### Test develompment 
- [ ] Load of failed development tests
  - Da scheint vor allem erstmal ein Probelm it Routen zu sein -> hier prüfen ob das überhaupt noch aktuell ist

---

## Mid-Term Features




### Haushaltsberichte
- [ ] **Haushaltsberichte Tabelle VE** *(Backend + Frontend)*
  Jährlicher Import der Anlage VWIB, Teil B (Bundeshaushalt) als PDF.
  Die Tabelle enthält alle Bedarfsplanmaßnahmen des Schienenwegeinvestitionsprogramms
  mit FinVe-Nummern, Kostenschätzungen und Jahresansätzen je Haushaltskonto.

  **Zweistufiger Ablauf:**

  1. **Verarbeitung (Parse-Schritt):**
     - `POST /api/v1/import/haushalt/parse` nimmt PDF + Haushaltsjahr entgegen
     - Backend extrahiert Tabellenzeilen (`pdfplumber` / `pymupdf`), trennt
       Hauptzeilen (FinVe-Einträge) von Titelunterzeilen (891 01, 891 52 etc.)
     - Gleicht jede FinVe-Nummer gegen bestehende `Finve`-Einträge in der DB ab:
       - **Vorhanden:** Änderungen werden als Update-Vorschlag markiert
       - **Neu:** FinVe wird als neu zu erstellen markiert; die Projektzuordnung
         (`finve_to_project`) bleibt zunächst leer und muss im Frontend manuell
         hergestellt werden (ein oder mehrere Projekte)
     - Nicht zuordenbare Zeilen (fehlende/unklare FinVe-Nummer) werden als
       `unmatched_rows` zurückgegeben und können im Review-Schritt manuell
       einer bestehenden FinVe zugewiesen werden
     - Für große Dokumente: asynchron via Celery Task Queue, Polling über
       `GET /api/v1/import/haushalt/status/{task_id}`

  2. **Freigabe (Confirm-Schritt):**
     - `POST /api/v1/import/haushalt/confirm` nimmt den (ggf. manuell korrigierten)
       Vorschlag entgegen und schreibt `Finve`- und `Budget`-Einträge transaktional
     - Nur für Rollen `editor` / `admin`
     - Import wird im ChangeLog protokolliert (Nutzer, Zeitstempel, Haushaltsjahr)

  **Frontend:** Review-Seite zeigt Vorschau der Änderungen (neue/geänderte FinVes,
  neue Budget-Zeilen, ungematchte Einträge). Für neue FinVes, die noch keinem Projekt
  zugeordnet sind, bietet die UI eine Auswahl bestehender Projekte an (Mehrfachauswahl).
  Erst nach manueller Prüfung wird Confirm ausgelöst.

  **Abhängigkeiten:** Celery Task Queue (für asynchronen Parse-Schritt),
  ChangeLog-Infrastruktur (für Protokollierung).


### Sonstiges

- [ ] **ProjectProgress** *(Backend + Frontend)*
  Fortschrittsstand eines Projekts (Planungs-, Genehmigungs-, Bauphase). Speist sich aus mehreren Quellen (z. B. Bundestag-Drucksachen, Pressemitteilungen, manuelle Eingabe). Benötigt Validierungslogik für Konflikte zwischen Quellen.
  - Backend: `ProjectProgress`-Modell implementieren (Status, Datum, Quelle, Kommentar)
  - Frontend: Zeitleiste/Meilenstein-Ansicht in `ProjectDetail`
– [ ] **Anzeige der BVWP-Daten** Für einige Projekte liegen BVWP-Daten vor, diese sind vollständig und übersichtlich darzustellen
- [ ] **Anzeige Texte und Kommentare:**
- [ ] **Vervollständigung und Automatisierung Test**

---

## Long-Term Features

- [ ] **Routenvorschlag per GrassHopper** *(Backend + Frontend)*
  Im Backend existiert bereits ein Routing-Microservice (GrassHopper/pgRouting). Ablauf:
  1. Nutzer öffnet ein Projekt und wählt "Route berechnen"
  2. Start- und Endpunkt werden aus bekannten **OperationalPoints** (Dropdown, durchsuchbar) gewählt
  3. Backend berechnet Route und gibt GeoJSON zurück
  4. Frontend zeigt die vorgeschlagene Route als Vorschau auf der Karte an
  5. Nutzer akzeptiert → Route wird als `geojson_representation` des Projekts gespeichert (PATCH)
  6. Nutzer lehnt ab → Vorschau wird verworfen
- [ ] Anzeige der Kommentare sowie 

- [ ] **Netzzustandsbericht** — PDF-Import, Extraktion relevanter Kennzahlen in die Datenbank

- [ ] **Beschleunigungskommission Schiene** — Datentransfer aus öffentlichen Quellen + automatische Updates
- [ ] **BVWP-Datenimport** — Übernahme aus Legacy-Datenbank
- [x] **Backend-Authentifizierung** — HTTP Basic Auth, PBKDF2, Rollen: viewer / editor / admin (Frontend-Integration steht noch aus, siehe Mid-Term)

- [ ] **RINF-Daten evaluieren** — Für Bahnhofs-/Stationsverbindungen ggf. weiterhin benötigt
- [ ] **GeoLine-Erstellung** — Möglichkeit, neue Streckengeometrien zu erzeugen, wenn vorhandene unvollständig/ungültig sind. Ansatz noch offen (Zeichentool auf Karte vs. automatische Vervollständigung).
- [ ] **Automatisierung Preisniveau** Ein Tool das ermöglicht, Preise gemäß der Inflation/Baukostenentwicklung auf das aktuelle Jahr zu berechnen und so die Vergleichbarkeit zu verbessern


- [ ] **Passwort zurücksetzen per E-Mail** *(Backend + Frontend)*
  Abhängigkeit: Schritt 1 abgeschlossen.
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
- **project data** — primäres Transferziel
- **finve and budgets** — aus Originalquellen neu aufbauen
- **bks** — niedrige Priorität
- **infrastructure data** — wird nicht übertragen
- **d-takt data** — ignoriert
- **texts** — kein Transfer

---

## Finished

- [x] Dicke der Linien auf Karte einstellbar, standardmäßig dicker (4 px)
- [x] Größe der Punkte auf Karte einstellbar
- [x] In Projektansicht Button "Zur Karte" neben "Zur Projektübersicht"
- [x] Lücken zwischen Liniensegmenten behoben (MultiLineString + `line-cap: round`)
- [x] Punkte aus GeoJSON auf Karte dargestellt (separater Circle-Layer)
- [x] Gruppen-Persistenz über URL-Params beim Wechsel zwischen Karte und Projektliste
- [x] Backend-Authentifizierung (HTTP Basic Auth, PBKDF2, Rollen: viewer / editor / admin)
- [x] Routing-Algorithmus implementiert (pgRouting / GrassHopper-Microservice)
- [x] Stelle sicher, dass properties of project im Browser bei den Projekten angezeigt werden. Aktuell ist das nur für ausgewählte der Fall. Finde einen guten Weg, die Darstellung properties flexibel ergänzt werden kann.
- [x] Stelle zudem ergänzend dar, welchen Train Kategorien (Verkehrsarten) ein Projekt dient
- [x] Zeige Projekteigenschaften auch in der Projektdarstellung auf der Karte an. Stelle sicher dass diese Kurzansicht der Projekte als Komponente definiert wird, da sie demnächst auch an anderer Stelle angezeigt wird.
- [x] Stelle bei jedem Projekt alle zugeordneten Unterprojekte mit der Kurzansicht Projekt dar.
- [x] Stelle bei jedem Projekt das übergeordnete Projekt mit der Kurzansicht Projekt dar
- [x] Zeige bei jedem Projekt die Karte mit dem Projekt. Wenn es Unterprojekte gibt, zeige diese auf der Karte. Die Karte soll sich gleich verhalten wie die Übersichtskarte, allerdings nur mit den genannten Variantne (entweder Projekt anziehen oder die Unterprojekte. Die sind dann auch anklickbar zu machen)
- [x] Stelle (sofern breit genug) Projektdetails + Beschreibung neben der Karte dar (Karte rechts und zwei/Drittel der Breite)

- [x] Projektbearbeitungsmodus: Zeige alle Eigenschaften des Projekts an und stelle sicher, dass diese bearbeitbar sind. Halte in der Agent.md fest, dass bei Änderungen der Eigenschaften eines Projekts immer sofort auch dieser Bearbeitungsmodus angepasst werden muss.
- [x] Zeige die Versionshistorie nur für eingeloggte Benutzer an. Mache das zum Grundsatz und halte es an geeigneter Stelle für dich fest.
- [x] Zeige die Texte für Projekte in jedem Projekt an (sofern sie existieren). Dies soll über den "Übergeordnetes Projekt" erfolgen. 
- [x] Ergänze die Möglichkeit, dass Texte neu erstellt werden können, nur im eingeloggten Zustand und auch das ChangeTracking hier beachten.
- [x] Ergänze die Möglichkeit, existierende Texte zu bearbeiten. 


- [x] Füge die Möglichkeit hinzu, dass Texte nur eingelogt oder öffentlich angezeigt werden können.
- [x] Verschiebe in den Projekten die Darstellung von Verkehrsarten und Merkmale in die Box "Projektdetails". Entferne dort die ehemalige ID

- [x] **Gruppen-Persistenz zwischen Karte und Liste**
  Gruppenfilter wird als URL-Param gespeichert (`?group=id1,id2`). Beim Wechsel zwischen Karte und Liste bleibt der aktive Filter erhalten. *(Aktuelle Implementierung: URL-Params — kein localStorage nötig.)*



- [x] **Karte/Liste als Tab-Toggle auf einer Seite**
  Karte und Projektliste werden auf derselben Route (`/`) zusammengeführt. Ein Tab-Toggle (`Karte` | `Liste`) auf der Seite steuert die aktive Ansicht. Aktive Ansicht wird im URL-Param gespeichert (`?view=map` oder `?view=list`), damit Links auf eine bestimmte Ansicht zeigen können. Die Navigation "Projekte" im Header entfällt bzw. wird Teil des Toggles. Bisherige Route `/projects` wird auf `/?view=list` weitergeleitet.



- [x] **Nur ranghöchste Projekte anzeigen** *(Karte + Liste)*
  Toggle/Checkbox in der Filterleiste: "Nur übergeordnete Projekte". Filtert auf Projekte, bei denen `superior_project_id IS NULL`. Default: alle Projekte anzeigen.


- [x] **Die Anzeige bei Auswahl eines Projektes in der Karte soll nicht nur den Namen und mehr Informationen, sondern die wichtigsten Informationen des Projektes anzeigen, nämlich die Projektnummer sowie die Beschreibung.** 

### Change Tracking

- [x] **Change Tracking** *(Backend + Frontend)*
  Ermöglicht nachzuvollziehen, wer wann welche Felder eines Projekts geändert hat, und einzelne Felder auf frühere Werte zurückzusetzen.
  Hinweis: Datenmodell existiert noch nicht (Verzeichnis `change_tracking/` ist leer); PATCH-Endpunkt für Projekte fehlt ebenfalls noch.

  - [x] **Schritt 1: Datenmodell + Migration** *(Backend)*
    Fundament für alle weiteren Schritte.
    - `ChangeLog`-Tabelle: `id`, `project_id` (FK→projects), `user_id` (FK→users), `created_at`, optionales `note`-Feld
    - `ChangeLogEntry`-Tabelle: `id`, `changelog_id` (FK→changelog), `field_name`, `old_value` (TEXT, nullable), `new_value` (TEXT, nullable)
    - Alembic-Migration erstellen und anwenden

  - [x] **Schritt 2: PATCH-Endpunkt für Projekte** *(Backend)*
    Voraussetzung für Schritt 3 – ohne PATCH-Endpunkt können keine Änderungen ausgelöst werden.
    - `PATCH /api/v1/projects/{project_id}` — nimmt alle Projektfelder als optional entgegen
    - Vergleicht alten und neuen Wert je Feld; schreibt für jedes geänderte Feld einen `ChangeLogEntry`
    - Erstellt einen übergeordneten `ChangeLog`-Eintrag mit Zeitstempel + eingeloggtem Nutzer
    - Erfordert Rolle `editor` oder `admin`

  - [x] **Schritt 3: GET-Endpunkt für Changelog** *(Backend)*
    Macht die History über die API abrufbar.
    - `GET /api/v1/projects/{project_id}/changelog` — gibt alle `ChangeLog`-Einträge mit zugehörigen `ChangeLogEntry`-Zeilen zurück
    - Öffentlich lesbar (kein Login erforderlich)
    - Pydantic-Schemas für Response-Serialisierung

  - [x] **Schritt 4: Projekt bearbeiten** *(Frontend)*
    Erste sichtbare Funktion für Nutzer mit Schreibrechten.
    - „Bearbeiten"-Button in `ProjectDetail` (nur für `editor` / `admin` sichtbar)
    - Bearbeitungsformular mit allen relevanten Feldern
    - Speichern-Aktion ruft `PATCH /api/v1/projects/{id}` auf

  - [ ] **Schritt 5: Versionshistorie** *(Frontend)*
    Zeigt allen Nutzern, wer wann was geändert hat.
    - Neuer Abschnitt „Versionshistorie" in `ProjectDetail`
    - Timeline-Ansicht: Datum, Nutzername, Liste der geänderten Felder mit altem → neuem Wert

  - [ ] **Schritt 6: Revert-Funktion** *(Frontend)*
    Erlaubt das Zurücksetzen einzelner Felder auf einen früheren Stand.
    - Pro `ChangeLogEntry`: Button „Zurücksetzen auf [alter Wert]" (nur für `editor` / `admin`)
    - Sendet `PATCH` mit dem alten Wert des jeweiligen Felds


### Benutzerverwaltung *(geordnete Implementierungsschritte)*

- [x] **Schritt 1: Login-UI** *(Frontend)*
  Das Backend hat bereits HTTP Basic Auth mit Rollen (viewer / editor / admin).
  Die App bleibt für alle Nutzer vollständig lesbar — Login ist nur für Schreiboperationen nötig.
  - „Anmelden"-Button im Header öffnet Login-Formular (Modal)
  - Credentials im React-Context vorhalten; `Authorization`-Header wird bei API-Requests mitgesendet
  - API-Interceptor: bei 401/403 → Login-Modal öffnen (kein Zwangs-Redirect für Lesezugriff)
  - Nach erfolgreichem Login: Header zeigt Nutzername + „Abmelden"-Button

- [x] **Schritt 2: Rollenbasierte Bearbeitung** *(Frontend)*
  Abhängigkeit: Schritt 1 abgeschlossen.
  - „Bearbeiten"-Button in `ProjectDetail` und alle anderen Schreiboperationen nur sichtbar/aktiv
    für eingeloggte Nutzer mit Rolle `editor` oder `admin`
  - Nicht eingeloggte Nutzer sehen alle Daten uneingeschränkt, aber keine Bearbeitungs-Controls
  - Admin-Bereich im Header nur für `admin` sichtbar

- [x] **Schritt 4: User-Management-Seite** *(Backend + Frontend)*
  Abhängigkeit: Schritte 1 + 2 abgeschlossen. Nur für Admins zugänglich.
  Backend (fehlende Endpunkte ergänzen):
  - `PUT /api/v1/users/{id}` — Rolle, E-Mail oder Passwort ändern
  - `DELETE /api/v1/users/{id}` — Nutzer löschen
  Frontend:
  - Seite `/admin/users`: Tabelle aller Nutzer (Name, Rolle, E-Mail, erstellt am)
  - Nutzer anlegen (Name, E-Mail, Rolle, initiales Passwort oder Reset-Link versenden)
  - Rolle ändern / Passwort zurücksetzen / Nutzer löschen

### Backup DB
- [x] **Manuelles Backup & Restore** *(Makefile + Shell-Skripte implementiert)*
  `scripts/backup_db.sh`, `scripts/restore_db.sh`, Makefile-Targets: `backup-db`, `restore-db`, `list-backups`.
  Vollständige Dokumentation inkl. Automatisierung (systemd-Timer, rclone): [`docs/production_setup.md`](production_setup.md#backup-system)



  ### Transfer to Docker
- [x] Transfer the system to docker. Make difference between development and production, but both live in side docker (in dev for example just some services like db etc)

  **Services:**
  | Service | Dev | Prod |
  |---------|-----|------|
  | PostgreSQL + PostGIS | Docker | Docker |
  | Backend (FastAPI/uvicorn) | Docker (volume-mounted src, hot-reload) | Docker |
  | Frontend | local Vite dev server | Docker (nginx, pre-built) |
  | nginx reverse proxy | — | Docker |

  **Implementation steps:**

  - [x] **Schritt 1: Dockerfile für Backend**
    - `apps/backend/Dockerfile` — multi-stage: `builder` (pip install) → `runtime` (uvicorn)
    - Base image: `python:3.12-slim` with GDAL/PostGIS client libs
    - Non-root user, copy venv from builder stage
    - `ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`

  - [x] **Schritt 2: Dockerfile für Frontend (Produktion)**
    - `apps/frontend/Dockerfile` — multi-stage: `builder` (npm ci + npm run build) → `nginx:alpine` (serve dist/)
    - nginx config: SPA fallback (`try_files $uri /index.html`), proxy `/api/` → backend

  - [x] **Schritt 3: docker-compose.yml (Produktion)**
    - Services: `db` (postgres:16-postgis), `backend`, `frontend` (nginx)
    - `db`: named volume `pgdata`, healthcheck
    - `backend`: depends_on db (healthy), reads `.env.prod`, runs Alembic migration on startup via entrypoint script
    - `frontend`: depends_on backend, exposes port 80/443
    - Shared network `raildashboard-net`

  - [x] **Schritt 4: Datenmigration – lokale DB → Docker-Volume (einmalig)**
    - ⚠️ Dieser Schritt muss **vor** dem ersten Start des DB-Containers ausgeführt werden, damit keine Daten verloren gehen.
    - Vorgehen:
      1. Backup der lokalen Datenbank erstellen: `make backup-db` → erzeugt `backups/raildashboard_<timestamp>.dump`
      2. Docker-Volume für die Dev-DB anlegen: `docker volume create raildashboard_pgdata_dev`
      3. DB-Container starten (noch leer): `docker compose -f docker-compose.dev.yml up -d db`
      4. Dump in den Container einspielen: `make restore-db BACKUP=backups/<datei>.dump DB_URL=postgresql://...@localhost:5433/raildashboard`
      5. Verifizieren: Anzahl der Projekte in lokaler DB == Anzahl im Docker-Container
    - Das Volume `raildashboard_pgdata_dev` überlebt `docker compose down` — Daten bleiben erhalten.
    - **Nur `docker compose down -v`** löscht das Volume. Niemals unbeabsichtigt ausführen.

  - [x] **Schritt 5: docker-compose.dev.yml (Entwicklung)**
    - Nur `db` Service (postgres:16-postgis) — Backend und Frontend laufen weiterhin lokal via `make dev`
    - Named volume `raildashboard_pgdata_dev` → Daten persistieren zwischen Container-Neustarts
    - Port-Mapping: `5433:5432` (vermeidet Konflikt mit eventuell lokal laufendem Postgres)
    - `DATABASE_URL` in `.env` auf `localhost:5433` anpassen (Kommentar: "Docker dev DB")
    - `VITE_API_BASE_URL=http://localhost:8000` bleibt unverändert
    - Startup: `docker compose -f docker-compose.dev.yml up -d`
    - `.env.docker-dev.example` dokumentiert die angepasste `DATABASE_URL`

  - [x] **Schritt 6: Entrypoint-Skript für Backend**
    - `apps/backend/docker-entrypoint.sh`: wartet auf DB-Readiness, führt `alembic upgrade head` aus, startet uvicorn
    - Verhindert Race-Condition beim ersten Start

  - [x] **Schritt 7: .env.docker.example**
    - Dokumentiert alle Docker-spezifischen Werte (z.B. `DATABASE_URL` mit `db` als Hostname statt `localhost`)
    - Abgeleitet von `.env.example`, nur Docker-Unterschiede kommentiert

  - [x] **Schritt 8: Makefile-Targets für Docker**
    - `docker-dev-up` / `docker-dev-down` — Dev-DB starten/stoppen
    - `docker-prod-build` — alle Images bauen
    - `docker-prod-up` / `docker-prod-down` — Prod-Stack starten/stoppen
    - `docker-migrate` — Alembic inside backend container
    - `docker-create-user` — `create_initial_user.py` inside backend container
    - `docker-backup-db` — `pg_dump` via `docker exec` auf db-Container

  - [x] **Schritt 9: docs/production_setup.md aktualisieren**
    - Neuer Abschnitt "Docker Deployment" als primärer Weg
    - Bestehenden systemd-Abschnitt als "Legacy / ohne Docker" behalten
    - Backup-Workflow mit `docker exec` dokumentieren

  - [x] **Schritt 10: .dockerignore-Dateien**
    - `apps/backend/.dockerignore`: `.venv`, `__pycache__`, `*.pyc`, `backups/`, `.env*`
    - `apps/frontend/.dockerignore`: `node_modules`, `dist`, `.env*`

  - [x] **Schritt 11: Roundtrip-Test**
    - `docker compose -f docker-compose.dev.yml up` → DB erreichbar, `make migrate` erfolgreich
    - `docker compose up --build` (Prod) → Frontend unter `localhost:80` erreichbar, API-Calls funktionieren, Login funktioniert

### Celery Tasks
- [x] **Celery Task Queue** — Für lang laufende Tasks (Routing, PDF-Verarbeitung)
  Voraussetzung für Haushaltsberichte-Import und Routing-Service.

  **Implementierungsschritte:**

  - [x] **Schritt 1: Redis als Broker + Result-Backend**
    - Redis-Service zu `docker-compose.yml` (prod) und `docker-compose.dev.yml` (dev) hinzufügen
    - In Dev: Redis als Docker-Container, Backend verbindet sich via `localhost:6379`
    - In Prod: Redis als interner Service im Compose-Stack (kein Port nach außen)
    - Dependencies: `celery[redis]` + `redis` zu `requirements.txt` / `pyproject.toml`
    - `.env.example` und `.env.docker.example` um `CELERY_BROKER_URL` und `CELERY_RESULT_BACKEND` erweitern

  - [x] **Schritt 2: Celery-App initialisieren**
    - `apps/backend/dashboard_backend/celery_app.py` — Celery-Instanz mit Broker- und Result-URL aus Settings
    - Settings (`config.py`) um `CELERY_BROKER_URL` (Default: `redis://localhost:6379/0`) und `CELERY_RESULT_BACKEND` erweitern
    - `tasks/`-Paket anlegen: `apps/backend/dashboard_backend/tasks/__init__.py`

  - [x] **Schritt 3: Worker-Start (Dev + Prod)**
    - Dev: Makefile-Target `celery-worker` → `celery -A dashboard_backend.celery_app worker --loglevel=info`
    - Prod: Eigener `worker`-Service in `docker-compose.yml` (gleiche Backend-Image, Command überschrieben)
      ```yaml
      worker:
        build: apps/backend
        command: celery -A dashboard_backend.celery_app worker --loglevel=info
        depends_on: [db, redis]
        env_file: .env.prod
      ```
    - Makefile-Target `docker-worker-logs` für Log-Einsicht im Prod-Container

  - [x] **Schritt 4: Task-Status-Endpoint**
    - `GET /api/v1/tasks/{task_id}` — gibt `{task_id, status, result, error}` zurück
    - Status-Werte: `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`
    - Pydantic-Schema `TaskStatusResponse`
    - Wird vom Frontend zum Polling verwendet (kein WebSocket notwendig)

  - [x] **Schritt 5: Proof-of-Concept-Task**
    - Dummy-Task `tasks/debug.py`: `add(x, y)` — addiert zwei Zahlen, schläft 2 s
    - `POST /api/v1/tasks/debug` startet Task, gibt `task_id` zurück
    - Roundtrip-Test: Task starten → Status pollen → SUCCESS verifizieren
    - Stellt sicher, dass die gesamte Pipeline (API → Celery → Redis → Result) funktioniert

  - [x] **Schritt 6: Dokumentation + Makefile**
    - `docs/architecture.md` um Celery/Redis-Komponente erweitern
    - `apps/backend/README.md` um Worker-Start-Anleitung ergänzen (Dev + Prod)
    - Makefile-Targets zusammenfassen: `celery-worker`, `docker-worker-logs`



