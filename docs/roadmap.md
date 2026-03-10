# Roadmap

Architecture overview: see `docs/architecture.md`, data models: `docs/models.md`.


---

## Short-Term Features

#### Test development
- [ ] lot of failed development tests — vor allem ein Problem mit Routen; prüfen ob noch aktuell (user task - no ai)
- [ ] zoom a little bit more out in the map in the project

---

## Mid-Term Features

### Haushaltsberichte

Jährlicher Import der Anlage VWIB, Teil B (Bundeshaushalt) als PDF.
Die Tabelle enthält alle Bedarfsplanmaßnahmen des Schienenwegeinvestitionsprogramms
mit FinVe-Nummern, Kostenschätzungen und Jahresansätzen je Haushaltskonto.

**Implementierungsstand:** Schritte 1–8 vollständig abgeschlossen (DB-Modelle, Parser, API, Frontend-Import-Flow, FinVe-Matching, FinVe-Anzeige in Projektdetailseite). Siehe Finished-Sektion für Details.

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

**Offene Punkte:**
- [ ] **FinVe in zugeordneten Projekten anzeigen** — In der Projektdetailseite werden die FinVes bereits angezeigt (`FinveSection.tsx`). Prüfen ob umgekehrt auch das zugeordnete Projekt aus der FinVe-Perspektive navigierbar ist.
- [x] **Sonderbehandlung Sammelfinve** — Einzelne FinVes (z.B. Sammelfinve für kleinere Maßnahmen) haben massenhaft Projektzuordnungen, die sich über die Jahre ändern. Benötigt: eigene UI-Behandlung im Review-Flow, ggf. Jahres-spezifische Zuordnungstabelle statt einfacher `FinveToProject`.
- [ ] Show all the financing in an separate overview. List all contracts. Make it clickable for more informations. Add the same diagrams as in ProjectView. Make the overview searchable

---

### Change Tracking

**Implementierungsstand:** Schritte 1–4 abgeschlossen (DB-Modelle `change_log`/`change_log_entry`, PATCH-Endpunkt für Projekte, GET-Changelog, Bearbeitungsformular im Frontend).

- [ ] **Schritt 5: Versionshistorie** *(Frontend)*
  - Neuer Abschnitt „Versionshistorie" in `ProjectDetail` (nur für eingeloggte Nutzer sichtbar)
  - Timeline-Ansicht: Datum, Nutzername, Liste der geänderten Felder mit altem → neuem Wert
  - Daten kommen von `GET /api/v1/projects/{project_id}/changelog`

- [ ] **Schritt 6: Revert-Funktion** *(Frontend)*
  - Pro `ChangeLogEntry`: Button „Zurücksetzen auf [alter Wert]" (nur für `editor` / `admin`)
  - Sendet `PATCH /api/v1/projects/{id}` mit dem alten Wert des jeweiligen Felds

---

### Sonstiges

- [ ] **ProjectProgress** *(Backend + Frontend)*
  Fortschrittsstand eines Projekts (Planungs-, Genehmigungs-, Bauphase). Speist sich aus mehreren Quellen (z. B. Bundestag-Drucksachen, Pressemitteilungen, manuelle Eingabe). Benötigt Validierungslogik für Konflikte zwischen Quellen.
  - Backend: `ProjectProgress`-Modell implementieren (Status, Datum, Quelle, Kommentar)
  - Frontend: Zeitleiste/Meilenstein-Ansicht in `ProjectDetail`

- [ ] **Anzeige der BVWP-Daten** — Für einige Projekte liegen BVWP-Daten vor, diese sind vollständig und übersichtlich darzustellen

- [ ] **Anzeige Texte und Kommentare** — Kommentare anzeigen (Details noch offen)

- [ ] **Vervollständigung und Automatisierung Tests**

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

- [ ] **Netzzustandsbericht** — PDF-Import, Extraktion relevanter Kennzahlen in die Datenbank

- [ ] **Beschleunigungskommission Schiene** — Datentransfer aus öffentlichen Quellen + automatische Updates

- [ ] **BVWP-Datenimport** — Übernahme aus Legacy-Datenbank

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
- **project data** — primäres Transferziel
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

