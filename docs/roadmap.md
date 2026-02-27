# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.

---

## Short-Term Features

- [ ] Login User - dauerhaft über Sitzungen hinweg.

- [ ] **Versionshistorie** *(Frontend)*
  Zeigt allen Nutzern, wer wann was geändert hat.
  - Neuer Abschnitt „Versionshistorie" in `ProjectDetail`
  - Timeline-Ansicht: Datum, Nutzername, Liste der geänderten Felder mit altem → neuem Wert

- [ ] **Revert-Funktion** *(Frontend)*
  Erlaubt das Zurücksetzen einzelner Felder auf einen früheren Stand.
  - Pro `ChangeLogEntry`: Button „Zurücksetzen auf [alter Wert]" (nur für `editor` / `admin`)
  - Sendet `PATCH` mit dem alten Wert des jeweiligen Felds

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

### Benutzerverwaltung

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

### Weiteres

- [ ] **Automatisiertes Backup Datenbank** — Maßnahmen zum Backup, möglichst über einfache Kommandozeile

- [ ] **ProjectProgress** *(Backend + Frontend)*
  Fortschrittsstand eines Projekts (Planungs-, Genehmigungs-, Bauphase). Speist sich aus mehreren Quellen (z. B. Bundestag-Drucksachen, Pressemitteilungen, manuelle Eingabe). Benötigt Validierungslogik für Konflikte zwischen Quellen.
  - Backend: `ProjectProgress`-Modell implementieren (Status, Datum, Quelle, Kommentar)
  - Frontend: Zeitleiste/Meilenstein-Ansicht in `ProjectDetail`

- [ ] **Anzeige der BVWP-Daten** — Für einige Projekte liegen BVWP-Daten vor; vollständig und übersichtlich darstellen

- [ ] **Anzeige Texte und Kommentare**

- [ ] **Vervollständigung und Automatisierung Tests**

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
- [ ] **Celery Task Queue** — Für lang laufende Tasks (Routing, PDF-Verarbeitung)
- [ ] **OpenStreetMap-Anbindung** — Breite Abdeckung, aber komplex für Routing-Anfragen
- [ ] **DB OpenData** — Schienennetz Deutsche Bahn ([GovData](https://www.govdata.de/suche/daten/schienennetz-deutsche-bahnddea3))
- [ ] **RINF-Daten evaluieren** — Für Bahnhofs-/Stationsverbindungen ggf. weiterhin benötigt
- [ ] **GeoLine-Erstellung** — Möglichkeit, neue Streckengeometrien zu erzeugen, wenn vorhandene unvollständig/ungültig sind. Ansatz noch offen (Zeichentool auf Karte vs. automatische Vervollständigung).
- [ ] **Automatisierung Preisniveau** — Tool zur Preisanpassung gemäß Inflation/Baukostenentwicklung für bessere Vergleichbarkeit

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
