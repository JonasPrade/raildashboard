# Architekturanalyse Schienendashboard (Stand 2026-10-23, HEAD 83554c8)

Diese Analyse untersucht das gesamte Repository: Backend (FastAPI, SQLAlchemy, Celery, MCP), Frontend (React, Vite, Mantine), Infrastruktur (Compose, GitHub Actions, Deploy-Skripte), Tests, Datenbankschema und Dokumentation. Sieben parallele Tiefenprüfungen wurden durchgeführt, die wichtigsten Befunde anschließend am Code nachgeprüft. Zeilenangaben beziehen sich auf den genannten Commit. Nichts wurde verändert.

Was tatsächlich ausgeführt wurde:
- Backend: `pytest` im frischen venv, 1357 bestanden, 3 übersprungen, 155 s. `alembic heads` liefert genau einen Head (`20261023002`), keine Branches.
- Frontend: `npm ci`, `tsc --noEmit` (0 Fehler), `eslint` (0 Fehler, 31 Warnungen), `vitest` (303 Tests grün), `vite build` grün, `dist/index.html` lädt nur `vendor-react` vor.
- OpenAPI-Schema offline aus `main.py` erzeugt und gegen `types.gen.ts` verglichen: 0 Zeilen Differenz.

## 1. Kurzfassung

Das System ist in guter Grundverfassung: Tests grün, Typen synchron, Deploy-Weg durchdacht, Ableitungslogik des Planungsstands sauber als reiner Service mit dichter Testabdeckung. Die Probleme liegen nicht in einzelnen Bugs, sondern in vier wiederkehrenden Mustern:

1. Geschäftsregeln sitzen in der Transportschicht statt in CRUD/Services. Dieselbe Operation hat über REST und MCP unterschiedliche Regeln (Pflicht-Notiz, Changelog, Neuberechnung, Capability). Das ist die Wurzel der meisten Datenintegritätsbefunde.
2. Der Planungsstand wird materialisiert, aber nicht jeder Schreibpfad löst die Neuberechnung aus. VIB über REST, Haushalt-Confirm, Sammel-FinVe-Phasen und Projektlöschung hinterlassen bis zu 24 h veraltete Werte in Liste, Karte und MCP.
3. Autorisierung ist capability-basiert, hat aber drei Löcher: ein ungeschützter Schreibendpunkt, Scope-Umgehung bei API-Keys über `User.has_permission`, und Nutzernamen auf zwei öffentlichen GETs.
4. Die Dokumentation ist an über 40 Stellen widersprüchlich oder veraltet. Vier Agenten-Steuerdateien widersprechen sich gegenseitig; README beschreibt zwei verschiedene Deploy-Modelle.

Die zehn wichtigsten Befunde:

| Nr. | Schwere | Befund | Stelle |
|---|---|---|---|
| 1 | Hoch | `POST /projects/{id}/routes` hat keine Capability-Prüfung; jeder eingeloggte Viewer oder Read-only-Key kann Routen schreiben | `api/v1/endpoints/project_routes.py:73-94` |
| 2 | Hoch | API-Key-Scopes werden durch `current_user.has_permission(...)` umgangen (Admin-Bypass greift) | `api/v1/endpoints/projects.py:437`, `api_keys.py:74` |
| 3 | Hoch | Nutzernamen (`username_snapshot`) auf zwei öffentlichen GETs trotz Architekturregel | `project_progress.py:39-45`, `guides.py:26-29` |
| 4 | Hoch | Haushalt-Confirm übernimmt vom Browser gesendete Werte statt des gespeicherten Parse-Ergebnisses; VIB-Confirm ebenso und löscht danach den Draft | `haushalt_import.py:197-229`, `vib_import.py:225-236` |
| 5 | Hoch | Haushalt-Confirm schreibt FinVe-Links direkt: kein Changelog, keine Neuberechnung, keine Archiv-Prüfung | `haushalt_import.py:139-168` |
| 6 | Hoch | VIB-REST-Pfade (confirm, patch, delete, assign) berechnen den Planungsstand nie neu; MCP-Pfade tun es | `vib_import.py:185-241, 457-536`, `crud/vib.py` |
| 7 | Hoch | Celery ohne `acks_late`, Zeitlimits, Retries; Worker-Absturz verliert Import still, UI meldet „kein Worker“ | `celery_app.py:17-20` |
| 8 | Hoch | Expand/Contract-Versprechen gebrochen: Migrationen löschen Daten (Fulda) bzw. Spalten; Rollback per SHA kann das nicht zurückholen | `alembic/versions/20261017001:53-62`, `20260928001` |
| 9 | Hoch | Dokumentiertes Restore-Kommando (`pg_restore --clean --single-transaction`) widerspricht dem eigenen Restore-Skript und ist ungetestet | `DEPLOY.md:231-237` vs `scripts/restore_db.sh:119-137` |
| 10 | Hoch | Frontend: neun Mutationen invalidieren den Cache unvollständig (Löschen, Planungsstand, Import-Confirms); Nutzer sehen bis 5 min alte Daten | `shared/api/queries.ts:394-438, 704-713, 1306-1430` |

## 2. Architektur-Ist-Bild

### 2.1 Komponenten

```
Browser ── nginx (Container, :80, nur 127.0.0.1:5000 am Host) ── FastAPI (2 uvicorn-Worker, /api/v1, /healthz, /mcp)
                                                                  ├── PostgreSQL + PostGIS + pgRouting (db-Image)
                                                                  ├── Redis (Broker + Result-Backend, ohne Auth)
                                                                  ├── Celery-Worker (gleiches Image, SKIP_MIGRATIONS=1)
                                                                  └── GraphHopper (Routing, intern)
Host-nginx (systemd) terminiert TLS und proxyt auf 127.0.0.1:5000.
```

Backend-Schichten: `api/v1/endpoints` (28 Module) → `schemas` (Pydantic) → `crud` → `models` (78 Tabellen) mit `services` für reine Logik und `tasks` für Celery. Zusätzlich `mcp/tools` mit 91 Tools, die direkt auf `crud` zugreifen. Umfang: 40.600 Zeilen Backend, 20.600 Zeilen Backend-Tests, 41.100 Zeilen Frontend, 76 Migrationen, 255 Commits (164 davon durch Claude).

### 2.2 Authentifizierung

Drei Credentials in fester Reihenfolge: Bearer-API-Key (`rdb_…`, SHA-256, Scopes schneiden die Rechte des Besitzers, kein Admin-Bypass), HMAC-signiertes Session-Cookie (7 Tage, zustandslos), HTTP Basic. `AuthRouter` hängt `require_auth()` an jede Nicht-GET-Route ohne `require_permission`. MCP akzeptiert nur Bearer mit `mcp.access` und prüft pro Schreib-Tool die Capability.

### 2.3 Planungsstand (Kern der Domäne)

