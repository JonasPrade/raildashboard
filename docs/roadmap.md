# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.

---

## Short-Term Features

### Frontend

- [ ] **Gruppen-Persistenz zwischen Karte und Liste**
  Gruppenfilter wird als URL-Param gespeichert (`?group=id1,id2`). Beim Wechsel zwischen Karte und Liste bleibt der aktive Filter erhalten. *(Aktuelle Implementierung: URL-Params — kein localStorage nötig.)*

- [ ] **Karte/Liste als Tab-Toggle auf einer Seite**
  Karte und Projektliste werden auf derselben Route (`/`) zusammengeführt. Ein Tab-Toggle (`Karte` | `Liste`) auf der Seite steuert die aktive Ansicht. Aktive Ansicht wird im URL-Param gespeichert (`?view=map` oder `?view=list`), damit Links auf eine bestimmte Ansicht zeigen können. Die Navigation "Projekte" im Header entfällt bzw. wird Teil des Toggles. Bisherige Route `/projects` wird auf `/?view=list` weitergeleitet.

- [ ] **Nur ranghöchste Projekte anzeigen** *(Karte + Liste)*
  Toggle/Checkbox in der Filterleiste: "Nur übergeordnete Projekte". Filtert auf Projekte, bei denen `superior_project_id IS NULL`. Default: alle Projekte anzeigen.

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
- [ ] **Haushaltsberichte Tabelle VE** — PDF-Import und Konvertierung in `FinVe`-Einträge
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
