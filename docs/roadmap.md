# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.

---

## Short-Term Features


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

### Benutzerverwaltung *(geordnete Implementierungsschritte)*

- [ ] **Schritt 1: Login-UI** *(Frontend)*
  Das Backend hat bereits HTTP Basic Auth mit Rollen (viewer / editor / admin).
  Die App bleibt für alle Nutzer vollständig lesbar — Login ist nur für Schreiboperationen nötig.
  - „Anmelden"-Button im Header öffnet Login-Formular (Modal)
  - Credentials im React-Context vorhalten; `Authorization`-Header wird bei API-Requests mitgesendet
  - API-Interceptor: bei 401/403 → Login-Modal öffnen (kein Zwangs-Redirect für Lesezugriff)
  - Nach erfolgreichem Login: Header zeigt Nutzername + „Abmelden"-Button

- [ ] **Schritt 2: Rollenbasierte Bearbeitung** *(Frontend)*
  Abhängigkeit: Schritt 1 abgeschlossen.
  - „Bearbeiten"-Button in `ProjectDetail` und alle anderen Schreiboperationen nur sichtbar/aktiv
    für eingeloggte Nutzer mit Rolle `editor` oder `admin`
  - Nicht eingeloggte Nutzer sehen alle Daten uneingeschränkt, aber keine Bearbeitungs-Controls
  - Admin-Bereich im Header nur für `admin` sichtbar

- [ ] **Schritt 3: Passwort zurücksetzen per E-Mail** *(Backend + Frontend)*
  Abhängigkeit: Schritt 1 abgeschlossen.
  Backend:
  - Feld `email` zum User-Modell ergänzen + Migration
  - Tabelle `password_reset_token` (Token, User-ID, Ablaufzeitpunkt) + Migration
  - SMTP-Konfiguration in Settings (Host, Port, Credentials)
  - `POST /api/v1/auth/request-reset` — nimmt E-Mail, sendet Reset-Link per Mail
  - `POST /api/v1/auth/reset-password` — nimmt Token + neues Passwort, invalidiert Token
  Frontend:
  - „Passwort vergessen?"-Link im Login-Modal → E-Mail-Eingabeformular
  - Reset-Formular (neues Passwort, Token aus URL-Param des Mail-Links)

- [ ] **Schritt 4: User-Management-Seite** *(Backend + Frontend)*
  Abhängigkeit: Schritte 1 + 2 abgeschlossen. Nur für Admins zugänglich.
  Backend (fehlende Endpunkte ergänzen):
  - `PUT /api/v1/users/{id}` — Rolle, E-Mail oder Passwort ändern
  - `DELETE /api/v1/users/{id}` — Nutzer löschen
  Frontend:
  - Seite `/admin/users`: Tabelle aller Nutzer (Name, Rolle, E-Mail, erstellt am)
  - Nutzer anlegen (Name, E-Mail, Rolle, initiales Passwort oder Reset-Link versenden)
  - Rolle ändern / Passwort zurücksetzen / Nutzer löschen

- [ ] **Change Tracking** *(Backend + Frontend)*
  Datenmodell existiert (`ChangeLog`, `ChangeLogEntry`), Logik fehlt noch.
  - Backend: Bei jedem PATCH auf ein Projekt werden geänderte Felder als `ChangeLogEntry` geschrieben (vorher/nachher per Feld)
  - Frontend: Pro Projekt eine "Versionshistorie"-Ansicht (Timeline) mit Datum, Feld, altem/neuem Wert und Nutzer
  - Revert-Funktion: Einzelne Felder auf einen früheren Stand zurücksetzen (nur editor/admin)

- [ ] **ProjectProgress** *(Backend + Frontend)*
  Fortschrittsstand eines Projekts (Planungs-, Genehmigungs-, Bauphase). Speist sich aus mehreren Quellen (z. B. Bundestag-Drucksachen, Pressemitteilungen, manuelle Eingabe). Benötigt Validierungslogik für Konflikte zwischen Quellen.
  - Backend: `ProjectProgress`-Modell implementieren (Status, Datum, Quelle, Kommentar)
  - Frontend: Zeitleiste/Meilenstein-Ansicht in `ProjectDetail`

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

- [x] **Gruppen-Persistenz zwischen Karte und Liste**
  Gruppenfilter wird als URL-Param gespeichert (`?group=id1,id2`). Beim Wechsel zwischen Karte und Liste bleibt der aktive Filter erhalten. *(Aktuelle Implementierung: URL-Params — kein localStorage nötig.)*



- [x] **Karte/Liste als Tab-Toggle auf einer Seite**
  Karte und Projektliste werden auf derselben Route (`/`) zusammengeführt. Ein Tab-Toggle (`Karte` | `Liste`) auf der Seite steuert die aktive Ansicht. Aktive Ansicht wird im URL-Param gespeichert (`?view=map` oder `?view=list`), damit Links auf eine bestimmte Ansicht zeigen können. Die Navigation "Projekte" im Header entfällt bzw. wird Teil des Toggles. Bisherige Route `/projects` wird auf `/?view=list` weitergeleitet.



- [x] **Nur ranghöchste Projekte anzeigen** *(Karte + Liste)*
  Toggle/Checkbox in der Filterleiste: "Nur übergeordnete Projekte". Filtert auf Projekte, bei denen `superior_project_id IS NULL`. Default: alle Projekte anzeigen.


- [x] **Die Anzeige bei Auswahl eines Projektes in der Karte soll nicht nur den Namen und mehr Informationen, sondern die wichtigsten Informationen des Projektes anzeigen, nämlich die Projektnummer sowie die Beschreibung.** 