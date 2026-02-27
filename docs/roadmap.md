# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.

---

## Short-Term Features
- [x] Erstelle ein Inhaltsverzeichnis für die Projektdarstellung, das an der linken Seite ausgeklappt werden kann, dadurch ist eine schnellere Orientierung möglich. Bei Elementen die eingeklappt sind, sind diese auszuklappen wenn das Element über das seitliche Inhaltsverzeichnis aufgerufen wird.
- [x] if the window is to small, collaps the header menu to burger menu
- [ ] Clean up the docs files. Focus on architecture.md

### Claude Hooks
- [ ] **Pre-edit guard on `.env`** — Hook that warns before any edit to `.env` files (AGENT.md rule: never modify `.env`)
- [ ] **Post-edit: `make gen-api` reminder** — After editing backend schemas or endpoints, remind to run `make gen-api` if the OpenAPI contract changed
- [ ] **Post-edit: migration reminder** — After editing `apps/backend/dashboard_backend/models/**`, remind to create an Alembic migration
- [ ] **Post-edit: roadmap sync reminder** — After editing features or API endpoints, remind to update `docs/roadmap.md`

### Claude Skills
- [ ] **`/commit`** — Conventional Commit helper: reads staged diff, proposes a commit message in `type(scope): description` format, asks for confirmation
- [ ] **`/gen-api`** — Regenerate frontend API client: verifies backend is running, runs `make gen-api`, reports changed files
- [ ] **`/update-roadmap`** — Mark a completed feature: finds the matching `[ ]` item in `docs/roadmap.md` and marks it `[x]`
- [ ] **`/new-api-route`** — New backend route scaffold: walks through the checklist (endpoint → schema → CRUD → test → `make gen-api`)

---

## Mid-Term Features

- [ ] **Routenvorschlag per GrassHopper** *(Backend + Frontend)*
  Im Backend existiert bereits ein Routing-Microservice (GrassHopper/pgRouting). Ablauf:
  1. Nutzer öffnet ein Projekt und wählt "Route berechnen"
  2. Start- und Endpunkt werden aus bekannten **OperationalPoints** (Dropdown, durchsuchbar) gewählt
  3. Backend berechnet Route und gibt GeoJSON zurück
  4. Frontend zeigt die vorgeschlagene Route als Vorschau auf der Karte an
  5. Nutzer akzeptiert → Route wird als `geojson_representation` des Projekts gespeichert (PATCH)
  6. Nutzer lehnt ab → Vorschau wird verworfen
- [ ] Anzeige der Kommentare sowie 

### Backup DB
- [x] **Manuelles Backup & Restore** *(Makefile + Shell-Skripte implementiert)*
  `scripts/backup_db.sh`, `scripts/restore_db.sh`, Makefile-Targets: `backup-db`, `restore-db`, `list-backups`.
  Vollständige Dokumentation inkl. Automatisierung (systemd-Timer, rclone): [`docs/production_setup.md`](production_setup.md#backup-system)

- [ ] **ProjectProgress** *(Backend + Frontend)*
  Fortschrittsstand eines Projekts (Planungs-, Genehmigungs-, Bauphase). Speist sich aus mehreren Quellen (z. B. Bundestag-Drucksachen, Pressemitteilungen, manuelle Eingabe). Benötigt Validierungslogik für Konflikte zwischen Quellen.
  - Backend: `ProjectProgress`-Modell implementieren (Status, Datum, Quelle, Kommentar)
  - Frontend: Zeitleiste/Meilenstein-Ansicht in `ProjectDetail`
– [ ] **Anzeige der BVWP-Daten** Für einige Projekte liegen BVWP-Daten vor, diese sind vollständig und übersichtlich darzustellen
- [ ] **Anzeige Texte und Kommentare:**
- [ ] **Vervollständigung und Automatisierung Test**

---

## Long-Term Features

- [ ] **Netzzustandsbericht** — PDF-Import, Extraktion relevanter Kennzahlen in die Datenbank
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
- [ ] **Beschleunigungskommission Schiene** — Datentransfer aus öffentlichen Quellen + automatische Updates
- [ ] **BVWP-Datenimport** — Übernahme aus Legacy-Datenbank
- [x] **Backend-Authentifizierung** — HTTP Basic Auth, PBKDF2, Rollen: viewer / editor / admin (Frontend-Integration steht noch aus, siehe Mid-Term)
- [ ] **Celery Task Queue** — Für lang laufende Tasks (Routing, PDF-Verarbeitung)
- [ ] **OpenStreetMap-Anbindung** — Breite Abdeckung, aber komplex für Routing-Anfragen
- [ ] **DB OpenData** — Schienennetz Deutsche Bahn ([GovData](https://www.govdata.de/suche/daten/schienennetz-deutsche-bahnddea3))
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