1. `sync_derived_observations_bulk` (`crud/projects/progress.py:539-785`) löscht alle abgeleiteten Beobachtungen und erzeugt sie neu aus VIB, PFA, FinVe, Bauportal, Medien, Fulda, Infraplan (neuester Jahrgang) und GVFG (neueste Ausgabe je Schlüssel).
2. `derive_headline` (`services/progress_derivation.py:324-412`) wählt die Kopfphase: neuester Bericht gewinnt, Vertrauen entscheidet nur im 365-Tage-Fenster, FinVe sind Untergrenzen ohne Alterung, Rückstufungen werden als Konflikt gehalten.
3. Überprojekte aggregieren den nicht-archivierten Teilbaum (`_build_aggregation_node`).
4. Prognose aus VIB-PFA-Terminen, BVWP-Dauern und erwarteten Beobachtungen; Bau-/IBN-Termin werden in `project_progress` gecacht.
5. Frische: Lazy-Resync nach 24 h beim Lesen, `recompute_for` nach Importen, Celery-Vollauf.

### 2.4 Import-Pipelines

Neun Ingestionspfade in vier Bauformen, nicht ein Lebenszyklus:
- Gestagte PDF-Celery-Parser (Haushalt, VIB-Upload, GVFG): Datei auf Volume, Task bekommt nur den Namen, Review im Frontend, Confirm per REST.
- Draft-eigene PDF (Infraplan): PDF bleibt beim Draft, Task re-runnable, Confirm liest serverseitig gespeicherte Zeilen.
- Agenten-geschrieben via MCP ohne Parser (VIB Phase 7, Fulda).
- Synchron im Request (Bauportal, Medien) bzw. Celery ohne Review (Parlament).

### 2.5 Deploy

`release.yml` (push master) führt `make test` und baut vier Images nach GHCR mit Commit-SHA. `deploy.yml` (manuell, Eingabe SHA) prüft Manifeste, SSH mit erzwungenem Kommando `prod.sh <sha>`, dieser pullt, setzt `IMAGE_TAG`, `compose up`, wartet 180 s auf `/healthz`, sonst Rollback auf die alte SHA. Vor der Migration dumpt der One-shot-Dienst `backup` die DB. Rollback bedeutet altes Image auf neuem Schema; `db_ahead.py` verhindert, dass `alembic upgrade` dabei abbricht.

## 3. Befunde

Schweregrade: Kritisch (ausnutzbar oder Datenverlust), Hoch (falsche Daten für Nutzer, Betriebsrisiko), Mittel (Regelverstoß mit begrenzter Wirkung), Niedrig (Hygiene).

### 3.1 Sicherheit und Autorisierung

Hoch: Routen-Bestätigung ohne Capability. `confirm_route` in `api/v1/endpoints/project_routes.py:73-94` deklariert kein `require_permission`; `AuthRouter` ergänzt nur `require_auth()`, das bei Bearer-Keys keine Scopes prüft (`core/security.py:258-262`). Ein Viewer oder ein Read-only-Key (`scopes=["mcp.access"]`, der UI-Default) kann Routen an jedem Projekt persistieren. MCP `route_project_geometry` verlangt `project.edit`. Fix: `Depends(require_permission("project.edit"))` ergänzen; `AuthRouter`-Fallback so ändern, dass Key-Auth ohne explizite Capability abgelehnt wird.

Hoch: Scope-Umgehung bei API-Keys. `require_permission` gibt `api_key.user` zurück, ein normales `User`-Objekt. `projects.py:437` prüft danach `current_user.has_permission("finve.edit")`, was Admin-Bypass hat und Scopes ignoriert. Ein Key mit Scope `project.edit` eines Admins kann FinVe-Links revertieren. Gleiches Muster in `api_keys.py:74`. Widerspricht `feature-mcp-server.md:371-376`. Fix: Dependency liefert ein Principal mit effektiver Rechtemenge (wie `McpPrincipal`); `User.has_permission` in Endpunkten per Test verbieten.

Hoch: Nutzernamen öffentlich. `GET /projects/{id}/progress` (`project_progress.py:39-45`, Docstring „Public“) liefert `observations[].username_snapshot` (`progress_schema.py:88`); `GET /guides/{slug}/overrides` (`guides.py:26-29`) ebenso, das Frontend rendert „Angepasst von <user>“ (`GuideSectionBody.tsx:126-127`). `docs/architecture.md:127-128` verbietet genau das. Fix: `optional_auth()` und Feld bei anonymen Lesern leeren; Test für anonyme Besucher.

Mittel: SSRF im Medien-Importer. `tasks/media_extraction.py:63-76` holt jede URL mit `follow_redirects=True` und speichert den Body; Endpunkt braucht nur `progress.edit`. Erreichbar sind `http://redis:6379`, `http://db:5432`, GraphHopper und Cloud-Metadaten. Fix: nur http(s), private/Loopback-Adressen auch nach Redirect ablehnen, Antwortgröße begrenzen.

Mittel: Kein Brute-Force-Schutz. `POST /auth/session` rechnet PBKDF2 mit 390.000 Iterationen bei jedem Fehlversuch (`security.py:21`), kein Rate-Limit; unbekannte Nutzer überspringen PBKDF2, also leakt die Antwortzeit Nutzerexistenz (`security.py:91-94`). Fix: `limit_req` im nginx, Dummy-PBKDF2 für unbekannte Nutzer.

Mittel: Session-Tokens nicht widerrufbar. Token = `user_id:ts` + HMAC (`security.py:191-224`); Logout löscht nur das Cookie, Passwortänderung und Rollenwechsel lassen alte Cookies 7 Tage gültig. Fix: Per-User-Secret (z. B. Teil des Passwort-Hashes oder `session_version`) in den HMAC mischen.

Mittel: `user.manage` und `role.manage` sind de facto Super-Admin. `users.py:51-61, 105-115`: Wer Nutzer verwalten darf, kann Admins anlegen und Admin-Passwörter setzen; `roles.py:53-95`: Wer Rollen verwaltet, kann der eigenen Rolle alles geben. Undokumentiert in `feature-user-roles-permissions.md:96-100`.