### Texte & Kommentare
- [x] Projekttexte anzeigen (über übergeordnetes Projekt), erstellen, bearbeiten
- [x] Sichtbarkeit von Texten: eingeloggt-only oder öffentlich
- [x] Versionshistorie und Bearbeitungsformular nur für eingeloggte Nutzer sichtbar

### Change Tracking (Schritte 1–4)
- [x] DB-Modelle `change_log` + `change_log_entry` + Alembic-Migration
- [x] `PATCH /api/v1/projects/{id}` — schreibt ChangeLog-Einträge je geändertem Feld (Rolle: editor/admin)
- [x] `GET /api/v1/projects/{id}/changelog` — öffentlich lesbar
- [x] Bearbeitungsformular in `ProjectDetail` (editor/admin); alle Felder bearbeitbar

### Benutzerverwaltung
- [x] Login-UI: Modal im Header, Credentials im React-Context, Authorization-Header bei API-Requests, 401/403-Interceptor
- [x] Rollenbasierte Bearbeitung: Schreiboperationen nur für editor/admin sichtbar
- [x] User-Management-Seite `/admin/users` (nur admin): Nutzer anlegen, Rolle/Passwort ändern, löschen

### Haushaltsberichte-Import (vollständig)
- [x] DB-Modelle: `HaushaltTitel`, `BudgetTitelEntry`, `HaushaltsParseResult`, `FinveChangeLog`, `BudgetChangeLog`, `UnmatchedBudgetRow` + Alembic-Migration
- [x] Pydantic-Schemas (`haushalt_import.py`), CRUD-Funktionen (`crud/haushalt_import.py`)
- [x] Celery-Task `parse_haushalt_pdf` (`tasks/haushalt.py`) mit `pdfplumber`; Parser-Fixes für 2026-Format (zusammengeführte Spalten, mehrzeilige Zellen, `_KAP_TITEL_RE` mit `(alt)`-Zusatz, `_BHO_NOTE_RE`)
- [x] API unter `/api/v1/import/haushalt`: `POST /parse`, `GET /parse-result`, `POST /confirm`, `GET/PATCH /unmatched`
- [x] Frontend `features/haushalt-import/`: Upload-Flow mit Celery-Polling, Review-Tabelle (neu/geändert/unmatched), Projektzuordnung per MultiSelect, Unmatched-Nachbearbeitung
- [x] Fuzzy-Matching (`tasks/finve_matching.py`, SequenceMatcher + Token-Overlap, Threshold 0.45) für automatische Projektzuordnungs-Vorschläge
- [x] FinVe → mehrere Projekte (bidirektionale Sync beim Confirm; MultiSelect auch bei update-Rows)
- [x] FinVe-Anzeige in `ProjectDetail`: `GET /api/v1/projects/{id}/finves`, `FinveSection.tsx` mit 3 Tabs (Budgetverteilung BarChart, Kostenentwicklung LineChart, Detailtabelle); `@mantine/charts` + `recharts`
- [x] **Sammelfinanzierungsvereinbarungen (SV-FinVes)**: Erkennung via Regex im Parser, `is_sammel_finve`-Flag in DB (`finve`-Tabelle) + Alembic-Migration, eigene Review-Sektion "Sammel-FinVes (Phase 2)" in der UI, per-Projekt-Unterzeilen mit Fuzzy-Vorschlägen aus dem Erläuterungstext, Erkennung mehrseitiger Erläuterungen (flat-table-Ansatz + Continuation-Detection), Wiederherstellung von Zeilen mit fehlendem YYY-Identifier via Raw-Text-Lookup

### Infrastruktur
- [x] Docker: Dev (nur DB + Redis), Prod (DB + Backend + Frontend/nginx + Worker); Entrypoint-Skript mit Alembic-Migration, Makefile-Targets
- [x] Celery Task Queue mit Redis-Broker; Task-Status-Endpoint `GET /api/v1/tasks/{task_id}`
- [x] Backup & Restore: `scripts/backup_db.sh`, `scripts/restore_db.sh`, Makefile-Targets; Doku in `docs/production_setup.md`
- [x] Backend-Authentifizierung: HTTP Basic Auth, PBKDF2, Rollen viewer/editor/admin
- [x] Routing-Algorithmus implementiert (pgRouting / GrassHopper-Microservice)
- [x] Docs bereinigt: `docs/architecture.md` als zentrale Architekturdokumentation
