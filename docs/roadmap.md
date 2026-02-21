# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.

---

## Short-Term Features

### Frontend


- [ ] **Die Anzeige bei Auswahl eines Projektes in der Karte soll nicht nur den Namen und mehr Informationen, sondern die wichtigsten Informationen des Projektes anzeigen, nämlich die Projektnummer sowie die Beschreibung.** 

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

- [ ] **Login-UI + Rollenbasierte Bearbeitung** *(Frontend)*
  Das Backend hat bereits HTTP Basic Auth mit Rollen (viewer / editor / admin).
  Fehlend im Frontend:
  - Login-Dialog oder Login-Seite (Eingabe von Username + Passwort, Token/Session im Browser speichern)
  - Bearbeiten-Button in `ProjectDetail` und andere Schreiboperationen nur sichtbar/aktiv, wenn Nutzer eingeloggt ist und die Rolle `editor` oder `admin` hat
  - Logout-Möglichkeit im Header

- [ ] **User-Management-Seite** *(Frontend + Backend)*
  Nur für Admins zugänglich. Ermöglicht:
  - Nutzer anlegen (Name, Passwort, Rolle)
  - Nutzer bearbeiten (Rolle ändern, Passwort zurücksetzen)
  - Nutzer deaktivieren/löschen
  Backend-Endpunkte für User-CRUD müssen ggf. noch ergänzt werden.

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
- [x] **User Authentication** — HTTP Basic Auth, PBKDF2, Rollen: viewer / editor / admin
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
- [x] User Authentication (HTTP Basic Auth, PBKDF2, Rollen: viewer / editor / admin)
- [x] Routing-Algorithmus implementiert (pgRouting / GrassHopper-Microservice)

- [x] **Gruppen-Persistenz zwischen Karte und Liste**
  Gruppenfilter wird als URL-Param gespeichert (`?group=id1,id2`). Beim Wechsel zwischen Karte und Liste bleibt der aktive Filter erhalten. *(Aktuelle Implementierung: URL-Params — kein localStorage nötig.)*



- [x] **Karte/Liste als Tab-Toggle auf einer Seite**
  Karte und Projektliste werden auf derselben Route (`/`) zusammengeführt. Ein Tab-Toggle (`Karte` | `Liste`) auf der Seite steuert die aktive Ansicht. Aktive Ansicht wird im URL-Param gespeichert (`?view=map` oder `?view=list`), damit Links auf eine bestimmte Ansicht zeigen können. Die Navigation "Projekte" im Header entfällt bzw. wird Teil des Toggles. Bisherige Route `/projects` wird auf `/?view=list` weitergeleitet.



- [x] **Nur ranghöchste Projekte anzeigen** *(Karte + Liste)*
  Toggle/Checkbox in der Filterleiste: "Nur übergeordnete Projekte". Filtert auf Projekte, bei denen `superior_project_id IS NULL`. Default: alle Projekte anzeigen.