Niedrig: `/healthz` ist öffentlich und listet Probleme auf (etwa dass der Session-Secret ein Platzhalter ist, `health.py:91`). `GET /users/me` meldet bei Key-Auth die vollen Rechte des Besitzers statt der effektiven (`users.py:24-28`). Logout-Cookie ohne `secure`. uvicorn ignoriert `X-Forwarded-Proto` (kein `--forwarded-allow-ips`). Container-nginx ohne `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `server_tokens off`. Redis ohne Passwort im Prod-Netz (Dev hat eines).

### 3.2 Datenintegrität und Domänenregeln

Hoch: VIB-REST ohne Neuberechnung. `vib_import.py:185-241` (confirm), `:457-467` (delete), `:517-536` (patch mit `project_ids`) und `admin_assignments.py:98-110` rufen nie `recompute_for`; `crud/vib.py` enthält das Wort nicht. Die MCP-Pfade in `crud/vib_agent.py` tun es an elf Stellen. Zusätzlich setzt REST-PATCH `confirmed=True`, MCP `assign_vib_entry` setzt es zurück. Beim Report-Löschen bleiben abgeleitete Beobachtungen mit `vib_entry_id=NULL` als Waisen (`progress_observation.py:401-403`, SET NULL). Fix: REST auf die `vib_agent`-Funktionen umstellen, `crud/vib.py` löschen.

Hoch: Haushalt-Confirm umgeht `change_finve_links`. `haushalt_import.py:139-168` schreibt `FinveToProject` direkt (Zeilen 147, 162). `crud/finve_links.py:3-9` nennt sich selbst „jeder Schreibpfad außer Haushalt“. Folgen: keine `finve_ids`-Historie (Revert unmöglich), keine Archiv-Prüfung, FinVe-Untergrenzen hinken 24 h. Fix: Delta sammeln und durch `change_finve_links` leiten.

Hoch: Confirm vertraut dem Client. Haushalt (`haushalt_import.py:197-229`) und VIB (`vib_import.py:225-232`) übernehmen die vom Browser gesendeten Zahlen und Einträge; `result_json` wird nur für das Link-Delta gelesen, `row_key`s werden nicht gegen `parse_result_id` geprüft. VIB löscht danach den Draft inklusive OCR-Text (`:235-236`), die Herkunft ist weg. Infraplan und GVFG machen es richtig (Server liest gespeicherte Zeilen). Fix: Confirm nimmt `parse_result_id` plus Overrides; Draft als bestätigt markieren statt löschen.

Hoch: PFA-Leaf-Termine fehlen in Prognose und Listen-Cache. `crud/projects/progress.py:945-953` lädt PFAs nur über die m:n-Tabelle; ein per `create_vib_pfa_subprojects` angelegtes Unterprojekt hat nur `VibPfaEntry.project_id`. `split_expected` (`:454-461`) verwirft die abgeleiteten VIB-Erwartungen. Folge: Prognose fällt auf BVWP-Schätzung zurück, `construction_start_date`/`commissioning_date` bleiben NULL, Listen-Spalte „Termine“, Filter `bau_von`/`ib_von` und MCP-Filter verfehlen diese Projekte, während der Zeitstrahl die Termine zeigt (`progress_timeline.py:444-453`). Fix: PFAs per `VibPfaEntry.project_id` in `_build_forecast_for_project` vereinigen.

Mittel: `delete_project` kaskadiert nichts. `crud/projects/projects.py:355-362` löscht und committet; Parent-Geometrie (`geojson_from_subprojects`), Wahlkreis-Links und Planungsstand der Vorfahren bleiben stehen. Archive, Merge und Update kaskadieren. Fix: `superior_project_id` vorher merken, danach `recompute_geojson_for_parent` und `recompute_progress`.

Mittel: Archiv-Regel bei PFAs verletzt. `progress.py:586-598` prüft `pfa.project_id is not None` ohne `is_archived`. Wird das einzige PFA-tragende Unterprojekt archiviert, verliert der Parent seine VIB-Beobachtung und die Kinder-Spanne, Ergebnis „Unbekannt“.

Mittel: Drafts inkonsistent im Teilbaum. `_subtrees` im Zeitstrahl (`progress_timeline.py:378-383`) filtert `is_draft`; `_load_subtree`, `subtree_ids`, `has_subprojects` und die Geometrie-Kaskade nicht; `get_subprojects` versteckt sie, `progress.children[]` zeigt sie. Es gibt vier Teilbaum-Walker und vier „is_superior“-Schreibweisen. Fix: ein gemeinsamer Helper, Entscheidung #265 treffen.

Mittel: GVFG-Aggregation nur eine Ebene tief und nur im Frontend. `crud/gvfg.py:449-456` liefert direkte Kinder; die Summe „Bundesförderung“ rechnet `projectCost.ts:34-66`. FinVe und Infraplan aggregieren den ganzen Teilbaum im Backend. MCP und IBN-Check sehen die Regel nicht. Prinzip „für jede Quelle“ verletzt.

Mittel: Länge wird nie aggregiert. `recompute_geojson_for_parent` schreibt nur Geometrie; `length` bleibt beim Parent leer oder veraltet, `list_data_gaps` meldet dann `has_length`. Fix: in der Kaskade `compute_geojson_length_km` setzen.

Mittel: „Neuere Quelle gewinnt“ gilt nicht für Kosten. `crud/infraplan.py:114-149` vergleicht nie gegen den GVFG-Stand; `ProjectCostBlock.tsx:68-90` zeigt immer Infraplan. `feature-infraplan-import.md:55` (Entscheidung 22) sagt Kosten folgen der neueren Quelle, `feature-gvfg-import.md` sagt Infraplan führt. Die Dokumente widersprechen sich, der Code folgt dem schwächeren.

Mittel: Infraplan-vs-GVFG-Rivalität global je Schlüssel. `_gvfg_stand_by_key` (`progress.py:788-803`) nimmt die neueste Ausgabe über alle Projekte; ist die neuere GVFG-Zeile einem anderen Projekt zugeordnet, verliert Projekt P die Infraplan-Phase und bekommt keine GVFG-Phase. Daten verschwinden.

Mittel: Merge mit archivierter Seite erlaubt (`merge.py:302-309`), kein Test. Sammel-FinVe-Phasenzuordnung (`finves.py:288-296`) berechnet verlinkte Projekte nicht neu.

Mittel: Datumspräzision unvollständig. `pf_date`, `parl_befassung_date`, `lifecycle_date` haben keine Präzision und werden als EXACT-Meilensteine emittiert (`progress_timeline.py:294-320`). Abgeleitete MONTH/YEAR-Sortierwerte liegen am 15. bzw. Jahresmitte (`progress_dates.py:94-96, 204-234`), manuelle am 1. bzw. 1. Januar (`date_precision.py:265-276`); zwei „2028“ sortieren sechs Monate auseinander. Infraplan `ibn_qualifier` BIS wird als Fahrplanwechsel gelesen (`progress_materialization.py:634-645`).

Mittel: `GET /projects/`, `/drafts`, `/{id}/subprojects` serialisieren `geojson_representation` je Zeile (`projects.py:11-29, 52-68`), gegen die eigene Regel „Geometrie nicht in Listen“. `recompute_all_progress` kostet ca. 10 Queries je Projekt, weil der Cache-Rebuild die volle Prognose samt GVFG-IBN-Check rechnet.

Mittel: Regeln nur in MCP. Pflicht-Notiz bei Phasen-Override (`mcp/tools/projects.py:1370`), Fulda-Zuordnung (`fulda.py:182`), Infraplan-Zuordnung; Changelog bei `create_project` und `set_project_draft` (MCP schreibt, REST `POST /projects/` und `/finalize` nicht); Capability `project.edit` (MCP) vs `project.create` (REST) für Finalisieren; GeoJSON-Validierung nur in MCP; `_validate_geometry_ownership` doppelt implementiert. Fix: Regeln in `crud`/Services verschieben, beide Transporte rufen dieselbe Funktion.

Niedrig: Vier Lph-zu-Phase-Leser mit abweichendem Ergebnis für „nur Lph 9“ (BAU vs IN_BETRIEB, `progress_materialization.py:537-569` vs `:671-693`). `stored_headline_phase`/`is_known` und PaBe-Relevanz je dreimal (Python und SQL-Zwillinge ohne Äquivalenztest). Explizite Konfidenz schaltet Alterung komplett ab (`progress_derivation.py:204-205`). Unterschiedliche `ondelete`-Semantik je Quelle (`finve_to_project` ohne, andere CASCADE). `list_finves` zeigt archivierte Projekte unmarkiert. `exclude_draft_projects`-Validator ist tot. Drei `formatMio`-Varianten im Frontend. Transaktionsmuster gemischt (CRUD committet teils pro Vorfahr, Endpunkte teils selbst).

### 3.3 Import-Pipelines

Hoch: Celery-Robustheit. `celery_app.py:17-20` setzt nur `task_track_started` und `result_expires`. Kein `task_acks_late`, kein `task_reject_on_worker_lost`, keine Zeitlimits, keine Retries. Haushalt und GVFG persistieren erst am Ende; VIB speichert den Draft erst nach OCR und Block-Splitting (Doku verlangt Speichern nach OCR); Infraplan setzt RUNNING und nie zurück. Nach einem Worker-Absturz fällt der Redis-Status auf PENDING und `tasks.py:120-121` meldet „kein Worker“. Die gestagte Datei wird nach 24 h gelöscht, bezahlte OCR-Ergebnisse sind weg. Fix: `acks_late`, `time_limit`, Ergebniszeile vor der Arbeit anlegen, Sweep für veraltete RUNNING.

Mittel: VIB `report_date` ist „das erste dd.mm.yyyy in 8000 Zeichen“ (`tasks/vib.py:152, 630-633`) und steuert die Prognose-Gewichtung gegen Fulda. Ein Datum auf dem Deckblatt verschiebt still, welche Quelle gewinnt.

Mittel: LLM-Client ohne Timeout, Retry, `max_tokens`, Null-Guard (`services/llm.py:21-36`); `retry_vib_ai_for_entry` läuft synchron im Request (`vib_import.py:321-376`, SDK-Default 600 s); `extract_vib_blocks` persistiert erst nach allen Einträgen, Absturz bei Eintrag 40/50 verliert 39 bezahlte Ergebnisse.

Mittel: Upload-Validierung je Endpunkt anders. `validate_mime` (python-magic) nutzt nur `project_texts.py`; Haushalt/GVFG prüfen den Client-Content-Type, Infraplan zusätzlich `%PDF`, VIB nichts.

Mittel: Haushalt „löschen und neu importieren“ löscht keine FinVe-Zeilen und keine permanenten Links (`crud/haushalt_import.py:119-149`); `upsert_budget_titel_entries` entfernt nie veraltete Einträge.

Mittel: Fehlerverhalten inkonsistent: „bereits bestätigt“ ist 400 (GVFG), 409 (Haushalt, Infraplan); VIB „läuft noch“ ist `HTTPException(202)`; Haushalt-FAILURE-Zeile ohne Nutzer; drei Formen von Task-Progress-Meta.

Mittel: Schichtinversion. `crud/*` importiert aus `tasks/*` an acht Stellen, `tasks/__init__.py` lädt `haushalt` und `vib` eager, `document_ocr.py` importiert `mistralai` und `fitz` am Modulanfang. Der API-Prozess lädt beim Start pymupdf, mistralai und den gesamten Haushalt-Parser. `tasks/gvfg.py` importiert 1718 Zeilen Haushalt-Code für ein 10-Zeilen-`report_step`.

Mittel: Vier Kopien des Fuzzy-Matchers (`finve_matching.py:25-63` ≡ `vib_matching.py:73-100`, private Importe aus `crud/gvfg.py:34` und `infraplan_matching.py:49`) mit Schwellen 0,35 / 0,45 / 0,50 / 0,85 / 0,9 und vier Ergebnisformen.

Mittel: Infraplan erzwingt sieben Abschnitte von 2026 als Pflicht (`tasks/infraplan.py:175-183`); MCP-Confirm kann `force` nie setzen (`mcp/tools/infraplan.py:429-435`), also ist ein künftiger Infraplan ohne InvKG-Tabelle nur über das Frontend bestätigbar.

Niedrig: `POST /tasks/{id}` gibt den vollen VIB-Parse-Payload an jeden Eingeloggten; Base64-OCR-Bilder in einer Text-Spalte (`vib_draft_report.ocr_images_json`); Infraplan-PDFs ohne Orphan-Sweeper; GVFG-Parse-Runs trotz Bestätigung löschbar; `tasks/debug.py` mit `sleep(2)` im Prod-API; toter pdfplumber-Code in `tasks/vib.py:164-208` nur von Tests gehalten; `scripts/dump_vib_parse_result.py` mit Shebang `python3.11`; 900.000er-FinVe-ID-Band als Workaround für gedruckte Nummern als Primärschlüssel.

Jahrgangsspezifische Hacks (Wartungsrisiko): Spaltenbreiten und Schriftgrößen für Infraplan 2026, 2027-Annahmen in `haushalt_keys.py`, 2023-Tippfehler im GVFG-Parser, Migration `20261022002` mit hartcodierten Beträgen, `repair_infraplan_full_stops` als 120 Zeilen Dauercode für eine Einmalreparatur.

### 3.4 Deploy, Rollback, Betrieb

Hoch: Expand/Contract gebrochen. `20261017001:53-62` löscht alle `fulda_announcement` und abgeleiteten Beobachtungen, nennt sich im Docstring „expand only“; `20261022003` schreibt Todo-Texte um; `20260928001` droppt `project.centroid` (Docstring sagt `Revises: 20260910001`, Code sagt `20261007001`). `prod.sh` kennt kein `alembic downgrade`; Rollback = altes Image auf neuem Schema. Nichts im CHANGELOG markiert „kein Code-Rollback über Revision X hinaus“. Heute keine Live-Exposition (ältester knopf-erreichbarer SHA liegt nach dem Drop), das Muster ist aber ungeschützt. Fix: Zwei-Release-Regel; Lint in `test_migration_ids.py`, der `drop_column`/`DELETE` ohne `# contract: approved` ablehnt; `db_ahead.py` nennt die älteste sichere SHA.

Hoch: Restore ungetestet und widersprüchlich. `DEPLOY.md:231-237` nutzt `pg_restore --clean --if-exists --single-transaction`; `scripts/restore_db.sh:119-123` vermeidet `--clean` ausdrücklich wegen vorinstallierter PostGIS-Erweiterungen und droppt stattdessen die DB. Der einzige Weg zurück nach einer destruktiven Migration ist nie verifiziert worden.

Mittel: `cancel-in-progress: true` am Deploy-Job (`deploy.yml:35-37`). Ein zweiter Klick tötet `prod.sh` zwischen `set_tag` und Health-Wait; `.env` zeigt dann auf eine unverifizierte SHA ohne Rollback. Fix: `cancel-in-progress: false`.

Mittel: `GH_OSM_URL` leer heißt nicht „GraphHopper überspringen“ (`.env.prod.example:63`), sondern Crash-Loop (`docker-entrypoint.sh:11-17`, `restart: unless-stopped`) und stündliche Alarme vom Host-Check.

Mittel: `/healthz` prüft weniger als behauptet. Compose und `production_setup.md` sagen „Pflichtkonfiguration“; geprüft wird nur der Session-Secret-Platzhalter (`health.py:26,78`). Nicht geprüft: `ENVIRONMENT=production` (schaltet allein das Secure-Cookie), CORS, Redis. Schema-Check deckt nur `project`.

Mittel: Migrations-Gate-Kanten. Gemischte bekannte/unbekannte `alembic_version`-Zeilen gelten nicht als „ahead“ und führen in den Crash-Loop; gelöschte Revisionsdateien lassen jede DB „ahead“ erscheinen und Migrationen werden still übersprungen; kein Advisory-Lock bei zwei Backend-Instanzen oder parallelem `make docker-migrate`.

Mittel: `make test` ist weder hostunabhängig noch „bit-identisch“ mit CI (`ci.yml:7-8`): `test_prod.sh`/`prod.sh` nutzen `grep -oP` (macOS-grep hat es nicht); GraphHopper wird nicht gebaut; Runtime-Images ohne Release-Build-Args; drei kalte Builds je Merge ohne Cache.

Niedrig: nginx im Container ohne `resolver`, Teil-Restart kann 502 erzeugen; Uploads nicht im Pre-Migrate-Backup, nur im repo-externen Borg-Cron, der nachts alle Container stoppt; Makefile: `.PHONY` und `help` lückenhaft, `docker-backup-db` hartcodiert `-U raildashboard`; `.env.prod.example:38-39` hat die Compose-Präzedenz verkehrt herum; `DEPLOY_FINGERPRINT` fehlt in zwei von drei Secret-Listen.

### 3.5 Frontend

Hoch: Cache-Invalidierung lückenhaft (`shared/api/queries.ts`):
- `useDeleteProject` (704-713) invalidiert nur `projects` und `projectDrafts`; Karte und Liste lesen `projectGroups`, der Parent liest `progressFor(parent)`. `invalidateAfterArchiveChange` (743-754) macht es richtig.
- Planungsstand-Mutationen (394-438, 481-489) invalidieren nur `progressFor(id)` und Changelog; Parent-Aggregat und `headline_phase` in `projectGroups` (Liste, Karte, Zeitstrahl) bleiben alt.
- `ProjectDetail.tsx:191-203` setzt nach PATCH nur das Projekt; Versionshistorie und Wahlkreise werden nicht invalidiert, obwohl das Backend beides schreibt.
- `useConfirmHaushaltsImport` (1306-1318) lässt `finves`, `project-finves`, `adminUnassignedFinves`, `progress` stehen; `useConfirmVibImport` (1418-1430) und `useDeleteVibReport` (1410-1416) ebenso für `projectVib`/`vibEntriesConfirmed`; `useConfirmGvfgImport` und `useCreateInfraplanSubproject` legen Drafts an, ohne `projectDrafts` zu invalidieren; `useAssignVibEntry`/`useAssignGvfgEntry` (1759-1788) unterinvalidieren.
Mit `staleTime` 5 min und ohne Focus-Refetch sehen Nutzer nach dem Speichern alte Daten. Fix: je Mutation die Backend-Seiteneffekte spiegeln; Helper `invalidateAfterFinveLinkChange` und `invalidateAfterProgressChange` nach dem Muster von `invalidateAfterArchiveChange`.

Mittel: Abgelaufene Sessions werden nie erkannt. `lib/auth.ts:55-62` lädt `/users/me` einmal; `client.ts:45-60` wirft bei 401 ohne Hook; kein `QueryCache.onError`. Nach 7 Tagen zeigt der Header weiter „Abmelden“, Mutationen scheitern mit „Unauthorized“.

Mittel: `ApiError` ist ein Plain Object (`client.ts:53-59`), `message` liest `details.message`, FastAPI sendet aber `detail`. Alle `instanceof Error`-Prüfungen (`ProjectDetail.tsx:206, 232, 271, 363`, `MapPage.tsx:325`) fallen durch; 422-Validierungstexte erreichen den Nutzer nie. Fix: `class ApiError extends Error` mit `message = detail ?? statusText`.

Mittel: App bleibt leer, bis `/users/me` antwortet (`auth.ts:91-93`); bei API-Ausfall leere Seite ohne `ErrorState`.

Mittel: Speichern im Planungsstand-Drawer sind N sequenzielle Mutationen ohne Atomarität (`ProgressEditDrawer.tsx:388-410`); `GeometryEditor.tsx:319-332` persistiert die Route, bevor der PATCH gelingt.

Mittel: Feld-Sync-Regel verletzt für `aliases`: Backend hat es (`project_fields_base.py:20`), Formular nicht. Editoren können die Aliasse, auf die der Infraplan-Matcher baut, nicht pflegen.

Mittel: Header-Gating (`Header.tsx:47-59`, 12 Capabilities) und Admin-Übersicht (`AdminOverviewPage.tsx:33-54`, zusätzlich `progress.edit`, `settings.manage`, `project.delete`) weichen ab. Fünf Admin-Seiten ohne `RequirePermission` (Bauportal, Medien, Fulda ×2, Projektgruppen). Filter in `useState` statt URL auf fünf Seiten (Tasks, GVFG, Bauportal, Medien, Infraplan-Review).

Niedrig: Sechs literale Query-Keys außerhalb von `queryKeys`; tote Hooks (`useProjects`, `useFuldaCategories`, `useConstituencies`, `useUpdateUserRole`); `ProjectEdit` verwirft ungespeicherte Eingaben bei Projektrefetch; dritter Breakpoint in `Header.tsx:19`; `window.confirm` an zwei Stellen; 19× `color="yellow|orange"` gegen „kein Gelb“; ESLint erzwingt keine der dokumentierten Regeln (kein `no-console`, kein `no-restricted-imports`); `src/shared/api/**` ist aus `tsconfig` ausgeschlossen, die dortigen Tests werden nie typgeprüft; `as any` in `MapView.tsx:521-547`; `createUpdatePayload` sendet alle 60 Felder (Last-Write-Wins bei Parallelbearbeitung).

Features ohne Tests: auth, bauportal-import, changelog, documentation, finanzen, fulda-import, guides (15 Dateien), gvfg, gvfg-import, haushalt-import (8 Dateien), media-import, vib-import (5 Dateien).

### 3.6 Tests, Schema, Migrationen

Hoch: Tests laufen ausschließlich auf SQLite. `tests/api/conftest.py:94-104` nutzt `sqlite:///:memory:` mit Pass-through-Stubs für `GeomFromEWKT`/`ST_AsEWKB`; Tabellen werden per `table.create()` angelegt, nie per Alembic; `Dockerfile:41` schließt `tests/db_related_tests` aus. `docs/architecture.md:42,178` sagt „nie SQLite“ und „dedizierte Test-DB“. Niemals in CI ausgeführt: die gesamte PostGIS-Verschneidung (`constituency_matching.py:55-78`), der Wahlkreis-GeoJSON-Endpunkt, `ST_GeomFromGeoJSON` im Parlaments-Import, alle Migrationen mit `ON CONFLICT`, `RETURNING`, `ILIKE`, `UPDATE … FROM`, Geometrie-Spalten, sowie alle `ondelete`-Regeln (SQLite-FKs sind aus, kein `PRAGMA foreign_keys=ON`). `.ilike()` ist auf SQLite ASCII-only („Köln“ ≠ „köln“). Fix: CI-Job mit dem `docker/db`-Image: `alembic upgrade head`, `alembic check`, Spatial-Tests.

Mittel: `pytest.ini` nutzt den Schlüssel `env` von `pytest-env`, installiert ist `pytest-dotenv` („Unknown config option: env“). `ENVIRONMENT=test` kommt nur aus Makefile und Dockerfile. Wer laut AGENT.md `.venv/bin/python -m pytest` direkt ausführt, lädt mit vorhandener `.env` die echte `DATABASE_URL` in `dashboard_backend.database.engine`.

Mittel: `tests/db_related_tests` ist eine tote Suite, die lokal still gegen `apps/backend/test.db` läuft; Routing-Tests überspringen immer.

Mittel: Bekannte Model/Migration-Drift blockiert Autogenerate (`routes.details` JSONB vs JSON, `ix_users_id`, nullable Flags, Unique-Constraints); seit Oktober trägt jede Migration den Satz „written by hand: autogenerate reports unrelated drift“. `make migrate-create` liefert Rauschen.

Niedrig: `todo_assignee` ohne Index entgegen `architecture.md:152-156`; `project_text.created_at` als Integer; `finve.id` mit `server_default="2000"` auf Autoincrement; tz-naive Timestamps mit 59× `datetime.utcnow()` (deprecated in 3.13); Base64-Bilder und mehrere JSON-Blobs inline; `project_to_project_group` mit nullable FKs; Tippfehler im Schema (`elektrification`, `strecklaenge_km`, `priortiy_area`); `tests/api.py` als 0-Byte-Datei neben dem Paket; `docs/testing.md` ist ein 11-Zeilen-Fragment; API-Tests mocken an vielen Stellen die CRUD-Schicht; Hilfsfunktionen zehnfach dupliziert (`_seed` ×10).

Veraltete Abhängigkeiten mit Major-Sprung: `redis` 6.4 → 8.1, `PyMuPDF` 1.27 → 2.0, `openai` 2.32 → 3.37, `mistralai` 2.4 → 3.3; `pandas` wird nur von drei Legacy-Skripten gebraucht.

### 3.7 Dokumentation und Steuerung

Die Doku hat vier Agenten-Steuerdateien (AGENT.md, CLAUDE.md, apps/backend/agent.md, apps/frontend/AGENT.md) und drei Deploy-Dokumente (DEPLOY.md, docs/workflow.md, docs/production_setup.md, dazu docs/uebergabe-deploy.md). `apps/frontend/AGENT.md` beschreibt ein anderes Projekt: `main`/`develop`, Prettier, Husky, `npm run type-check`, Playwright, 80 % Coverage, zwei Approvals, „Zustand oder Redux bevorzugen“ (Root-Doku verbietet beides). `docs/production_setup.md` beschreibt einen Server mit Makefile und `.env.example`, den es nicht gibt. Die Roadmap ist in mindestens sechs Punkten veraltet (ProjectProgress Phase 1 offen, obwohl umgesetzt; „VIB über MCP“ offen; „#261“ offen, obwohl HEAD der Merge ist; „CI-Automatisierung offen“, obwohl zwei Workflows laufen).

## 4. Widerspruchstabelle (Auswahl, vollständig geprüft)

| Aussage | Quelle | Realität | Quelle |
|---|---|---|---|
| Deploy per `v*`-Tag über SSH | README.md:191-197 | Manuell per SHA, Tags rollen nichts aus | README.md:169-175, DEPLOY.md:55-59, deploy.yml |
| Python 3.11+ | README.md:24, apps/backend/README.md:32, production_setup.md:13 | 3.13 (Image, venv, AGENT.md verbietet 3.11) | Dockerfile:12, AGENT.md:85-88 |
| `make dev` → :8000 / :5173 | README.md:50-52, .env.example:112, config.py:37 (CORS) | :8001 / :5174 | Makefile:141,144 |
| `.env.docker-dev` wird genutzt | README.md:35 | Nichts liest es; Redis-URL darin ohne Passwort, Dev-Redis verlangt eines | config.py:8-17, docker-compose.dev.yml:40 |
| Roadmap ohne Checkbox-Semantik | AGENT.md:9,12, CLAUDE.md | „mark it `[x]` in the roadmap“, Command und Hook erzwingen es | AGENT.md:40,116, .claude/commands/update-roadmap.md, remind-roadmap.sh |
| `docs/superpowers/` darf nicht existieren | AGENT.md:35 | Existiert mit 7 Dateien | docs/superpowers |
| Nie SQLite | architecture.md:42, apps/backend/agent.md:20 | Alle CI-Tests auf SQLite, App hat SQLite-Sonderzweige | tests/api/conftest.py:94, architecture.md:110 |
| Nutzernamen nur für Eingeloggte | architecture.md:127-128 | Zwei öffentliche GETs liefern sie | project_progress.py:39, guides.py:26 |
| Kein Admin-Bypass bei Key-Auth | feature-mcp-server.md:371-376 | `has_permission` nach Key-Auth | projects.py:437 |
| Schreibende MCP-Tools loggen „wie REST“ | feature-mcp-server.md | REST `POST /projects/` und `/finalize` loggen nicht | projects.py:131-133, 344-352 |
| `create_project` „final, ohne Geometrie“ | feature-mcp-server.md Katalog | Draft per Default | mcp/tools/projects.py:983 |
| Migrationen Expand/Contract | AGENT.md:77, DEPLOY.md:276 | 20261017001 löscht, 20260928001 droppt | alembic/versions |
| `/healthz` prüft Pflichtkonfiguration | compose.yaml:73, production_setup.md:93 | Nur Session-Secret-Platzhalter | health.py:26,78 |
| Healthcheck pollt `/api/v1/health` | production_setup.md:347-350 | `/healthz` | compose.yaml:77 |
| Worker `depends_on: service_started` | apps/backend/README.md:210, roadmap.md:48 | `service_healthy` | compose.yaml:114 |
| Squash-Merge | docs/git_workflow.md:5 | Merge-Commits (Hook `merge_method: merge`) | pr_auto_merge.py:25, git log |
| `client.gen.ts`, axios | architecture.md:280, apps/frontend/README.md:57 | Existieren nicht; ein `fetch`-Wrapper | shared/api/client.ts |
| `@mantine/charts` nur über `FinveBudgetDetails` | architecture.md:247 | Auch `GvfgSection.tsx`, `InfraplanPage.tsx` (lazy, Bundle-Ziel hält) | ebd. |
| Jede Assoziationstabelle hat Index auf der zweiten Spalte | architecture.md:152 | `todo_assignee` hat keinen | models/todos/todo.py |
| `task_always_eager` in conftest | architecture.md:100 | Nur Autouse-Fixture in `test_tasks.py` | tests/api/test_tasks.py:11 |
| Kosten folgen der neueren Quelle | feature-infraplan-import.md:55 | Infraplan führt immer | crud/infraplan.py:114, feature-gvfg-import.md |
| 409 bei doppeltem Nutzernamen | architecture.md:131 | 400 (Rollen: 409) | users.py:59,94 vs roles.py:43 |
| `GH_OSM_URL` leer = GraphHopper aus | .env.prod.example:63 | Crash-Loop | docker/graphhopper/docker-entrypoint.sh:11 |
| CI bit-identisch zu lokal | ci.yml:7-8 | Host-Shell für `test_prod.sh`, kein GraphHopper | Makefile:162-170 |
| `OSM_PBF_DIR`, `USE_GEOMETRY`, `RINF_*` sind Backend-Settings | .env.example:101-105, config.py:30-33 | Ungenutzt | grep über dashboard_backend |
| Restore mit `--clean --single-transaction` | DEPLOY.md:234 | Skript meidet `--clean` bewusst | scripts/restore_db.sh:119 |

## 5. Strukturelle Ursachen

1. Zwei Transportschichten, keine Service-Schicht für Schreibregeln. REST und MCP rufen zwar meist dieselben CRUD-Funktionen, aber Validierung (Pflicht-Notiz, GeoJSON-Prüfung), Changelog und Neuberechnung werden vom Aufrufer entschieden. `crud/finve_links.change_finve_links` zeigt das richtige Muster (loggt, prüft Archiv, committet, berechnet neu); es wurde nur für FinVe-Links umgesetzt.
2. Materialisierung ohne zentrale Trigger-Liste. `recompute_for` muss jeder Schreibpfad selbst aufrufen. Es gibt keine Stelle, die „Eingaben des Planungsstands“ definiert; daher fehlen VIB-REST, Haushalt, Sammel-FinVe-Phasen und Löschen.
3. Kein gemeinsamer Teilbaum-/Aggregations-Helper. Vier Walker, vier „is_superior“, je Quelle eigene Aggregation (FinVe Backend-Teilbaum, Infraplan Backend-Teilbaum mit Carrier-Dedupe, GVFG Frontend eine Ebene, Länge gar nicht). Jede neue Regel (archiviert, Draft) muss an vier bis sechs Stellen nachgezogen werden.
4. Import-Pipelines sind nacheinander entstanden und kopieren einander. Vier Bauformen, vier Matcher, drei Progress-Meta-Formen, Validierung je Endpunkt anders. Das Vereinheitlichungs-Dokument beschreibt einen Zielzustand, den nur die ältesten Pipelines erreicht haben; die neuesten (Infraplan, GVFG) sind besser, folgen aber einem anderen, undokumentierten Muster.
5. Tests auf SQLite erzeugen falsche Sicherheit für alles, was Postgres-spezifisch ist: Geometrie, FK-Kaskaden, Migrationen, ILIKE.
6. Dokumentation wird pro Feature geschrieben, nicht pro Thema gepflegt. 164 von 255 Commits stammen von Claude; die Regel „alle Doku-Schichten aktualisieren“ hat Duplikate erzeugt, die auseinanderlaufen. Es fehlt eine Besitzer-Zuordnung je Thema.
7. Transportnahe Autorisierung. `AuthRouter` macht die Capability optional; `require_permission` gibt ein `User`-Objekt zurück, das mehr kann als der Request.

## 6. Lösungen und Verbesserungen

### 6.1 Sofort (Sicherheit, je unter einem Tag)

1. `require_permission("project.edit")` an `confirm_route`; `AuthRouter`-Fallback lehnt Bearer-Keys ab; Test, der jede Nicht-GET-Route ohne `require_permission` fehlschlagen lässt.
2. `require_permission` liefert ein `RequestPrincipal(user, permissions: frozenset)`; `_revert_finve_ids` und `api_keys.py:74` prüfen gegen `principal.permissions`; Grep-Test verbietet `has_permission` in `api/`.
3. `optional_auth()` auf `/projects/{id}/progress` und `/guides/{slug}/overrides`, `username_snapshot` für Anonyme auf `None`; Test für anonyme Leser.
4. `fetch_url_text`: Schema-Whitelist, DNS-Auflösung und Sperre privater Bereiche auch nach Redirect, `max_bytes`.
5. `deploy.yml`: `cancel-in-progress: false`.
6. `celery_app.conf`: `task_acks_late=True`, `task_reject_on_worker_lost=True`, `task_time_limit=1800`, `task_soft_time_limit=1500`.
7. README-Abschnitt „Deployment“ (Zeilen 191-197) löschen.

### 6.2 Kurzfristig (Datenintegrität, 1 bis 2 Wochen)

1. Ein Schreibpfad je Quelle. VIB-REST auf `crud/vib_agent` umstellen, `crud/vib.py` löschen. Haushalt-Confirm sammelt Link-Deltas und ruft `change_finve_links`. `set_finve_progress_phase` und `delete_project` rufen `recompute_for` bzw. die Geometrie-Kaskade. Danach ein Test je Eingabequelle: „Schreiben über REST und über MCP erzeugt denselben Planungsstand“.
2. Regeln in CRUD: Pflicht-Notiz bei Phasen-Override und Zuordnungen als Pydantic-Validator oder in `progress_crud.update_progress`; Changelog in `create_project`/`finalize_project`; GeoJSON-Validierung und Geometrie-Ownership in `update_project`; eine Capability für Finalisieren.
3. Confirm liest den Server. Haushalt- und VIB-Confirm nehmen `parse_result_id` plus Overrides; VIB-Draft wird als bestätigt markiert und behalten.
4. PFA-Leaf-Termine: `_build_forecast_for_project` vereinigt `VibPfaEntry.project_id == project_id`; Archiv-Filter in `has_assigned_pfa`.
5. Postgres in CI: neuer Job im `ci.yml` mit dem `docker/db`-Image: `alembic upgrade head`, `alembic check`, `tests/db_related_tests` als Spatial-Suite neu befüllen. Vorher eine „Zero-Drift“-Migration (JSONB, `ix_users_id`, Flags, Unique-Constraints), damit `alembic check` grün wird.
6. Frontend-Invalidierung: `invalidateAfterProgressChange(projectId, superiorId)` (Progress-Prefix, `projectGroups`, Changelog) und `invalidateAfterFinveLinkChange` einführen; `useDeleteProject` nutzt die Archiv-Logik; Import-Confirms spiegeln die Backend-Seiteneffekte. `ApiError extends Error` mit `detail`; 401-Hook im Client setzt `user=null` und öffnet den Login; `AuthProvider` rendert sofort.
7. `pytest.ini` durch `os.environ.setdefault("ENVIRONMENT", "test")` in `tests/conftest.py` ersetzen; `PRAGMA foreign_keys=ON` im SQLite-Listener; `tests/api.py` und `tests/db_related_tests` (alt) entfernen.
8. Migrations-Lint in `test_migration_ids.py`: `drop_column`, `alter_column(nullable=False)`, `DELETE FROM` ohne Marker `# contract: approved` schlagen fehl. Restore-Kommando in DEPLOY.md gegen eine Scratch-DB auf dem Server testen und das Ergebnis dokumentieren.

### 6.3 Mittelfristig (Struktur, 1 bis 2 Monate)

1. Service-Schicht für Projektoperationen: `services/project_writes.py` mit `create`, `update`, `finalize`, `delete`, `archive`, `merge`, die Validierung, Changelog, Kaskaden und Neuberechnung bündeln; REST und MCP werden dünne Adapter.
2. Ein Teilbaum-Helper (`services/hierarchy.py`: `subtree_ids`, `active_children`, `is_superior`, mit Flags `include_drafts`, `include_archived`), der die vier Walker und vier Prädikate ersetzt. Entscheidung #265 (Drafts) dort einmal umsetzen.
3. Aggregation als Backend-Vertrag: `aggregate_for_project(source)` je Quelle (FinVe, GVFG, Infraplan, Länge) im Backend, Frontend-Summen (`projectCost.ts`) entfernen, MCP bekommt dieselben Zahlen. Kosten-Headline nach „neuerer Stand gewinnt“ oder Entscheidung 22 anpassen.
4. Import-Baukasten: `services/matching/score.py` (ein Matcher, eine `Suggestion`-Form, Schwellen als Konstanten), `tasks/_base.py` (Session, `report_step`, FAILURE-Zeile, ein Progress-Meta-Format), `read_pdf_upload_within_limit` (Größe, Magic-Bytes, Content-Type) für alle Uploads, `ImportConflictError → 409`. `tasks/__init__.py` leeren, `crud → tasks`-Importe auflösen, Parser nach `services/pdf/`. Modulschnitt: `tasks/haushalt.py` (1718), `mcp/tools/projects.py` (1576), `crud/projects/progress.py` (1852) wie in den Teilberichten skizziert aufteilen.
5. Datumspräzision vervollständigen: `pf_date_precision`, `parl_befassung_date_precision`, `lifecycle_date_precision` (Expand); abgeleitete Sortierwerte durch `normalize_sort_date`; Infraplan `BIS` als YEAR mit Label oder neue Präzision NOT_AFTER.
6. Session-Härtung: Per-User-Secret im HMAC, Rate-Limit im nginx, `/healthz` nach außen nur als Status ohne Problemliste.
7. Dokumentation konsolidieren: eine Steuerdatei für Agenten (AGENT.md), CLAUDE.md nur als Verweis; `apps/frontend/AGENT.md` auf das Existierende kürzen; `docs/production_setup.md` in „Server (DEPLOY.md gilt)“ und „Lokaler Full-Stack“ trennen; Roadmap-Checkbox-Klauseln in AGENT.md, Command `update-roadmap` und Hook `remind-roadmap.sh` entfernen; `docs/superpowers` löschen oder die Regel; `docs/testing.md` neu schreiben (zwei Stufen: SQLite-Unit/API, Postgres-Integration); Ports vereinheitlichen (Makefile, `.env.example`, `config.py`, READMEs); eine Besitzer-Tabelle „Thema → Datei“ in `docs/README.md`.

### 6.4 Langfristig

1. OCR-Bilder und große JSON-Blobs aus Tabellenzeilen auf das Upload-Volume; Blob-Spalten `deferred()`.
2. `TimestampMixin` mit `DateTime(timezone=True)`, `server_default=now()`, `onupdate`; `project_text`-Integer-Timestamps migrieren; `now_utc()`-Helper statt `datetime.utcnow()`.
3. Projektgeometrie zusätzlich als PostGIS-Spalte pflegen, damit Verschneidung und Längen ohne GeoJSON-Reparse laufen.
4. Rollback-Vertrag zweistufig: Mapping entfernen in Release N, Spalte droppen in N+1; `db_ahead.py` und `/healthz` melden „älteste sichere SHA“.
5. Jahrgangs-Hacks (Infraplan-Schriftgrößen, Haushalt-2027-Annahmen, GVFG-2023-Tippfehler) in Konfigurationstabellen je Jahrgang überführen; Einmalreparaturen (`repair_infraplan_full_stops`, `set_dt_aliases_2026`, `draft_gvfg_2025_projects`) nach Ausführung entfernen; `scripts/import_old_db` samt `pandas` entfernen.
6. Abhängigkeiten mit Major-Sprung bewusst heben (redis, PyMuPDF, openai, mistralai) mit grüner Suite.

## 7. Was gut ist

- Ableitungslogik des Planungsstands: reiner Service, rund 150 Unit-Tests, fast 1:1 auf die dokumentierten Regeln abbildbar (Vertrauensfenster, Konflikte, Untergrenzen, Datumspräzision, W1 bis W4).
- Archivierung wurde in einem Zug konsistent über fast alle Query-Stellen eingeführt, mit Helpern und Tests.
- Merge ist generisch über Metadaten, plant vor dem Schreiben, hält Redirects kettenfrei.
- Materialisierung ist gebündelt (eine Query je Quelle für N Projekte), Listen lesen nur den Cache.
- Auth-Primitive solide (PBKDF2, `compare_digest`, Keys nur als Hash, Scopes ohne Admin-Bypass im Dependency-Pfad), MCP mit einem Auth-Chokepoint und Capability-Prüfung an jedem der 48 Schreib-Tools, protokollnah getestet.
- Deploy-Weg: `prod.sh` klein und mit Stub getestet, SHA-Regex, Pull vor Switch, Backup vor Migration, echter Readiness-Check, Prüfung der Image-Manifeste vor SSH.
- Frontend: generierte Typen exakt synchron, ein `fetch`-Wrapper, zentrale Query-Keys, Lazy-Routen mit Retry, `vendor-react` einziges Preload, Design-System ohne Hex-Werte in Komponenten, `ResponsiveTable` überall, `tsc` strict sauber.
- Staged-File-Übergabe an Celery traversalsicher und getestet; Infraplan-Pipeline als Vorbild (persistenter Draft, Re-Parse, serverseitiges Confirm, Provenienz, REST und MCP auf derselben CRUD).
- Die Doku ist an vielen Stellen ehrlich über operative Fakten (GHCR-Token-Ablauf, Borg-Fenster, Vorfälle), und `test_migration_ids.py`/`test_db_ahead.py` kodieren echte vergangene Vorfälle.

## 8. Methodik und Grenzen

Sieben Tiefenprüfungen (Backend-Kern/Auth, Domänenlogik, Import-Pipelines, MCP, Frontend, Infrastruktur/Doku, Tests/Schema) haben den Code gelesen und Befunde mit Datei und Zeile belegt. Die zehn Top-Befunde wurden anschließend direkt im Code nachgeprüft. Nicht möglich war: Ausführung gegen eine PostGIS-Datenbank (`alembic check`), Prüfung des Live-Servers, `make test` unter macOS. Als „unverifiziert“ gelten: das Verhalten von `grep -oP` auf dem Entwickler-Mac, ob ein Client je nicht-kanonische Pfade (307-Redirect mit `http://`) trifft, und ob der Trust-Fenster-Fall „älterer, höherer Bericht im Fenster“ der Absicht entspricht.
