# Feature: MCP-Server mit API-Key-Authentifizierung

**Status: umgesetzt (2026-10-07)** — Phase 1 (API-Keys) und Phase 2 (MCP-Server)
sind implementiert. Abweichungen und Präzisierungen gegenüber dem Konzept stehen
unter [Umsetzungsstand](#umsetzungsstand-2026-10-07).

## Ziel

Das Dashboard über das **Model Context Protocol (MCP)** für KI-Assistenten
zugänglich machen: Projekte, Finanzierung und Planungsstand abfragen und gezielt
fortschreiben, ohne den Umweg über die Weboberfläche. Der Zugriff läuft über
**persönliche API-Keys** und erbt dabei vollständig das bestehende Rollen- und
Rechtemodell — ein Key kann nie mehr als der Nutzer, dem er gehört.

## Designentscheidungen (mit dem Nutzer abgestimmt, 2026-09-09)

- **API-Keys statt OAuth** — nicht als Übergangslösung, sondern als eigene,
  bleibende Auth-Art. Der geplante Authentik-Umzug löst den *Menschen*-Login
  (Browser, SSO); Maschinen- und Agenten-Zugriff läuft auch danach über Keys.
  Es entsteht also kein Wegwerf-Code (siehe
  [Abgrenzung zu Authentik/OAuth](#abgrenzung-zu-authentikoauth)).
- **MCP-Server im Backend gemountet**, nicht als eigener Compose-Service. Ein
  Deployment, eine Auth-Kette, keine Token-Weitergabe zwischen zwei Prozessen.
  Ein separater Service brächte ein zweites Rechte-Modell und eine zusätzliche
  Vertrauensgrenze, ohne Gegenwert.
- **Tools rufen die vorhandene CRUD-/Service-Schicht**, nicht die eigene
  HTTP-API. Kein Selbstaufruf über das Netzwerk, keine doppelte Serialisierung.
- **Lesen *und* Schreiben** — Schreib-Tools sind über den bestehenden
  Permission-Katalog gegated und lassen sich pro Key zusätzlich einschränken
  (ein Key kann read-only sein, auch wenn sein Nutzer Editor ist).
- **Importe dürfen MCP-Tools bekommen (2026-10-17, vorher ausgeschlossen).** Ein
  Import bekommt Tools, wenn sein Ablauf in kurze Schritte zerfällt: Ein langlaufender
  Celery-Job wird nur *gestartet* und sein Status von einem zweiten Tool abgefragt, nie
  in einem Tool-Aufruf abgewartet. Mensch-im-Loop bleibt: Agenten schreiben Rohdaten und
  Zuordnungen mit Begründung, abgeleitete Beobachtungen entstehen erst beim Bestätigen.
  Jeder Import gated über sein eigenes `*.import`-Recht. Umgesetzt bzw. geplant:
  **Fulda-Runde** (Agent liest das PDF selbst, kein Upload, siehe
  `feature-fulda-import.md`), **VIB** (Agent liest das PDF selbst, der Upload bleibt als
  zweiter Weg, siehe `feature-vib-import.md` → Phase 7; Teilprojekt-Entwürfe aus PFA-Abschnitten
  auf Anforderung mit `create_vib_pfa_subprojects`, Phase 8) und **Infraplan** (Tools nach dem
  Upload, siehe `feature-infraplan-import.md` → „MCP & Skill“). Skills für diese Abläufe liegen in
  `.claude/skills/` und kommen vom Server (nächster Punkt).
- **Skills kommen vom MCP (2026-10-17):** Skills für die Arbeit über den MCP werden
  nicht mehr von Hand nach claude.ai hochgeladen, sondern vom Server selbst
  ausgeliefert (`list_skills`, `get_skill`) — immer in der Fassung des deployten
  Images, passend zu den Tools, die gerade laufen. Siehe
  [Skills über MCP](#skills-über-mcp-2026-10-17).

## Ausgangslage (Stand 2026-09-09)

- **Authentifizierung** (`core/security.py`): HTTP Basic (`HTTPBasic`) **oder**
  signiertes Session-Cookie (`session`, HMAC-SHA256, 7 Tage). Passwörter als
  PBKDF2-HMAC-SHA256 mit 390.000 Iterationen und zufälligem Salt; ein
  kurzlebiger Credential-Cache (5 min, HMAC-Fingerprint, Issue #92) fängt die
  PBKDF2-Kosten pro Request ab. Kein JWT, kein Bearer-Token, kein OAuth.
- **Rechte** (`core/permissions.py`): Capability-Katalog im Code
  (`project.edit`, `progress.edit`, `todo.create`, …), Rollen in der DB,
  `require_permission(*keys)` als FastAPI-Dependency,
  `User.has_permission()` mit Super-Admin-Bypass. Siehe
  `docs/features/feature-user-roles-permissions.md`.
- **API-Oberfläche**: `apps/backend/dashboard_backend/api/v1/` mit ~25 Routern,
  gemountet unter `/api/v1` (`main.py`), nginx leitet `/api/` an
  `backend:8000` weiter (`apps/frontend/nginx.conf`).
- **MCP existierte im Repo bis zur Umsetzung (2026-10-07) nicht.**

## Abgrenzung zu Authentik/OAuth

Der Authentik-Umzug ist ein **eigenes, vorgelagertes oder paralleles Thema** und
nicht Teil dieses Features. Wichtig ist nur, dass dieses Feature ihn nicht
blockiert und von ihm nicht entwertet wird:

| | heute | nach Authentik |
|---|---|---|
| Menschen im Browser | Basic + Session-Cookie | OIDC-Login gegen Authentik |
| Agenten / Maschinen | **API-Key (dieses Feature)** | API-Key (unverändert) **oder** von Authentik ausgestelltes Token |
| MCP-Tools | unverändert | unverändert |
| Rechteprüfung | `User.has_permission()` | `User.has_permission()` |

Der Authentik-Umzug ergänzt später einen **zweiten Bearer-Zweig** an derselben
Stelle in derselben Dependency: `/mcp` wird Resource Server, das Bearer-Token
ist dann ein von Authentik signiertes JWT statt eines API-Keys. Tools,
Rechteprüfung und Datenmodell bleiben davon unberührt. Erst damit wird auch der
Connector-Weg über claude.ai möglich, der OAuth voraussetzt; Clients mit
konfigurierbaren Headern (Claude Code) funktionieren schon vorher.

## Scope

**In scope:**

1. Datenmodell `api_keys` inkl. Alembic-Migration.
2. Bearer-Auth als dritter Weg in der bestehenden Auth-Kette (gilt damit für
   die gesamte REST-API, nicht nur für MCP).
3. Key-Verwaltung: Endpunkte + Admin-UI (anlegen, auflisten, widerrufen).
4. MCP-Server unter `/mcp`, Streamable HTTP, im Backend gemountet.
5. Tool-Katalog (lesend + schreibend) mit Permission-Gates.
6. Tests, `make gen-api`, Deployment-Konfiguration, Doku.

**Out of scope:**

- OAuth / Authentik-Anbindung (eigenes Thema, siehe oben).
- ~~MCP-Tools für die übrigen Importe~~ — erledigt: Bauportal mit #293, Medien seit
  2026-10-31 (siehe [Ausbau 2026-10-31](#ausbau-2026-10-31-lückenanalyse)).
- Löschen von Projekten oder anderen Stammdaten über MCP (einzelne Geometrie-Features
  schon, siehe `edit_project_geometry`; Projekttexte und Medienberichte seit
  2026-10-31 — Inhalte mit Änderungsprotokoll bzw. Importeinträge, keine Stammdaten).
- MCP-*Resources* und *Prompts* — die erste Ausbaustufe bietet nur *Tools*.
- Pro-Key-Ratelimits (nur `last_used_at`-Tracking, siehe Sicherheit).

## Datenmodell

Neue Tabelle **`api_keys`**:

| Spalte | Typ | Bedeutung |
|---|---|---|
| `id` | Integer, PK | |
| `user_id` | FK → `users.id`, cascade delete | Besitzer; der Key erbt dessen Rechte |
| `name` | String(100) | Klartext-Label („Claude Code Laptop") |
| `prefix` | String(12), unique, indexiert | Klartext-Teil des Tokens, dient dem Lookup |
| `key_hash` | String(64) | SHA-256-Hex des Geheimnisses |
| `scopes` | JSON/Array of String, nullable | `NULL` = alle Rechte des Nutzers; sonst Schnittmenge |
| `created_at` | DateTime | |
| `last_used_at` | DateTime, nullable | gedrosselt geschrieben (siehe unten) |
| `expires_at` | DateTime, nullable | `NULL` = unbegrenzt |
| `revoked_at` | DateTime, nullable | gesetzt = sofort ungültig; Zeile bleibt für die Nachvollziehbarkeit |

Migration über `make migrate-create MSG="add api_keys table"` — nie `alembic`
direkt aufrufen.

## Token-Format und Prüfung

Format: `rdb_<prefix>_<secret>`

- `prefix`: 12 Zeichen, base32, im Klartext gespeichert und indexiert → der
  Lookup ist ein einzelner Index-Treffer statt eines Scans über alle Keys.
- `secret`: 32 zufällige Bytes (`secrets.token_urlsafe(32)`).
- Gespeichert wird `sha256(secret)`, verglichen mit `hmac.compare_digest`.

**Warum SHA-256 und nicht PBKDF2**: die 390.000 Iterationen in `security.py`
sind für Passwörter richtig, weil Passwörter wenig Entropie haben. Ein Token
mit 256 Bit Entropie ist gegen Offline-Brute-Force auch mit einem einfachen
Hash unangreifbar — und PBKDF2 pro Request wäre bei einem Agenten, der Dutzende
Tool-Calls hintereinander absetzt, nicht bezahlbar. Der Basic-Auth-Cache aus
Issue #92 wird für Keys damit gar nicht erst gebraucht.

Das vollständige Token wird **genau einmal** bei der Erzeugung zurückgegeben und
danach nirgends mehr — weder in der API noch im Log. In Logs erscheint
höchstens der `prefix`.

## Integration in die Auth-Kette

`require_permission()` in `core/security.py` bekommt einen dritten Zweig, vor
den bestehenden Cookie- und Basic-Prüfungen:

1. `Authorization: Bearer rdb_<prefix>_<secret>` → Key über `prefix` laden,
   Hash vergleichen, `revoked_at`/`expires_at` prüfen → `User` + Key.
2. Session-Cookie (unverändert).
3. HTTP Basic (unverändert).

Effektive Rechte eines Key-Requests: `user.effective_permissions ∩ scopes`
(bei `scopes IS NULL`: die Rechte des Nutzers). **Der Super-Admin-Bypass aus
`User.has_permission()` greift bei Key-Auth nicht** — sonst wäre ein Key eines
Admins durch `scopes` nicht einschränkbar, und genau das ist der Zweck von
`scopes`. Das ist der einzige Punkt, an dem sich Key-Auth vom bisherigen
Verhalten unterscheidet, und muss beim Umbau explizit getestet werden.

Fehlerfälle: kein/ungültiges Token → `401` mit `WWW-Authenticate: Bearer`
(die Stelle, an die später die `resource_metadata`-Angabe für OAuth gehört);
gültiges Token ohne die nötige Capability → `403`.

`last_used_at` wird **gedrosselt** geschrieben (höchstens einmal pro Minute pro
Key), damit nicht jeder Tool-Call einen DB-Write auslöst.

## Key-Verwaltung

Neuer Router `api/v1/endpoints/api_keys.py` unter `/api/v1/api-keys`:

| Methode | Pfad | Wirkung |
|---|---|---|
| `GET` | `/api-keys` | eigene Keys (Metadaten, nie das Token) |
| `POST` | `/api-keys` | Key anlegen → Antwort enthält das Token **einmalig** |
| `DELETE` | `/api-keys/{id}` | widerrufen (setzt `revoked_at`) |

Jeder eingeloggte Nutzer verwaltet seine eigenen Keys — dafür braucht es keine
neue Capability. Fremde Keys sehen und widerrufen darf nur, wer `user.manage`
hat (Admin-Bereich). Ein Key-Request darf die Key-Verwaltung **nicht** bedienen
(kein Selbst-Eskalationspfad): diese Endpunkte verlangen Cookie oder Basic.

Frontend: neue Sektion in der Benutzerverwaltung (`features/admin/`) mit
Anlege-Dialog, einmaliger Token-Anzeige samt Kopier-Button und Warnhinweis,
Liste mit `name`, `prefix`, `last_used_at`, `expires_at` und Widerruf-Aktion.
Nach den Backend-Änderungen `make gen-api` laufen lassen.

## MCP-Server

- **Bibliothek**: offizielles Python-SDK `mcp` (aktuell `2.2.0`, Python ≥ 3.10,
  Backend läuft auf 3.13), exakt gepinnt in `requirements.txt` wie alle anderen
  Abhängigkeiten. Es deckt Streamable HTTP ab; die konkrete ASGI-Mount-API ist
  bei der Umsetzung gegen die v2-Doku zu prüfen (v1-Beispiele aus dem Netz
  passen nicht mehr).
- **Ort**: `apps/backend/dashboard_backend/mcp/` — `server.py` (Server-Instanz
  und Mount), `tools/` (ein Modul je fachlichem Bereich).
- **Mount**: als ASGI-App unter `/mcp` in `main.py`, neben
  `app.include_router(api_router, prefix="/api/v1")`.
- **Zustand**: stateless betreiben, solange möglich — das Backend läuft
  potenziell mit mehreren Uvicorn-Workern, und eine im Prozess gehaltene
  Session würde bei Lastverteilung brechen.
- **Kontext**: jeder Tool-Aufruf löst den `User` aus dem Bearer-Token des
  Requests auf und prüft die Capability, bevor er die CRUD-Schicht ruft. Es
  gibt keinen Service-Account und keinen Fallback auf einen „System"-Nutzer.

### Tool-Katalog (erste Ausbaustufe)

| Tool | Wirkung | benötigte Capability |
|---|---|---|
| `list_project_groups` | Projektgruppen mit Projektanzahl, optional per Freitext | — (eingeloggt) |
| `list_projects` | Projekte suchen/filtern (archivierte mit `archived` only/include, dann mit `is_archived` und `replaced_by_project_id`; Text in Name, Nummer, Beschreibung und Aliasen; Projektgruppe(n), Phase, Planungsstand bekannt, Geometrie, Länge, Lebenszyklus, Parl. Befassung, geändert seit, Termin offen), sortieren; je Eintrag Bau- und IB-Termin als `{date, precision, text}`, filterbar über `construction_start`/`commissioning` (eine Untergrenze trifft nie einen Zeitraum); `with_description` liefert je Eintrag den ersten Satz der Beschreibung und die Aliase | — (eingeloggt) |
| `list_project_filters` | Katalog der Filter von `list_projects`: Felder, Typen, Operatoren, Enum-Werte | — |
| `get_project` | Projektdetail inkl. BVWP-Daten und Unterprojekten | — |
| `get_project_progress` | Planungsstand inkl. Beobachtungen und Prognose; `forecast.ibn_doubt`, wenn die GVFG-Finanzreihe nach dem IBN-Jahr noch Mittel vorsieht | — |
| `list_project_finves` | Finanzierungsvereinbarungen und Budgets eines Projekts; `include_subprojects` nimmt die FinVe aller Teilprojekte dazu (jede einmal, mit tragenden Teilprojekten) | — |
| `list_finves` | FinVe frei suchen — auch ohne Projektzuordnung: FinVe-Nummer, Name, Bedarfsplannummer, lfd. Nr.; Filter Haushaltsjahr, Sammel-FinVe, mit/ohne Projekt | — |
| `get_finve` | eine FinVe per Nummer mit Budgethistorie und verknüpften Projekten | — |
| `update_finve_projects` | Projekte einer FinVe hinzufügen und entfernen, auch bei bereits zugeordneten FinVe; nur feste Verknüpfungen (Jahres-Links der Sammel-FinVe bleiben); Änderungsprotokoll je Projekt (`finve_ids`, zurücksetzbar) und Neuberechnung des Planungsstands (`docs/features/feature-finve-zuordnung.md`) | `finve.edit` |
| `list_haushalt_years` · `list_haushalt_finves` · `suggest_haushalt_finve_projects` | Haushalt-Nacharbeit lesen: Jahre mit offenen FinVes/Zeilen und Importläufen, FinVes eines Jahres mit Jahres-Projekten und Erläuterung, Kandidaten mit Gründen (siehe `feature-haushalt-import.md` → „Nacharbeit per MCP“) | — |
| `set_sammel_finve_year_projects` | Projekte einer Sammel-FinVe für ein Haushaltsjahr setzen (optional Folgejahre), Änderungsprotokoll `sammel_finve_years` (zurücksetzbar), Neuberechnung des Planungsstands | `finve.edit` |
| `list_haushalt_unmatched_rows` · `resolve_haushalt_unmatched_row` | offene Zeilen des Haushaltsimports lesen und einer FinVe zuweisen | `haushalt.import` |
| `list_gvfg_programs` | GVFG-Ausgaben mit Jahresspalten, Zahl der Vorhaben und der Vorhaben ohne Projekt | — |
| `list_gvfg_entries` | Vorhaben einer Ausgabe (Standard: neueste) suchen: Schlüssel in jeder Schreibweise, Name, Stadt; Filter Land, kommunal/DB, Teil, Fördertatbestand, mit/ohne Projekt | — |
| `get_gvfg_entry` | ein Vorhaben mit ∑/A/B/C-Zeilen und Verlauf desselben Schlüssels über alle Ausgaben | — |
| `list_project_gvfg` | GVFG-Förderung eines Projekts über alle Ausgaben, optional mit direkten Teilprojekten; `ibn_doubt` wie in der Prognose | — |
| `assign_gvfg_entry` | Projekte eines Vorhabens setzen (ersetzt die bisherigen), optional für alle Ausgaben; ergänzt die Gruppen „GVFG“/„GVFG BW“ | `assignment.manage` |
| `get_project_infraplan` | Infraplan-Einträge eines Projekts über alle Jahrgänge, Gesamtkostenprognose, „nicht mehr im Infraplan“ | — |
| `list_infraplan_drafts` · `get_infraplan_draft` (auch `compact`) · `get_infraplan_page_text` · `suggest_infraplan_kpi_values` · `get_infraplan_page_image` · `list_infraplan_kpis` · `get_infraplan_kpi_values` | Infraplan-Import lesen: Entwürfe mit Warnungen, Zeilen mit Vorschlägen (kompakt über alle Abschnitte), Seitentext mit Positionen, Kennzahl-Vorschläge aus dem Text, Seitenbild (Bild-Content), Kennzahlen (siehe `feature-infraplan-import.md` → „MCP & Skill“, „Ausbau für den Import 2027“) | `infraplan.import` |
| `start_infraplan_parse` · `apply_infraplan_suggestions` · `assign_infraplan_row(s)` · `create_infraplan_subproject(s)` · `confirm_infraplan_import` · `set_infraplan_kpi_values` | Infraplan-Import führen: neu auslesen, Vorschläge übernehmen, begründet zuordnen (`AGENT`, einzeln oder gesammelt mit Ergebnis je Zeile), Teilprojekt oder eigenständiges Entwurfsprojekt anlegen (auch nach der Bestätigung), bestätigen (nie bei Parser-Warnungen), Kennzahlen ungeprüft schreiben | `infraplan.import` |
| `get_project_texts` | Projekttexte nach Typ, mit Kategorie, Sichtbarkeit und Anhängen (Metadaten) | — |
| `read_text_attachment` · `get_text_attachment_image` | Inhalt eines Anhangs lesen: PDF seitenweise als Text (höchstens 10 Seiten je Aufruf, `next_page`, Seiten ohne Textebene in `empty_pages`), Word (.docx) als Text; PDF-Seite oder PNG/JPEG als Bild. Alte Office-Formate und Tabellen nur in der Oberfläche; kein Upload, kein Löschen (#338) | — |
| `list_text_types` | Texttypen (für `text_type_id`) | — |
| `list_text_categories` | Textkategorien mit Stil (für `category_id`) | — |
| `list_todos` | Aufgaben, gefiltert (u. a. `tag`, Textsuche `search`), seitenweise mit `limit`/`offset` | — |
| `list_todo_tags` | Alle Aufgaben-Tags mit Beschreibung und Anzahl; „@LLM“ = vom LLM über MCP zu erledigen, mit „@Jonas“ zusammen erst nach Jonas’ Teil | — |
| `create_project` | Projekt/Unterprojekt anlegen (final, ohne Geometrie) | `project.create` |
| `compute_project_length` | Länge aus der Geometrie berechnen, optional übernehmen | — / `project.edit` mit `apply` |
| `update_project` | Projektfelder ändern | `project.edit` |
| `set_project_draft` | Projekt zum Entwurf machen oder Entwurf fertigstellen | `project.edit` |
| `archive_project` | Ersetztes/überholtes Projekt archivieren (Pflicht-Begründung, optional `replaced_by_project_id` = Nachfolger: Verweis in beide Richtungen, Vorjahres-Vorschläge der Importe gehen an ihn); zählt danach nirgends mehr, abgelehnt bei fester FinVe-Zuordnung, GVFG-Zuordnung, aktiven Teilprojekten oder ABGEBROCHEN (Sammel-FinVe-Jahresverknüpfungen blockieren nicht, sie bleiben als Historie und stehen in `kept_links.sammel_finve_year_links`); Änderungsprotokoll (siehe `feature-project-archive.md`) | `project.delete` |
| `unarchive_project` | Archiviertes Projekt wiederherstellen (Begründung optional), Änderungsprotokoll | `project.delete` |
| `create_project_group` | Neue Projektgruppe anlegen (Name, eindeutiger Kurzname, Farbe, Sichtbarkeit); Duplikate (Kurzname/Name) werden abgelehnt | `projectgroup.create` |
| `set_project_groups` | Projekt Gruppen hinzufügen/entfernen (id, Kurzname, Name) | `project.edit` |
| `add_progress_observation` | Planungsstand-Beobachtung ergänzen, mit `date_precision` (EXACT Default, MONTH, YEAR, NOT_BEFORE, ASSUMED) und optionalem `date_label` | `progress.edit` |
| `update_progress_observation` | manuelle Beobachtung in place ändern (Präzision, Terminzusatz, Datum, Notiz, Vertrauen, erwartet), mit Änderungsprotokoll; abgeleitete nicht | `progress.edit` |
| `delete_progress_observation` | manuelle Beobachtung löschen (abgeleitete nicht) | `progress.edit` |
| `set_phase_override` | manuellen Phasen-Override setzen (mit Begründung) oder aufheben | `progress.edit` |
| `set_project_lifecycle` | Lebenszyklus setzen: AKTIV, PAUSIERT oder ABGEBROCHEN (PAUSIERT/ABGEBROCHEN mit Pflicht-Begründung `note` und optionalem „seit“-Datum `since`; AKTIV leert beides), mit Änderungsprotokoll | `progress.edit` |
| `update_progress_tracks` | Planfeststellung und parlamentarische Befassung pflegen (`changes`: `has_planfeststellung`, `pf_state_override`, `pf_text`, `pf_date`, `pf_links`, `parl_befassung_relevant`, `parl_state_override`, `parl_befassung_text`, `parl_drucksache_url`, `parl_befassung_date`, `clear_*`), mit Änderungsprotokoll | `progress.edit` |
| `upsert_project_text` | Projekttext anlegen/ändern, inkl. Kategorie (Standard „Info“) und `is_public` | `projecttext.edit` |
| `merge_projects` | Dublette in ein anderes Projekt überführen (Vorschau, mit `apply` ausführen; destruktiv) | `project.merge` |
| `search_operational_points` | Betriebsstellen nach Name/op_id suchen (Wegpunkte, Stationen) | — |
| `get_project_geometry` | Geometrie-Übersicht je Feature (Index, Typ, Länge, Station), GeoJSON auf Wunsch | — |
| `route_project_geometry` | Route über GraphHopper berechnen (Vorschau), mit `apply` anhängen/ersetzen | `project.edit` |
| `edit_project_geometry` | Linien/Punkte aus Koordinaten, Betriebsstellen als Punkte, Features löschen | `project.edit` |
| `list_data_gaps` | Projekte mit fehlenden/veralteten Daten, Lücken je Projekt und Zählung (siehe *Datenpflege*) | — |
| `check_geometry` | Geometrie-Plausibilität für ein Projekt oder eine Gruppe (siehe *Datenpflege*) | — |
| `check_project_data` | Prüfliste Stammdaten: doppelte Projektnummern, namensgleiche Teilprojekte, GVFG-Ländercode ≠ Land, Teilmaßnahmen ohne Namen (siehe `feature-infraplan-import.md` → „Datenqualität“) | — |
| `get_project_changelog` · `get_project_text_changelog` | Änderungsprotokoll eines Projekts bzw. seiner Texte, neueste zuerst, Filter Feld/Text/seit, seitenweise; Geometriewerte nur als Größe, lange Werte gekürzt; je Änderung `entry_id` | — |
| `revert_project_change` | ein Feld auf den protokollierten alten Wert zurücksetzen — wie der Knopf in der Oberfläche (`services/changelog_revert.py`, gemeinsam mit `POST /projects/{id}/changelog/revert`), schreibt REVERT | `project.edit`, für FinVe-/Sammel-FinVe-Felder zusätzlich `finve.edit` |
| `get_todo` | eine Aufgabe, mit `history=true` samt Verlauf | — |
| `delete_project_text` | Projekttext samt Anhängen löschen (verschwindet aus allen verknüpften Projekten, `linked_projects` nennt sie); Löschung im Text-Änderungsprotokoll mit altem Inhalt | `projecttext.edit` |
| `update_project_group` | Einstellungen einer Projektgruppe ändern (Name, Kurzname, Beschreibung, Farbe, Sichtbarkeit, übersprungene Phasen, angenommene Bauzeit); Löschen nur in der Oberfläche | `projectgroup.edit` |
| `get_project_group_timeline` | Zeitleiste einer Gruppe (datierte Meilensteine je Projekt, wie `GET /project_groups/{id}/timeline`) | — |
| `list_project_documents` · `set_track_document` | Dokumente eines Projekts mit ihren Strängen; Dokument an PF/PARL hängen oder lösen (Änderungsprotokoll) | — / `progress.edit` |
| `recompute_project_progress` | Planungsstand eines Projekts sofort neu berechnen | `progress.edit` |
| `list_progress_conflicts` | Rücksprung-Konflikte über alle Projekte (wie Admin → Konflikte), seitenweise | `progress.edit` |
| `list_sammel_finve_phases` · `set_sammel_finve_phase` | Sammel-FinVes mit erkannter, manueller und wirksamer Phase; Phase setzen/lösen, verknüpfte Projekte werden neu berechnet | — / `progress.edit` |
| `list_media_reports` · `add_media_report` · `update_media_report` · `delete_media_report` | Medienberichte lesen und schreiben, die der Agent selbst gelesen hat (kein Abruf, keine Extraktion auf dem Server); erst bestätigt mit Projekt und Phase entsteht die MEDIEN-Beobachtung (Trust 0.4); gleiche URL am selben Projekt abgelehnt; Skill `medien-import` | `progress.edit` |
| `list_politicians` · `get_politician` · `list_constituencies` · `get_constituency` · `get_project_constituencies` | Wahlkreise und Abgeordnete lesen (beide Arbeitsrichtungen aus `feature-abgeordnete.md`), je Antwort `data_status` (letzter Abruf, veraltet); kein Import über MCP | — |
| `get_system_status` | Routing (GraphHopper) und Celery-Worker erreichbar? Ohne Zugangsdaten | `settings.manage` |
| `list_bauportal_entries` · `get_bauportal_entry` · `assign_bauportal_entry` | DB-Bauportal-Einträge lesen (Filter Titel, Projekt, unbestätigt, ohne Projekt; einzeln mit `raw_json` und abgeleiteter Phase) und Zuordnung setzen/lösen/bestätigen wie `PATCH /import/bauportal/entries/{id}`; Bestätigen materialisiert die BAUPORTAL-Beobachtung neu. Der Abruf der externen API bleibt im Admin-Bereich. Eine abgeleitete BAUPORTAL-Beobachtung in `get_project_progress` trägt `bauportal_status_id` und `bauportal` (id, Titel, Link) | `progress.edit` |
| `list_skills` | Skills für die Arbeit über den MCP (Name, Beschreibung), siehe *Skills über MCP* | — |
| `get_skill` | Anleitung eines Skills (Text der `SKILL.md`, optional eine Begleitdatei) | — |
| `create_todo` | Aufgabe anlegen, optional mit `tags` | `todo.create` |
| `update_todo` | Aufgabe ändern; `tags` ersetzt die Tag-Menge | `todo.edit` |
| `update_todo_tag` | Tag umbenennen oder Beschreibung ändern (Umbenennung im Verlauf jeder Aufgabe); Löschen nur in der Oberfläche | `todo.edit` |

Bewusst schmal gehalten: ein Tool je Absicht, keine generischen
„führe-beliebige-Abfrage-aus"-Tools. Ausgaben sind kompakt zu halten (Listen
paginiert, Geometrien nur zusammengefasst — Volltext nur auf ausdrücklichen
Wunsch per `get_project_geometry`), weil jede Antwort im Kontextfenster
des Clients landet.

## Konfiguration & Deployment

- Neue `Settings`-Felder (`core/config.py`): `mcp_enabled: bool = True`.
  Optionale Felder brauchen keinen conftest-Eintrag — **würde ein Pflichtfeld
  dazukommen, muss es in `apps/backend/tests/conftest.py` einen
  `os.environ.setdefault(...)` bekommen**, sonst bricht der CI-Test-Gate auf
  einem sauberen Checkout ohne `.env`.
- `apps/frontend/nginx.conf`: `location = /mcp` analog zu `/api/`, zusätzlich
  `proxy_buffering off;` und ein erhöhtes `proxy_read_timeout` — Streamable HTTP
  hält langlebige Verbindungen, die nginx sonst puffert oder abschneidet.
- Kein neuer Compose-Service, keine Änderung an den GHCR-Images außer der neuen
  Python-Abhängigkeit.
- Neue Konfiguration in `.env.prod.example` dokumentieren.
- `CHANGELOG.md` und `docs/production_setup.md` nachziehen (nginx-Regel ist
  deploy-relevant).

Client-seitig (Claude Code, `.mcp.json`):

```json
{
  "mcpServers": {
    "raildashboard": {
      "type": "http",
      "url": "https://<host>/mcp",
      "headers": { "Authorization": "Bearer rdb_..." }
    }
  }
}
```

## Sicherheit

- Token nur über HTTPS; der Key steht beim Client im Klartext in einer
  Config-Datei — deshalb sind Ablaufdatum und Widerruf Pflichtfunktionen und
  kein Nice-to-have.
- Schreib-Tools sind doppelt gegated: Capability des Nutzers **und** `scopes`
  des Keys. Empfehlung in der UI: für Agenten-Zugriff standardmäßig einen
  Read-only-Key anlegen.
- Kein Token, kein Prefix-plus-Secret und keine Passwörter in Logs oder
  Fehlermeldungen.
- Schreibende Tools schreiben wie die REST-Endpunkte in den `change_log`, damit
  Agenten-Änderungen nachvollziehbar und über die bestehende Revert-Funktion
  rücknehmbar bleiben.
- Ein Key-Request kann keine Keys verwalten (siehe oben).

## Tests

- `security.py`: gültiger Key, unbekannter Prefix, falsches Secret,
  widerrufener Key, abgelaufener Key, `scopes`-Schnittmenge, kein
  Admin-Bypass bei Key-Auth.
- Key-Endpunkte: Token erscheint genau einmal; fremde Keys nur mit
  `user.manage`; Key-Auth wird an der Key-Verwaltung abgewiesen.
- MCP-Tools: je ein Lese- und ein Schreib-Tool end-to-end mit Key;
  Schreib-Tool ohne Capability → Fehler; Schreib-Tool mit Read-only-Key →
  Fehler.
- Bestehende Auth-Tests müssen unverändert grün bleiben (Cookie und Basic
  dürfen sich nicht ändern).

## Akzeptanzkriterien

**Phase 1 — API-Keys als Auth-Weg**

- [x] Tabelle `api_keys` + Migration (`20261007001`); `make migrate` gegen
      eine echte DB steht als manueller Test aus.
- [x] `Authorization: Bearer …` authentifiziert gegen die gesamte REST-API.
- [x] `scopes` schränken die Rechte ein, auch bei einem Admin-Nutzer.
- [x] Widerrufener oder abgelaufener Key → `401`.
- [x] Key-Endpunkte inkl. einmaliger Token-Anzeige; Key-Auth dort abgewiesen.
- [x] Admin-UI zum Anlegen, Ansehen und Widerrufen; `make gen-api` gelaufen.
- [x] Cookie- und Basic-Auth verhalten sich unverändert.

**Phase 2 — MCP-Server**

- [x] `/mcp` antwortet über Streamable HTTP und listet die Tools aus dem
      Katalog.
- [ ] Claude Code verbindet sich mit einem Key aus `.mcp.json` und ruft
      erfolgreich ein Lese-Tool auf. *(manueller Test gegen die laufende
      Instanz; automatisiert per JSON-RPC in `tests/api/test_mcp_server.py`)*
- [x] Schreib-Tools respektieren Capability *und* Key-Scopes.
- [x] Schreibende Tools erzeugen `change_log`-Einträge.
- [x] nginx-Regel für `/mcp` steht; `docs/production_setup.md` und
      `CHANGELOG.md` nachgezogen.
- [x] `mcp` exakt gepinnt; Backend-Tests grün.

## Offene Punkte (geklärt)

- **Ablaufzeit**: jeder neue Key läuft nach **90 Tagen** ab (mit dem Nutzer
  entschieden, 2026-10-07). Es gibt keine Auswahl — wer länger braucht, legt
  einen neuen Key an.
- **Scopes in der UI**: zwei Presets — „Nur lesen" (Default, `scopes =
  ["mcp.access"]`) und „Wie mein Nutzer" (`scopes = NULL`). Die API nimmt
  weiterhin eine freie Liste gültiger Capability-Keys an.
- **Filter von `list_projects`**: Freitext (Name, Projektnummer, Beschreibung, Aliase), Projektgruppe
  (id, Kurzname oder Name, ohne Groß-/Kleinschreibung; eine Liste verlangt alle
  Gruppen), Planungsphase, übergeordnetes Projekt, Paginierung. Die Gruppen selbst
  findet `list_project_groups`. Weitere Bedingungen über `filters` (siehe *Generische
  Projektfilter*).
- **Planungsstand korrigieren** (2026-10-11): `set_phase_override` setzt den
  manuellen Phasen-Override wie das Formular im Planungsstand-Panel — nur mit
  Begründung (`note` → `manual_override_note`), `phase = null` hebt ihn auf.
  `delete_progress_observation` löscht manuelle Beobachtungen; abgeleitete
  (`is_derived`, aus den Importen) bleiben wie in der REST-API geschützt.
- **Lebenszyklus und Nebenspuren** (2026-10-31): Bis dahin ließ sich über MCP nur
  die Phase korrigieren; ein abgebrochenes Projekt (z. B. Stadtbahn Regensburg nach
  dem Bürgerentscheid) musste im Frontend umgestellt werden. `set_project_lifecycle`
  setzt den Lebenszyklus wie der Schalter im Planungsstand-Panel; PAUSIERT und
  ABGEBROCHEN brauchen über MCP eine Begründung (`note` → `lifecycle_note`), damit
  die Quelle festgehalten ist. `update_progress_tracks` pflegt die Blöcke
  Planfeststellung und parlamentarische Befassung über denselben Schreibweg
  (`PATCH /projects/{id}/progress`); Phasen-Override und Lebenszyklus lehnt es ab
  und verweist auf die eigenen Werkzeuge.
- **Projekte zusammenführen** (2026-10-14): `merge_projects(survivor_id, merged_id,
  geometry_from, apply)` überführt eine Dublette in das bleibende Projekt und löscht
  sie; ihre alte id leitet über `project_redirect` weiter (`get_project` liefert dann
  das bleibende Projekt mit `redirected_from`, andere Tools nennen die neue id).
  Ohne `apply` nur die Vorschau. Eigene Capability `project.merge` (keine
  Systemrolle). Regeln: [`feature-project-merge.md`](feature-project-merge.md).
- **Projektgruppen** (2026-10-11): `set_project_groups(add, remove)` löst Gruppen
  wie `list_projects` auf und lässt übrige Zuordnungen stehen; `update_project`
  lehnt `project_group_ids` ab und verweist darauf. Gruppenwechsel landen — auch über
  REST/Oberfläche — als Feld `project_group_ids` (sortierte id-Liste) im
  `change_log` und sind über den bestehenden Revert rücknehmbar; die Historie zeigt
  die Kurznamen.
- **Projekte anlegen** (2026-10-11): `create_project` legt ein Projekt standardmäßig als Entwurf an
  (`final=true` = direkt fertig; seit #204), typischerweise als Etappe mit `superior_project_id`; Gruppen per
  id/Kurzname/Name, weitere Felder über `fields` wie bei `update_project`. Geometrie
  und Entwurfs-Flag sind in `fields` gesperrt (Flag: `set_project_draft`; `list_projects` und
  `list_data_gaps` haben den Filter `drafts` = exclude/only/include). Die Anlage steht als `CREATE`-Eintrag (ein Feld je
  gesetztem Wert, Gruppen als id-Liste) im `change_log`; die Historie bietet dafür
  kein „Zurücksetzen“ an.
- **Länge aus Geometrie** (2026-10-11): `compute_project_length` rechnet wie der
  Knopf „Länge aus Geometrie berechnen“ (Python-Port von `shared/geo/length.ts` in
  `services/geo_length.py`, Haversine, 0,01 km) und liefert berechnete und
  gespeicherte Länge; die Geometrie selbst bleibt außen vor. `apply=true` schreibt
  den Wert über den `change_log` ins Feld `length`.
  **Konvention** (mit dem Nutzer entschieden, 2026-10-11): `length` kommt aus der
  Geometrie, nicht aus veröffentlichten DB-Angaben (die anders messen). Server-
  Instructions sowie die Beschreibungen von `compute_project_length` und
  `update_project` sagen das dem Client.
- **Planungsstand im `change_log`** (2026-10-11): Jede Planungsstand-Änderung —
  Flags, Overrides, PF-/Parlaments-Angaben, Beobachtung angelegt/gelöscht,
  Dokument verknüpft/gelöst — schreibt die CRUD-Schicht (`crud/projects/progress.py`)
  in den Projekt-`change_log`, egal ob über REST/Oberfläche oder MCP. Feldnamen
  tragen das Präfix `progress.` (z. B. `progress.manual_phase_override`,
  `progress.observation` mit einer lesbaren Zeile zur Beobachtung); die Historie
  zeigt sie als „Planungsstand“. Sie sind reine Historie: Der Revert-Endpunkt
  akzeptiert nur Projektfelder, die Oberfläche blendet „Zurücksetzen“ dort aus.

- **Geometrie und Routing** (2026-10-12): Das MCP bekommt dieselben Werkzeuge wie der
  `GeometryEditor` (`mcp/tools/geometry.py`):
  - `search_operational_points` (Name/op_id, exakte Treffer zuerst) liefert die Wegpunkte.
  - `route_project_geometry(waypoints, mode, add_stations, apply)`: Wegpunkte sind
    Betriebsstellen (id, op_id oder exakter Name; mehrdeutige Namen → Fehler mit
    Kandidaten) oder freie Koordinaten `{lat, lon}`; Zwischenpunkte erzwingen den Korridor.
    Ohne `apply` nur Vorschau (Distanz, Dauer, aufgelöste Wegpunkte, Ergebnis-Geometrie);
    mit `apply` wird die Linie angehängt (`append`) oder ersetzt (`replace`); die
    Betriebsstellen kommen nur mit `add_stations: true` als Punkte dazu (Standard: aus,
    wie der Schalter im UI; ohne Dublette per `op_id`), und die
    Route wird wie bei „Übernehmen“ in `routes` gespeichert. Der `RouteService` wird pro
    Request wie die DB-Session in den Scope gelegt (in Tests: der Routing-Stub).
  - `edit_project_geometry`: `replace` (allein: Geometrie leeren) oder
    `remove_feature_indices` (Indizes aus `get_project_geometry`), dann `add_features`
    (Feature, Geometrie oder FeatureCollection; Point/MultiPoint/LineString/
    MultiLineString, `[lon, lat]`) und `add_operational_points`. Koordinaten außerhalb
    Deutschlands ergeben eine Warnung („lon/lat vertauscht?“), ungültige einen Fehler.
  - `get_project_geometry`: Zusammenfassung je Feature und gespeicherte Routen; das volle
    GeoJSON (auf ~1 m gerundet) nur mit `include_geojson`, weil lange Routen groß sind.
  - Geschrieben wird über `update_project` mit `change_log`-Eintrag
    (`geojson_representation`), also im UI rücknehmbar; Elternprojekte werden wie bisher
    neu aggregiert. Projekte, deren Geometrie aus den Unterprojekten entsteht, lehnen beide
    Schreib-Tools ab (wie die REST-Prüfung); abschalten über
    `update_project {"geojson_from_subprojects": false}`. Die Länge bleibt ein eigener
    Schritt (`compute_project_length`), das Ergebnis enthält dafür einen Hinweis.

## Umsetzungsstand (2026-10-07)

- **Nur Admins (vorerst)**: Neue Capability **`mcp.access`** („API-Keys &
  MCP-Zugriff", Gruppe Administration). Sie ist keiner Systemrolle zugewiesen,
  also hält sie nur der Super-Admin `admin`; später lässt sie sich über eine
  eigene Rolle in `/admin/roles` vergeben. Sie gatet zwei Dinge: das **Anlegen**
  von Keys (`POST /api-keys`) und den Zugang zu **`/mcp`** (der Key selbst muss
  `mcp.access` tragen — ein Key mit `scopes` ohne `mcp.access` kommt nicht an
  MCP heran). Eigene Keys auflisten und widerrufen geht mit jedem Login, damit
  ein Key auch nach Entzug der Capability widerrufbar bleibt.
- **Key-Verwaltung** zusätzlich `GET /api-keys/all` (alle Keys, `user.manage`).
  Fremde Keys widerrufen nur mit `user.manage`, sonst `404`. Key-Requests an die
  Key-Verwaltung → `403`.
- **REST**: `require_permission()` und `require_auth()` akzeptieren Bearer-Keys
  vor Cookie und Basic; Rechte = Nutzer-Rechte ∩ `scopes`, ohne Admin-Bypass.
- **MCP-Endpunkt**: SDK `mcp==2.3.0` (`MCPServer`), Streamable HTTP unter
  `/mcp`, `stateless_http` + `json_response`. Eine eigene ASGI-Middleware
  (`mcp/auth.py`) prüft den Bearer-Key (nur Bearer — kein Cookie, kein Basic)
  und legt den Principal in den Request-Scope; die Tools lesen ihn über den
  SDK-`Context`. Weil der SDK-Session-Manager nur einmal pro Instanz startbar
  ist, baut `McpEndpoint` den Server in jedem App-Lifespan neu. Der
  DNS-Rebinding-Schutz des SDK ist aus, weil ohne Cookies nichts zu holen ist
  (er würde sonst jeden Nicht-localhost-Host ablehnen).
- **Tool-Katalog** wie oben (`list_text_types`/`list_text_categories` liefern
  die ids für `upsert_project_text`). Lese-Tools tragen
  `readOnlyHint`. `update_project` sperrt `geojson_representation` und
  `is_draft`. Changelog-Einträge entstehen wie bei den REST-Endpunkten: für
  Projektfelder und Projekttexte; Beobachtungen tragen den Nutzernamen,
  Aufgaben `created_by`.
- **Frontend**: Seite `/admin/api-keys` („API-Keys & MCP", gated mit
  `mcp.access`) mit Anlege-Dialog, einmaliger Token-Anzeige samt fertiger
  `.mcp.json`-Konfiguration, Widerruf und — mit `user.manage` — der Liste aller
  Keys.

## Datenpflege über viele Projekte (#175, Stufe A)

Ohne diese Werkzeuge müsste das LLM für eine Lückenanalyse jedes Projekt einzeln abrufen.
Beide sind lesend; behoben wird mit den bestehenden Schreib-Werkzeugen. Code:
`mcp/tools/data_quality.py`, die Prüflogik in `services/geometry_check.py`.

**`list_data_gaps(project_group?, gaps[], stale_years=3, limit, offset)`** — Entwürfe
ausgenommen; ein Projekt erscheint, wenn mindestens eine der gewählten Lücken zutrifft
(Standard: alle). Antwort: `counts` je Lücke über alle Treffer, eine Seite Projekte mit `gaps`.

| Lücke | Bedeutung |
|---|---|
| `no_geometry` | keine Linie und kein Punkt gespeichert (auch leere FeatureCollection) |
| `no_route` | Geometrie vorhanden, aber keine gespeicherte GraphHopper-Route (skizziert oder von Hand gezeichnet); Oberprojekte, deren Geometrie aus den Unterprojekten kommt, zählen nicht |
| `no_length` | `length` leer oder 0 |
| `unknown_phase` | Planungsstand unbekannt: kein Override und keine glaubwürdige Beobachtung (Semantik von `stored_headline_phase`, auch ohne `project_progress`-Zeile) |
| `no_description` / `no_project_number` | Feld leer oder nur Leerzeichen |
| `stale_observation` | jüngste Beobachtung (`observed_date`, ohne erwartete Termine) älter als `stale_years`; Projekte ganz ohne Beobachtung fallen unter `unknown_phase` |

**`check_geometry(project_id | project_group, only_findings=true, gap_tolerance_km=0.05,
max_station_distance_km=3, limit, offset)`** — genau eines von `project_id` und
`project_group`. Jede Prüfung liefert einen Befund, kein Urteil (ein Programm aus
Einzelstationen zerfällt zu Recht in viele Teile):

| Befund | Regel |
|---|---|
| `chords` | Linienteile mit genau zwei Punkten und ≥ 0,2 km machen ≥ 50 % der Linienlänge aus (geroutete Linien haben alle paar Dutzend Meter einen Punkt). Beispiel #1907 HLK Stuttgart – Ulm: 58 von 59 Segmenten |
| `gaps` | Linienteile, deren Enden sich nicht bis auf `gap_tolerance_km` nähern, bilden getrennte Komponenten; die Lücken sind die Kanten eines minimalen Spannbaums zwischen den Komponenten (größte zuerst, mit Koordinaten) |
| `far_from_start` / `far_from_end` | Erster/letzter Ort im Projektnamen (Trenner: Gedankenstrich, oder Bindestrich mit Leerzeichen; Klammern entfallen; längster passender Wortausschnitt zuerst) wird über exakten Namen, sonst „<Name> Hbf“, zur Betriebsstelle aufgelöst; Befund, wenn kein Linienpunkt näher als `max_station_distance_km` liegt. Nicht auflösbare Orte stehen unter `unresolved_places` |
| `length_mismatch` / `length_missing` | gespeicherte vs. aus der Geometrie berechnete Länge (gleiche Rechnung wie `compute_project_length`); Abweichung > max(0,5 km, 2 %) |
| `overlaps` | Andere Projekte auf derselben Strecke (aus `project_overlap`, `feature-map-overlapping-geometries.md`): je Partner `project_id`, `name`, `shared_km`, `share_self`, `share_other`, größte zuerst, höchstens fünf, `total` zählt alle. Teilen beide ≥ 90 % ihrer Linie, trägt der Eintrag `possible_duplicate` (mögliche Dublette → `merge_projects`, erst ohne `apply`). Eigene Über- und Unterprojekte erscheinen nicht, ihre Überlappung ist gewollt |
| `no_geometry` / `no_line` | keine Geometrie bzw. nur Punkte |

Für eine Gruppe listet `only_findings` nur Projekte mit Befund; `checked` zählt alle
geprüften, `counts` die Befunde je Art.

**`list_projects`** bekommt dafür die Filter `is_known`, `has_geometry`, `has_length`,
`lifecycle_status` (ohne `project_progress`-Zeile gilt `AKTIV`), `parl_befassung_relevant`
(Override, sonst BSWAG*-Gruppe — wie `resolve_parl_relevant`), `closure` (Stilllegung;
ungesetzt zählt als `false`), `updated_since` (Eintrag im
Projekt-Changelog ab diesem Datum) sowie `order_by` (`name`, `id`, `length`, `last_change`)
und `descending`; Projekte ohne Länge bzw. ohne Änderung stehen immer am Ende. Jeder Eintrag
trägt `is_known`. Das Feld `phase` bleibt wie bisher (bei unbekanntem Stand der
`NICHT_GESTARTET`-Rückfallwert) — das zu ändern ist Teil von #172.

**Generische Projektfilter** (2026-10-20): Statt für jedes neue Merkmal einen Parameter
in `list_projects` zu ergänzen, gibt es eine Registry (`FilterField` in
`mcp/tools/projects.py`: Name, Typ, Operatoren, SQL-Ausdruck, Enum-Werte). Sie speist
- `list_projects(filters=[{field, op, value}, …])` — Bedingungen per UND, auch mit den
  benannten Parametern, die intern dieselbe Registry nutzen;
- `list_project_filters` — liefert den Katalog (Felder, Typen, Operatoren mit Erklärung,
  erlaubte Enum-Werte), damit das MCP selbst nachfragt statt Filter fest zu kennen.

Felder: `name`, `project_number`, `description` (Text: `eq`, `ne`, `contains`,
`not_contains`, `starts_with`, `ends_with`, `is_empty`, `not_empty`; ohne Groß-/Kleinschreibung,
`%`/`_` im Wert sind wörtlich), `closure` (Stilllegung; ungesetzt = `false`), `phase`,
`lifecycle_status` (Enum: `eq`, `ne`, `in`), `project_group` (`eq` = Mitglied, `ne`, `in` =
eine der Gruppen), `superior_project_id` (`eq`, `ne`, `is_empty` = oberste Ebene), `length`
(Zahl: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `is_empty`), `is_known`, `has_geometry`,
`has_length`, `parl_befassung_relevant` (Wahrheitswert: `eq`), `last_change` (Datum:
`gte`, `lte`; nie geänderte Projekte treffen keines). Whitelist statt freier Spalten: Entwürfe
(`is_draft`) und Geometrie-Blobs sind nie filterbar. Ein neues Feld wird nur in der Registry
ergänzt. `list_data_gaps` hat weiter feste Lückenarten; sie auf dieselbe Registry zu stützen
ist ein möglicher Folgeschritt.

**Stufe B und C** (Gruppen-Zusammenfassung, erwartete Meilensteine, Ortssuche,
Volltextsuche, Änderungs- und Beobachtungsverlauf, Sammel-Längenberechnung) sind noch nicht
umgesetzt; was davon kommt, wird in eigenen Issues entschieden.

## Ausbau 2026-10-31 (Lückenanalyse)

Eine Lückenanalyse REST ↔ MCP (2026-10-31) hat die fachlichen Funktionen gefunden, die
nur in der Oberfläche gingen. Umgesetzt wurde, was ein Agent sinnvoll braucht (Issues
#333–#336); Bauportal kam getrennt mit #293. Tools in der Katalogtabelle oben.

| Bereich | Tools | Issue |
|---|---|---|
| Wahlkreise und Abgeordnete (lesend) | `list_politicians`, `get_politician`, `list_constituencies`, `get_constituency`, `get_project_constituencies` | #333 |
| Änderungsprotokoll | `get_project_changelog`, `get_project_text_changelog`, `revert_project_change`, `get_todo` | #334 |
| Medien/Presse | `list_media_reports`, `add_media_report`, `update_media_report`, `delete_media_report`, Skill `medien-import` | #335 |
| Ergänzungen | `list_projects(archived)`, `delete_project_text`, Anhänge in `get_project_texts`, `update_project_group`, `get_project_group_timeline`, `list_project_documents`, `set_track_document`, `recompute_project_progress`, `list_progress_conflicts`, `list_sammel_finve_phases`, `set_sammel_finve_phase`, `get_system_status` | #336 |
| Anhänge lesen | `read_text_attachment`, `get_text_attachment_image` (`services/attachment_content.py`, nur pymupdf und Standardbibliothek) | #338 |

**Entscheidungen (mit dem Nutzer, 2026-10-31):**

- **Zurücksetzen über MCP** ist erlaubt — mit denselben Regeln wie der Knopf in der
  Oberfläche. Die Logik liegt in `services/changelog_revert.py` und wird von REST und
  MCP geteilt; das Zurücksetzen selbst steht wieder im Protokoll.
- **Projekttexte und Medienberichte löschen** ist über MCP erlaubt (Ausnahme zu „kein
  Löschen von Stammdaten“): Texte stehen mit ihrem alten Inhalt im Text-Protokoll,
  Medienberichte sind Importeinträge wie Fulda- oder VIB-Einträge.
- **Medien nach dem Fulda-Muster:** Der Agent liest den Artikel selbst; Abruf und
  Sprachmodell-Extraktion auf dem Server bleiben dem Frontend-Weg. Bestätigen darf der
  Agent wie bei Fulda — der Skill verlangt, dass jede bestätigte Aussage mit Zitat
  belegt ist.
- **Anhänge lesen ja, hochladen und löschen nein** (Nutzer, 2026-10-31): Inhalte von PDF
  und Word, Bilder als Bild; `.doc`, `.xls`, `.xlsx` bleiben ohne neue Abhängigkeit bei den
  Metadaten.
- **Routine-Abrufe** (Abgeordnetenstand, Bauportal) laufen nicht über MCP, sondern sollen
  zeitgesteuert laufen — Planung in eigener Session (`feature-routine-abrufe.md`, sobald
  angelegt).
- **Bewusst nicht über MCP:** Nutzer, Rollen, Rechte, API-Keys, Einstellungen (kein
  Weg zur Rechte-Ausweitung), Löschen von Projekten, Gruppen und Jahrgängen, PDF-Uploads
  (Haushalt, GVFG), Freigaben von Infraplan-Kennzahlen, Zustandsbericht und
  Haushalt-Abschluss (Mensch-im-Loop), Abgeordneten-Import und Neuverschneidung,
  Anleitungstexte, Texttypen/-kategorien und KPI-Definitionen anlegen.
- `set_sammel_finve_phase` berechnet die verknüpften Projekte sofort neu; der
  REST-Endpunkt `PATCH /finves/{id}/progress-phase` tut das (noch) nicht.

## Skills über MCP (2026-10-17)

**Problem:** Mehrstufige Abläufe (z. B. Infraplan-Import) brauchen eine Anleitung als
Skill. Von Hand nach claude.ai hochgeladene Skills veralten bei jeder Änderung im Repo,
und über die Claude-API hochgeladene Skills erscheinen in claude.ai nicht.

**Lösung:** Der MCP-Server liefert die Skills selbst aus. Quelle bleibt der eine Ordner
`.claude/skills/` (`AGENT.md` → „Skills“); er wird beim Bauen als zweiter Build-Kontext
`skills` ins Backend-Image kopiert (`/app/skills`). Damit entspricht der ausgelieferte
Text immer dem **deployten** Stand — ein Rollback nimmt die Anleitung mit zurück.

Mit dem Nutzer abgestimmt (Widerspruchs-Check, 2026-10-17):

| # | Frage | Entscheidung |
|---|---|---|
| W1 | „Upload nach claude.ai von Hand“ (`AGENT.md`, Skills-README, Infraplan Nr. 21) | ersetzt: Inhalt kommt vom MCP; von Hand hochgeladen wird nur noch der dünne Einstiegs-Skill `schienendashboard`, einmalig |
| W2 | Form — Resources/Prompts sind oben ausgeklammert | **Tools** (`list_skills`, `get_skill`); für claude.ai sind nur Tools sicher unterstützt. Der Ausschluss von Resources/Prompts bleibt |
| W3 | Wie kommt `.claude/skills/` ins Image (Kontext `apps/backend`)? | zusätzlicher **Named Build-Context** `skills=.claude/skills` in `Makefile`, `release.yml` und `compose.override.yaml`; keine Kopie im Repo |
| W4 | Welche Skills? | nur **markierte**: Frontmatter `metadata:` → `mcp: true`. Repo-Skills (`audit-auth`, `widerspruchs-check`) brauchen den Code und bleiben außen vor |

**Tools** (`mcp/tools/skills.py`, lesend, jeder Key mit `mcp.access`):

- `list_skills()` → `skills: [{name, description}]` aller markierten Skills.
- `get_skill(name, file?)` → `name`, `description`, `content` (Text der `SKILL.md` ohne
  Frontmatter) und `files` (Begleitdateien im Skill-Ordner). Mit `file` kommt statt der
  `SKILL.md` diese Begleitdatei; Pfade außerhalb des Skill-Ordners werden abgelehnt.
  Unbekannte oder nicht markierte Skills → Tool-Fehler.

**Fundort:** `/app/skills` im Image, sonst `.claude/skills/` im Checkout (lokaler
`uvicorn`, `make test-local`). Ein Build ohne Kontext `skills` schlägt fehl — gewollt,
damit kein Image stillschweigend ohne Skills ausgeliefert wird.

**Frontmatter:** einfache Form (`key: wert` je Zeile, `metadata:` mit eingerückten
Unterschlüsseln). Ein Test prüft alle Skills im Ordner (Name = Ordnername, Beschreibung
vorhanden), damit ein kaputter Skill `make test` bricht statt still zu verschwinden.

**Einstieg in claude.ai:** `.claude/skills/schienendashboard/` ist der einzige
hochgeladene Skill. Er sagt nur: bei Arbeit mit dem Schienendashboard-MCP erst
`list_skills`, dann `get_skill` und der Anleitung folgen. Er ändert sich praktisch nie.
Die `INSTRUCTIONS` des Servers weisen zusätzlich auf `list_skills` hin (wirkt in Claude
Code; ob claude.ai das Feld auswertet, ist nicht dokumentiert).

**Akzeptanzkriterien**

- [x] `list_skills` listet genau die markierten Skills, `get_skill` liefert Text und
      Begleitdateien, Pfad-Ausbrüche und unmarkierte Skills werden abgelehnt.
- [x] `make test` baut Test- und Runtime-Image mit Kontext `skills`; `release.yml` und
      `compose.override.yaml` ebenso.
- [ ] Nach dem nächsten Deploy liefert `list_skills` in claude.ai die markierten Skills
      (`fulda-runde`, `vib-import`, `infraplan-import`).

## Umsetzung

Zwei Issues, in dieser Reihenfolge:

1. **API-Keys als Auth-Weg** (`area:auth`, `type:backend`) — Phase 1 oben.
   Eigenständig nützlich, auch ohne MCP.
2. **MCP-Server** (`area:auth`, `type:integration`) — Phase 2 oben.
   `Depends on:` Issue 1.
